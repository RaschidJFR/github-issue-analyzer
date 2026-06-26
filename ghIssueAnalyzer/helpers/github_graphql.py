import requests
import logging
_GITHUB_API = "https://api.github.com/graphql"

_ISSUE_FIELDS = """
  number
  title
  body
  state
  createdAt
  url
  labels(first: 20) {
    nodes {
      name
    }
  }
  timelineItems(first: 25, itemTypes: [CROSS_REFERENCED_EVENT]) {
    nodes {
      ... on CrossReferencedEvent {
        willCloseTarget
        source {
          ... on PullRequest {
            number
            title
            state
            merged
            url
          }
        }
      }
    }
  }
  reactionGroups {
    content
    users {
      totalCount
    }
  }
  comments(first: 100) {
    nodes {
      body
      author {
        login
      }
      authorAssociation
      createdAt
      reactionGroups {
        content
        users {
          totalCount
        }
      }
    }
  }
"""


_SEARCH_QUERY = """
  query($queryString: String!, $cursor: String) {
    search(query: $queryString, type: ISSUE, first: 100, after: $cursor) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        ... on Issue {
          """ + _ISSUE_FIELDS + """
        }
      }
    }
  }
"""

def fetch_issues(github_token: str, repo_owner: str, repo_name: str, filters: list[str] = None):
  """Fetch open issues from a GitHub repository using the search API, sorted by last updated descending.
  When multiple keywords are provided, a separate query is run per keyword and results are deduplicated
  by issue number. This avoids GitHub's OR operator splitting qualifiers across expressions.
  Args:
    github_token (str): GitHub personal access token.
    repo_owner (str): Owner of the repository (user or organization).
    repo_name (str): Name of the repository.
    filters (list[str], optional): Keywords to filter by. Only issues whose title or body
      match at least one keyword are returned. Defaults to None (no filter).
  Returns:
    list[dict]: List of open issues.
  """
  repo_owner = repo_owner.strip()
  repo_name = repo_name.strip()
  headers = _build_headers(github_token)
  keywords = filters if filters else [None]

  seen = {}
  for keyword in keywords:
      kw_part = f"{keyword} " if keyword else ""
      query_string = f"repo:{repo_owner}/{repo_name} is:open {kw_part}sort:updated-desc"
      logging.info(f"Querying issues for {repo_owner}/{repo_name} through GraphQL search API...")
      issues = _fetch_all_pages(query_string, headers)
      for issue in issues:
          if issue.get("number") not in seen:
              seen[issue.get("number")] = issue

  logging.info(f"Successfully fetched {len(seen)} issues")
  return _unwrap_comments(list(seen.values()))

def _fetch_all_pages(query_string: str, headers: dict) -> list[dict]:
  """Paginate through all results for a given search query string, up to the fetch limit."""
  limit = 400
  issues: list[dict] = []
  cursor = None

  while len(issues) < limit:
      variables = {"queryString": query_string, "cursor": cursor}
      data = _post(_SEARCH_QUERY, variables, headers)
      page = data.get("search", {})
      issues, cursor, has_next = _collect_page(issues, page)
      if not has_next:
          break

  return issues

def _build_headers(github_token: str) -> dict:
  """Build the HTTP headers required for GitHub GraphQL API requests."""
  return {
      "Authorization": f"Bearer {github_token}",
      "Content-Type": "application/json",
  }

def _post(query: str, variables: dict, headers: dict) -> dict:
  """Execute a GraphQL query and return the parsed `data` field.
  Raises an exception on HTTP errors or GraphQL-level errors.
  """
  response = requests.post(
      _GITHUB_API,
      headers=headers,
      json={"query": query, "variables": variables}
  )

  if response.status_code != 200:
      raise Exception(f"Query failed with status code: {response.status_code}")

  result: dict = response.json()

  if "errors" in result:
      error_messages = [error.get("message", "Unknown error") for error in result["errors"]]
      raise Exception(f"GraphQL Errors: {'; '.join(error_messages)}")

  data = result.get("data")
  if data is None:
      raise Exception("No data returned from GitHub API")

  return data

def _collect_page(issues: list[dict], page: dict) -> tuple[list[dict], str | None, bool]:
  """Append nodes from a page response to the issues list.
  Nodes that don't match the Issue fragment are returned as empty dicts by the search API and are skipped.
  Returns the updated list, the next cursor, and whether another page exists.
  """
  nodes = [node for node in page.get("nodes", []) if node]
  if not nodes:
      logging.warning("No issues found in current page")
  issues.extend(nodes)
  page_info = page.get("pageInfo", {})
  return issues, page_info.get("endCursor"), page_info.get("hasNextPage", False)

def _format_linked_prs(timeline_nodes: list[dict]) -> str:
  """Format cross-referenced PRs from timeline nodes into a readable string.
  Only nodes that resolve to a PullRequest are included.
  The status is one of: open, merged, closed.
  PRs that will close the issue (via a fixing keyword) are marked with *.
  """
  parts = []
  for node in timeline_nodes:
      source = node.get("source", {})
      if not source or "number" not in source:
          continue
      pr_number = source["number"]
      pr_title = source.get("title", "")
      will_close = node.get("willCloseTarget", False)
      if source.get("merged"):
          status = "merged"
      elif source.get("state") == "OPEN":
          status = "open"
      else:
          status = "closed"
      closing_marker = "*" if will_close else ""
      
      # Format: (status) *PR title* #PR number
      parts.append(f"({status}){closing_marker} {pr_title} #{pr_number}")
  return "\n".join(parts)

def _unwrap_comments(issues: list[dict]) -> list[dict]:
  """Flatten nested GraphQL response structures into a clean issue format."""
  try:
      # Format issues to match gh cli output
      formatted_issues = [{
          "number": issue["number"],
          "title": issue["title"],
          "body": issue["body"],
          "state": issue["state"],
          "createdAt": issue["createdAt"][:10], # Truncate to date-only string
          "url": issue["url"],
          "labels": ", ".join(label["name"] for label in issue["labels"]["nodes"]),
          "linked_prs": _format_linked_prs(issue["timelineItems"]["nodes"]),
          "reactionGroups": [{
              "content": group["content"],
              "count": group["users"]["totalCount"]
          } for group in issue["reactionGroups"]],
          "comments": [comment for comment in issue["comments"]["nodes"]]
      } for issue in issues]
      
      return formatted_issues
      
  except Exception as e:
      logging.error(f"Error: {str(e)}")
      raise