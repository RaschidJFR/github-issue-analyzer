from ..models import ConversationalLLM, helpers
from ..github_graphql import fetch_issues
from .issue_summarizer import IssueSummarizer
from .traction_analyzer import TractionAnalyzer
from .impact_analyzer import ImpactAnalyzer
import logging
from typing import Self
_logger = logging.getLogger(__name__)

class IssueAnalyzer:
  def __init__(self, repo:str, token: str, model: ConversationalLLM):
    self._model = model
    self._token = token
    self._repo = repo
    self.issues: list[dict] = None
    
  def fetch_issues(self) -> Self:
    _logger.info(f'Fetching issues for repository {self._repo}...')
    issues: list[dict] = []
    repo_owner = self._repo.split('/')[0]
    repo_name = self._repo.split('/')[1]
    issues = fetch_issues(
      self._token, 
      repo_owner=repo_owner, 
      repo_name=repo_name)
    self.issues = issues
    return self
    
  def load_issues(self, issues: list[dict]) -> Self:
    self.issues = issues
    return self
    
  def _calculate_scores(self, merged_data: list[dict]) -> list[dict]:
    """
    Calculate scores for issues based on impact, traction, and effort.
    
    Args:
      merged_data (list[dict]): List of dictionaries containing issue data with 'impact', 'traction', and 'effort'.
    Returns:
      list[dict]: List of dictionaries with calculated scores for each issue.
    """
    for issue in merged_data:
        issue['score'] = issue['impact'] * issue['traction'] / (issue['effort'] or 1)
    merged_data = helpers.normalize_values(merged_data, ['score'])
    merged_data = sorted(merged_data, key=lambda x: x['score'], reverse=True)
    return merged_data

  def analyze(self, issues: list[dict] = None, head: int = 20) -> list[dict]:
    """Analyze and prioritize issues based on traction, impact, and effort.
    Args:
      issues (list[dict], optional): List of issues to analyze. If None, uses previously loaded issues.
      head (int, optional): Maximum number of issues to return. Defaults to 20.
    Returns:
      list[dict]: List of prioritized issues with calculated scores.
    """
    
    issues = issues or self.issues
    if issues is None:
      raise ValueError("You must first call `fetch_issues` or `load_issues` to load issue data.")
    
    # Take the top issues from traction analyzer
    traction_data = TractionAnalyzer(self._repo, self._token).analyze(issues)
    head = min(head, len(traction_data))
    traction_data = traction_data[:head]
    top_numbers = {issue['number'] for issue in traction_data}
    _logger.info(f'Prioritizing top {head} issues based on traction...')
    
    top_issues = []
    for issue in issues:
      if issue['number'] in top_numbers:
        top_issues.append(issue)
    
    summary_data = IssueSummarizer(self._repo, self._token, self._model).summarize(top_issues)
    impact_data = ImpactAnalyzer(self._repo, self._token, self._model).analyze(top_issues)
    
    merged_data = {}
    for issue in traction_data:
      merged_data[issue['number']] = issue
      merged_data[issue['number']]['traction'] = issue.pop('score', 0)
    
    for issue in summary_data:
      if issue['number'] in merged_data:
        merged_data[issue['number']].update(issue)
        
    for impact in impact_data:
      if impact['number'] in merged_data:
        merged_data[impact['number']].update(impact)
        
    for issue in issues:
      if issue['number'] in merged_data:
        merged_data[issue['number']].update({
          'title': issue['title'],
          'url': issue['url'],
          'createdAt': issue['createdAt'],
        })

    result = self._calculate_scores(list(merged_data.values()))
    _logger.info(f'Prioritized {len(result)} issues.')
    return result
    
