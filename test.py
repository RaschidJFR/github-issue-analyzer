import os
from dotenv import load_dotenv
load_dotenv()
import logging
logging.basicConfig(level=logging.INFO)

from ghIssueAnalyzer.helpers.github_graphql import fetch_issues
# fetch_issues(os.getenv("GITHUB_TOKEN"), "parse-community", "parse-server")

from ghIssueAnalyzer.helpers import functions
print(functions.merge([{'x':1, 'a': 1}, {'x':2, 'b': 2}], [{'x':1, 'c': 3}, {'x':2, 'd': 4}], 'x'))

from ghIssueAnalyzer.models import ChatGPT
# print(ChatGPT(os.getenv("OPENAI_API_KEY")).prompt('Hi!'))

from ghIssueAnalyzer.agents import TractionAnalyzer
print(TractionAnalyzer('parse-community/parse-server', os.getenv('GITHUB_TOKEN')).analyze(['']))