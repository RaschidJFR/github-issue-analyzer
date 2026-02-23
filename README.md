# AI GitHub Issue Analyzer

A Python tool for analyzing and prioritizing GitHub issues based on _traction_, _impact_, and estimated _effort_. This tool helps developers and project maintainers identify which issues to focus on first.

## Features

- **Automated Issue Fetching**: Retrieves issues from any GitHub repository
- **AI Analysis**: Analyzes issues based on multiple factors including:
  - Traction (comments, reactions, engagement)
  - Impact (potential effect on users/project based on the conversation)
  - Effort (estimated complexity and time required)
- **Prioritization Scoring**: Generates priority scores to help with decision making

## Usage

See the provided [Jupyter notebook](./notebook.ipynb) for usage examples:

```py
from lib.agents import IssueAnalyzer
from lib.models import ChatGPT

# A simple ChatGPT wrapper interface.
# (TO-DO: support other LLMs providers in the future)
model = ChatGPT('YOUR_OPENAI_API_KEY', model='gpt-4o-mini')

agent = IssueAnalyzer(
    'parse-community/parse-server',   # GitHub repository
    'YOUR_GITHUB_TOKEN',              # GitHub token
    model
)

# Fetch open issues and analyze the top 15
analysis = agent.fetch_issues().analyze(head=15)

# Export analysis to CSV using your preferred method
pd.DataFrame(analysis).to_csv('issue_analysis.csv', index=False)
```

## Output Format

`IssueAnalyzer.analyze()` returns a list of dictionaries with the following structure:

### Main Fields

| Key               | Type  | Description                                                                                                                                                                                                                                                                 |
| ----------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `number`          | int   | GitHub issue number                                                                                                                                                                                                                                                         |
| `url`             | str   | GitHub issue URL                                                                                                                                                                                                                                                            |
| `title`           | str   | Issue title                                                                                                                                                                                                                                                                 |
| `issue_type`      | str   | One of: Bug, Security, Performance, Documentation, Feature Request, Other                                                                                                                                                                                                   |
| `summary`         | str   | Concise summary of the issue and its conclusion                                                                                                                                                                                                                             |
| `traction`        | float | Normalized score based on comments, reactions, and engagement. Calculated using the following weights: <br>`commentCount * .3 + uniqueCommenterCount * .6 + reactionCount * .15 + avg_comments_per_week' * .2`                                                              |
| `impact`          | float | Impact score (1 to 4) from LLM analysis according to the template selected. _See [prompts](./ghIssueAnalyzer/agents/prompts/)_                                                                                                                                              |
| `impact_analysis` | str   | Explanation of impact score assignment                                                                                                                                                                                                                                      |
| `effort`          | float | If set in the analysis parameters, this is the effort estimation from LLM analysis; `1` otherwise. _See [prompt](./ghIssueAnalyzer/agents/prompts/summarize.md)_. <br>**Note:** This estimation can be improved with a dedicated prompt but for now it seems to be enough for a decent issue ranking |
| `score`           | float | Overall priority score (normalized 0-1, higher = more important). The resulting list is sorted by this value. <br>**Formula:** `traction * impact / effort`                                                                                                                 |
| `createdAt`       | str   | ISO timestamp when issue was created                                                                                                                                                                                                                                        |

### Additional Fields

| Key                     | Type  | Description                                            |
| ----------------------- | ----- | ------------------------------------------------------ |
| `avg_comments_per_week` | float | Average number of comments per week over recent period |
| `commentCount`          | int   | Total number of comments (excluding repo members)      |
| `commenterCount`        | int   | Number of unique commenters (excluding repo members)   |
| `reactionCount`         | int   | Total number of reactions on issue and comments        |
| `last_comment`          | str   | ISO timestamp of most recent comment                   |

---

**Note**: This tool uses AI to analyze issues, so results may vary. Always review the analysis before making important decisions.

## Configuration

### GitHub Token Permissions

Your GitHub token needs the following permissions:

- `repo` (for public and private repositories)

### OpenAI Token Permissions

In your API key settings, make sure to enable access to the GPT-4o mini model (or whichever model you plan to use)

## To Do

- [ ] Validate and improve ranking algorithm
- [ ] Provide a way to export the analysis results
- [ ] Support other LLM providers (eg: Gemini, Claude, etc)
- [ ] Test support for private repositories
- [ ] Integrate report with Github Discussions
