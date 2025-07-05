from ..helpers import functions
from ..models import ConversationalLLM
from ..helpers.github_graphql import fetch_issues
import os.path
import logging
from typing import Self

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts')

class ImpactAnalyzer:
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

  def analyze(self, issues: list[dict] = None, limit: int = None) -> list[dict]:
    issues = issues or self.issues
    if issues is None:
      raise ValueError("You must first call `fetch_issues` or `load_issues` to load issue data.")
    
    prompt = ''
    with open(os.path.join(PROMPTS_DIR, 'estimate_impact.md'), 'r') as file:
      prompt = file.read()
  
    logging.info(f'Applying impact analysis prompt to {len(issues)} issues...')
    return functions.apply_prompt(issues, model=self._model, prompt=prompt, limit=limit)