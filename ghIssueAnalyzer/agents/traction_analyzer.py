from ..helpers.github_graphql import fetch_issues
from ..helpers import functions
from dateutil import parser
import pandas as pd
import json
import logging
from typing import Self

class TractionAnalyzer:
  def __init__(self, repo:str, token: str):
    self._token = token
    self._repo = repo
    self.issues: list[dict] = None
    
  def fetch_issues(self) -> Self:
    """ Fetch issues from the GitHub repository using the provided token.
    This method retrieves issues from the repository and stores them in the instance variable `self.issues`.
    
    Returns:
      list[dict]: A list of issues from the repository.
    """
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
    """ Load issues into the analyzer.

    Args:
      issues (list[dict]): A list of issues previously fetched with `fetch_issues()`.
    """
    self.issues = issues
    return self
  
  def _get_comment_dates(self, issues: list[dict]) -> list[dict]:
    """ 
    Extract the creation dates of issues and their comments.
    """
    
    def parse_date(date_str):
      return parser.parse(date_str).isoformat() if date_str else None
    
    return [
      {
        'number': issue['number'],
        'createdAt': parse_date(issue['createdAt']),
        'comments': [parse_date(comment['createdAt']) for comment in issue.get('comments', [])],
      } for issue in issues
    ]
    
  def _count_interactions(self, issues: list[dict]) -> list[dict]:
    """ Calculate the number of comments, commenters, and reactions for each issue.
    This function counts:
      - The number of comments on each issue (excluding repo members')
      - The number of unique commenters (excluding repo members)
      - The total number of reactions (any type) on each issue
    """
    
    data:list[dict] = []
    for issue in issues:
      issue_data = {'number': issue['number'], 'commentCount': 0, 'commenterCount': 0, 'reactionCount': 0}
      commenters = set()
      
      # count the number of reactions (any type)
      for reactionGroup in issue.get('reactionGroups', []):
        issue_data['reactionCount'] += reactionGroup['count']
        
      for comment in issue.get('comments', []):
        for reactionGroup in comment.get('reactionGroups', []):
          if 'users' in reactionGroup:
            issue_data['reactionCount'] += reactionGroup['users']['totalCount']

        # count the number of unique commenters (non-members) and thier comments
        if(comment.get('authorAssociation', '') != 'MEMBER'): # exclude repo members
          if comment.get('author') and 'login' in comment['author']:
            commenters.add(comment['author']['login'])
          issue_data['commentCount'] += 1
          
      issue_data['commenterCount'] = len(commenters)
      
      data.append(issue_data)
    return data
  
  def _calc_avg_comments(self, issues: list[dict], window=52, min_periods=1) -> list[dict]:
    """ Calculate the average number of comments per week for each issue.
    This function aggregates the comments by week and calculates the moving average.
    It also fills in missing weeks with zero comments.
    """
    dates_df = pd.DataFrame(self._get_comment_dates(issues)).set_index('number')
    
    col_index = dates_df.index.name
    col_dates_arr='comments'
    exploded_df = dates_df.explode(col_dates_arr)
    exploded_df[col_dates_arr] = pd.to_datetime(exploded_df[col_dates_arr], utc=True)
    
    #aggregate the number of comments per week per issue
    exploded_df['week'] = exploded_df[col_dates_arr].dt.to_period('W').astype(str).str[:10]
    weekly_counts = (exploded_df
                    .groupby([col_index, 'week']).size()
                    .reset_index(name='comment_count')
                    .set_index(col_index))
    
    # Fill in the missing weeks
    issues = dates_df.index.unique()
    end_date = pd.Timestamp.now(tz='UTC')
    start_date = end_date - pd.Timedelta(weeks=window)
    all_weeks = pd.date_range(start=start_date, end=end_date, freq='W').to_period('W').start_time.astype(str)
    complete_weeks = pd.DataFrame([(issue, week) for issue in issues for week in all_weeks], columns=[col_index, 'week'])
    
    weekly_counts = weekly_counts.merge(complete_weeks, on=[col_index, 'week'], how='outer').fillna(0)
    weekly_counts = weekly_counts.merge(dates_df[['createdAt']], on=[col_index], how='left')
    weekly_counts['week'] = pd.to_datetime(weekly_counts['week'], utc=True)
        
    # Calculate the moving average of comments per week
    weekly_counts['avg_comments_per_week'] = weekly_counts.groupby(col_index)['comment_count'].transform(
        lambda x: x.rolling(window=window, min_periods=min_periods).mean())    
    
    # Get the latest week for each issue
    weekly_counts = weekly_counts.sort_values([col_index,'week'], ascending=False).groupby(col_index).head(1).set_index(col_index)
    # Get the last comment date for each issue
    last_comment_df = (exploded_df
                      .groupby(col_index)
                      .agg({col_dates_arr: 'max'})
                      .rename(columns={col_dates_arr: 'last_comment'}))
    
    stats_df = last_comment_df.merge(weekly_counts[['avg_comments_per_week']], on=col_index, how='outer')
    oldest_date = pd.to_datetime('now', utc=True) - pd.Timedelta(weeks=window)
    # set average_comments_per_week to 0 for issues with no comments in the last 12 weeks
    stats_df['avg_comments_per_week'] = (stats_df.apply(
      lambda row: 0 if row['last_comment'] is pd.NaT or row['last_comment'] < oldest_date else row['avg_comments_per_week'], axis=1)
    )
    # Truncate last_comment to date-only string
    records = json.loads(stats_df.reset_index().to_json(orient='records', date_format='iso'))
    for record in records:
      if record.get('last_comment'):
        record['last_comment'] = record['last_comment'][:10]
    return records

  def analyze(self, issues: list[dict] = None) -> list[dict]:
    """ Analyze the traction of issues in the repository.
    This function calculates a traction score for each issue based on the number of comments, unique commenters, reactions, and average comments per week.
    The traction score is a weighted sum of these metrics, normalized to a range of 0 to 1.
    Args:
      issues (list[dict], optional): A list of issues to analyze. If not provided, the method will use the issues previously fetched with `fetch_issues()` or loaded with `load_issues()`.
    Returns:
      list[dict]: A list of issues with their traction scores and other metrics.
      
      Example output:
      [
        {
          "number": 123,
          "avg_comments_per_week": 1.5,
          "commentCount": 10,
          "commenterCount": 5,
          "reactionCount": 3,
          "score": 0.85
        },
        ...
      ]
    """
    logging.info(f'Analyzing traction for {len(issues)} issues...')
    
    issues = issues or self.issues
    if issues is None:
      raise ValueError("You must first call `fetch_issues()` or `load_issues()` to load issue data.")
    
    comments_data = self._calc_avg_comments(issues)
    interactions_data = self._count_interactions(issues)
    merged_data = functions.merge(comments_data, interactions_data, 'number')

    columns_to_normalize = ['avg_comments_per_week', 'commentCount', 'commenterCount', 'reactionCount']
    normalized_data = functions.normalize_values(merged_data, columns_to_normalize)

    for index, issue in enumerate(normalized_data):
      merged_data[index]['score'] = 0 if issue['avg_comments_per_week'] == 0 else (
        issue['commentCount'] * .3 
        + issue['commenterCount'] * .6 
        + issue['reactionCount'] * .15 
        + issue['avg_comments_per_week'] * .2
      )
    merged_data = functions.normalize_values(merged_data, ['score'])
    merged_data = sorted(merged_data, key=lambda x: x['score'], reverse=True)
    return merged_data
