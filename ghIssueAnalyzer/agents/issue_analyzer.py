from ..helpers import functions
from ..models import ConversationalLLM
from ..helpers.github_graphql import fetch_issues
from .issue_summarizer import IssueSummarizer
from .traction_analyzer import TractionAnalyzer
from .impact_analyzer import ImpactAnalyzer
import logging
from typing import Self
from pydispatch import dispatcher
from enum import Enum, auto

class IssueAnalyzer:
  
  class Signals(Enum):
    """Enum representing events related to issue analysis.
    Each event corresponds to a specific action or state in the issue analysis process.
    
    - ISSUE_ANALYZER_PROGRESS: Event triggered to signal progress in the issue analysis task.
    """
    PROGRESS_UPDATE = auto()
    TASK_COMPLETED = auto()
    ERROR = auto()

  class Steps(Enum):
    """Enum representing the steps in the issue analysis process.
    Each step corresponds to a specific stage in the analysis workflow.
    - TASK_STARTED: The analysis task has started.
    - TRACTION_ANALYSIS_STARTED: The traction analysis step has started.
    - ISSUE_SUMMARIZATION_STARTED: The issue summarization step has started.
    - IMPACT_ANALYSIS_STARTED: The impact analysis step has started.
    - RANKING_STARTED: The ranking of issues based on scores has started.
    - TASK_COMPLETED: The analysis task has been completed successfully.
    - ERROR: An error occurred during the analysis process.
    """
    FETCHING_ISSUES = auto()
    TRACTION_ANALYSIS_STARTED = auto()
    ISSUE_SUMMARIZATION_STARTED = auto()
    IMPACT_ANALYSIS_STARTED = auto()
    SCORING_STARTED = auto()
  
  def __init__(self, repo:str, token: str, model: ConversationalLLM):
    self._model = model
    self._token = token
    self._repo = repo
    self.issues: list[dict] = None
    
  def fetch_issues(self, filters: list[str] = None) -> Self:
    """Fetch open issues from the GitHub repository.
    Args:
      filters (list[str], optional): Keywords to filter issues by. GitHub's search API is used
        to retrieve only issues whose title or body contain at least one keyword. Defaults to None (no filter).
    Returns:
      Self: The current instance for method chaining.
    """
    logging.info(f'Fetching issues for repository {self._repo}...')
    self._emit_progress(IssueAnalyzer.Steps.FETCHING_ISSUES)

    repo_owner = self._repo.split('/')[0]
    repo_name = self._repo.split('/')[1]
    self.issues = fetch_issues(
      self._token,
      repo_owner=repo_owner,
      repo_name=repo_name,
      filters=filters)
    return self
    
  def load_issues(self, issues: list[dict]) -> Self:
    self.issues = issues
    return self
    
  def _calculate_scores(self, merged_data: list[dict], **kwargs) -> list[dict]:
    """
    Calculate scores for issues based on impact, traction, and effort.
    
    Args:
      merged_data (list[dict]): List of dictionaries containing issue data with 'impact', 'traction', and 'effort'.
      include_effort (bool, optional): Whether to include effort in score calculation. Defaults to False.
    Returns:
      list[dict]: List of dictionaries with calculated scores for each issue.
    """
    for issue in merged_data:
        issue['score'] = issue['impact'] * issue['traction']
        if kwargs.get('include_effort', False):
            issue['score'] = issue['score'] / (issue.get('effort', 0) or 1)
    merged_data = functions.normalize_values(merged_data, ['score'])
    merged_data = sorted(merged_data, key=lambda x: x['score'], reverse=True)
    return merged_data

  def _emit_progress(self, step: Steps, data: dict = {}) -> None:
    dispatcher.send(
      signal=IssueAnalyzer.Signals.PROGRESS_UPDATE,
      sender=self,
      step=step,
      data=data
    )

  def analyze(self, issues: list[dict] = None, head: int = 20, **kwargs) -> list[dict]:
    """Analyze and prioritize issues based on traction, impact, and effort.
    Args:
      issues (list[dict], optional): List of issues to analyze. If None, uses previously loaded issues.
      head (int, optional): Maximum number of issues to return. Defaults to 20.
      include_effort (bool, optional): Whether to include effort in score calculation. Defaults to False.
      template ('DX' | 'SDAP', optional): Template type for impact analysis. Defaults to 'DX'.
    Returns:
      list[dict]: List of prioritized issues with calculated scores.
    """
    include_effort = kwargs.get('include_effort', False)
    template = kwargs.get('template', 'DX')
    result = []
    try:
      issues = issues or self.issues
      if issues is None:
        raise ValueError("You must first call `fetch_issues` or `load_issues` to load issue data.")
      
      # Take the top issues from traction analyzer
      self._emit_progress(IssueAnalyzer.Steps.TRACTION_ANALYSIS_STARTED)
      traction_data = TractionAnalyzer(self._repo, self._token).analyze(issues)
      head = min(head, len(traction_data))
      traction_data = traction_data[:head]
      top_numbers = {issue['number'] for issue in traction_data}
      logging.info(f'Prioritizing top {head} issues based on traction...')
      
      top_issues = []
      for issue in issues:
        if issue['number'] in top_numbers:
          top_issues.append(issue)
      
      self._emit_progress(IssueAnalyzer.Steps.ISSUE_SUMMARIZATION_STARTED)
      summary_data = IssueSummarizer(self._repo, self._token, self._model).summarize(top_issues, include_effort=include_effort)
      
      self._emit_progress(IssueAnalyzer.Steps.IMPACT_ANALYSIS_STARTED)
      impact_data = ImpactAnalyzer(self._repo, self._token, self._model).analyze(top_issues, template=template)
      
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

      self._emit_progress(IssueAnalyzer.Steps.SCORING_STARTED)
      result = self._calculate_scores(list(merged_data.values()), include_effort=include_effort)
      logging.info(f'Prioritized {len(result)} issues.')
    
      dispatcher.send(signal=IssueAnalyzer.Signals.TASK_COMPLETED, sender=self, data=result)
      return result
    
    except Exception as e:
      logging.exception(f'Error analyzing issues: {e}')
      dispatcher.send(signal=IssueAnalyzer.Signals.ERROR, sender=self, data=str(e))
          