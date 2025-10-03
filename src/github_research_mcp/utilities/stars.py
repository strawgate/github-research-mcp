import os
from typing import TYPE_CHECKING

from github_research_mcp.clients.github import GitHubResearchClient

if TYPE_CHECKING:
    from github_research_mcp.clients.models.github import Repository

default_minimum_stars = int(os.getenv("MINIMUM_STARS", "10"))
default_owner_allowlist: list[str] = [owner.strip() for owner in (os.getenv("OWNER_ALLOWLIST", "").split(","))]


async def check_minimum_stars(
    research_client: GitHubResearchClient, owner: str, repo: str, minimum_stars: int = default_minimum_stars
) -> bool:
    repository: Repository | None = await research_client.get_repository(owner=owner, repo=repo, error_on_not_found=False)

    if repository is None:
        msg = f"Repository {owner}/{repo} does not exist or access is not authorized"
        raise ValueError(msg)

    if repository.stars < minimum_stars:
        msg = f"Repository {owner}/{repo} has less than {minimum_stars} stars and is not eligible for summarization"
        return False

    return True


def check_owner_allowlist(owner: str, owner_allowlist: list[str] = default_owner_allowlist) -> bool:
    return owner in owner_allowlist
