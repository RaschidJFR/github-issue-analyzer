from setuptools import setup, find_packages

setup(
  name="github_issue_analyzer",             
  version="0.1.0",                         
  packages=["ghIssueAnalyzer"],
  package_dir={"ghIssueAnalyzer": "lib"},   
  install_requires=open('requirements.txt').read().splitlines(),
  python_requires=">=3.12",
)