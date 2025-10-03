import pytest

from github_research_mcp.clients.github import GitHubResearchClient
from github_research_mcp.utilities.stars import check_minimum_stars, check_owner_allowlist


@pytest.fixture
def github_research_client() -> GitHubResearchClient:
    return GitHubResearchClient()


async def test_check_minimum_stars(github_research_client: GitHubResearchClient) -> None:
    assert await check_minimum_stars(research_client=github_research_client, owner="strawgate", repo="github-issues-e2e-test") is False
    assert (
        await check_minimum_stars(research_client=github_research_client, owner="strawgate", repo="github-issues-e2e-test", minimum_stars=0)
        is True
    )


def test_check_owner_allowlist() -> None:
    assert check_owner_allowlist(owner="test") is False
    assert check_owner_allowlist(owner="test", owner_allowlist=["test"]) is True
