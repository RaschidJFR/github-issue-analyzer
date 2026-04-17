from ..helpers import functions
from ..models import ConversationalLLM
from ..helpers.github_graphql import fetch_issues
import os.path
import logging
from typing import Self

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts')


class IssueSummarizer:
  def __init__(self, repo:str, token: str, model: ConversationalLLM):
    self._model = model
    self._token = token
    self._repo = repo
    self.issues: list[dict] = None
    
  def fetch_issues(self) -> Self:
    logging.info(f'Fetching issues for repository {self._repo}...')
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

  def summarize(self, issue_data: list[dict] = None, limit: int = None, **kwargs) -> list[dict]:
    """Summarize issues using a predefined prompt template.
    Args:
      issue_data (list[dict], optional): List of issues to summarize. If None, uses previously loaded issues.
      limit (int, optional): Maximum number of issues to return. Defaults to None (no limit).
      include_effort (bool, optional): Whether to include effort in summary. Defaults to False.
    Returns:
      list[dict]: List of issues with summary results.
    """
    
    include_effort = kwargs.get('include_effort', False)
    issue_data = issue_data or self.issues
    if issue_data is None:
      raise ValueError("You must first call `fetch_issues` or `load_issues` to load issue data.")
    
    prompt = ''
    with open(os.path.join(PROMPTS_DIR, 'summarize.md'), 'r') as file:
      prompt = file.read()
  
    logging.info(f'Summarizing {len(issue_data)} issues...')
    issues = functions.apply_prompt(issue_data, model=self._model, prompt=prompt, limit=limit)
    
    if not include_effort:
      for issue in issues:
        issue.pop('effort', None)
    
    return issues
    
