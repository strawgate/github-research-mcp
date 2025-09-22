from typing import Any

import pytest
from githubkit.github import GitHub

from github_research_mcp.clients.github import GitHubResearchClient


@pytest.fixture
def github_research_client(githubkit_client: GitHub[Any]) -> GitHubResearchClient:
    return GitHubResearchClient(githubkit_client=githubkit_client)
