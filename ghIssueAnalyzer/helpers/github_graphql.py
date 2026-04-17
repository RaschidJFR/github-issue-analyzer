import requests
import logging
_GITHUB_API = "https://api.github.com/graphql"

def fetch_issues(github_token: str, repo_owner: str, repo_name: str):
  logging.info(f"Querying issues for {repo_owner}/{repo_name} through GraphQL API...")
  limit = 400

  headers = {
      "Authorization": f"Bearer {github_token}",
      "Content-Type": "application/json",
  }

  query = """
  query($owner: String!, $repo: String!, $cursor: String) {
    repository(owner: $owner, name: $repo) {
      issues(first: 100, after: $cursor, states: [OPEN], orderBy: {field: UPDATED_AT, direction: DESC}) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          number
          title
          body
          state
          createdAt
          url
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
        }
      }
    }
  }
  """

  issues: list[dict] = []
  cursor = None
  
  while len(issues) < limit:
      variables = {
          "owner": repo_owner.strip(),  # Ensure no whitespace
          "repo": repo_name.strip(),    # Ensure no whitespace
          "cursor": cursor
      }
      
      
      response = requests.post(
          _GITHUB_API,
          headers=headers,
          json={"query": query, "variables": variables}
      )
      
      if response.status_code != 200:
          raise Exception(f"Query failed with status code: {response.status_code}")
      
      result: dict = response.json()
      
      # Check for GraphQL errors
      if "errors" in result:
          error_messages = [error.get("message", "Unknown error") for error in result["errors"]]
          raise Exception(f"GraphQL Errors: {'; '.join(error_messages)}")
      
      data = result.get("data", {}).get("repository", {}).get("issues", {})
      
      if data is None:
          raise Exception("No data returned from GitHub API")
          
      # Add issues from current page
      current_nodes = data.get("nodes", [])
      if not current_nodes:
          logging.warning("No issues found in current page")
      
      issues.extend(current_nodes)
      
      # Check if there are more pages
      page_info = data.get("pageInfo", {})
      if not page_info.get("hasNextPage"):
          break
          
      cursor = page_info.get("endCursor")
  
  logging.info(f"Successfully fetched {len(issues)} issues")
  return _unwrap_comments(issues)

def _unwrap_comments(issues: list[dict]) -> list[dict]:
  try:
      # Format issues to match gh cli output
      formatted_issues = [{
          "number": issue["number"],
          "title": issue["title"],
          "body": issue["body"],
          "state": issue["state"],
          "createdAt": issue["createdAt"],
          "url": issue["url"],
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