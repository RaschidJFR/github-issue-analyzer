from ..models import ConversationalLLM, helpers
from ..github_graphql import fetch_issues
import os.path
import logging
from typing import Self

_logger = logging.getLogger(__name__)

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts')


class IssueSummarizer:
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

  def summarize(self, issue_data: list[dict] = None, limit: int = None) -> list[dict]:
    issue_data = issue_data or self.issues
    if issue_data is None:
      raise ValueError("You must first call `fetch_issues` or `load_issues` to load issue data.")
    
    prompt = ''
    with open(os.path.join(PROMPTS_DIR, 'summarize.md'), 'r') as file:
      prompt = file.read()
  
    _logger.info(f'Summarizing {len(issue_data)} issues...')
    return helpers.apply_prompt(issue_data, model=self._model, prompt=prompt, limit=limit)
    
