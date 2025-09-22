from logging import Logger
from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP
from fastmcp.tools import Tool
from fastmcp.utilities.logging import get_logger

from github_research_mcp.clients.github import GitHubResearchClient
from github_research_mcp.servers.shared.annotations import OWNER, REPO
from github_research_mcp.servers.summary import (
    RepositorySummary,
    SummaryServer,
)

if TYPE_CHECKING:
    from github_research_mcp.clients.models.github import Repository

ONE_DAY_IN_SECONDS = 60 * 60 * 24

logger = get_logger(__name__)


class PublicServer(SummaryServer):
    minimum_stars: int
    owner_allowlist: list[str]

    def __init__(
        self,
        research_client: GitHubResearchClient,
        logger: Logger | None = None,
        minimum_stars: int | None = None,
        owner_allowlist: list[str] | None = None,
    ):
        super().__init__(research_client=research_client, logger=logger)

        self.minimum_stars = minimum_stars or 10
        self.owner_allowlist = owner_allowlist or []

    def register_tools(self, fastmcp: FastMCP[Any]) -> FastMCP[Any]:
        fastmcp.add_tool(tool=Tool.from_function(fn=self.generate_agents_md))
        return fastmcp

    async def _check_minimum_stars(self, owner: OWNER, repo: REPO) -> bool:
        repository: Repository | None = await self.research_client.get_repository(owner=owner, repo=repo, error_on_not_found=False)

        if repository is None:
            msg = f"Repository {owner}/{repo} does not exist or access is not authorized"
            raise ValueError(msg)

        if repository.stars < self.minimum_stars:
            msg = f"Repository {owner}/{repo} has less than {self.minimum_stars} stars and is not eligible for summarization"
            return False

        return True

    async def _check_owner_allowlist(self, owner: OWNER) -> bool:
        return owner in self.owner_allowlist

    async def generate_agents_md(self, owner: OWNER, repo: REPO) -> RepositorySummary:
        if not await self._check_minimum_stars(owner=owner, repo=repo) and not await self._check_owner_allowlist(owner=owner):
            msg = (
                f"Repository {owner}/{repo} is not eligible for AGENTS.md generation, "
                f"it has less than {self.minimum_stars} stars and is not explicitly allowlisted."
            )
            raise ValueError(msg)

        return await self.summarize_repository(owner=owner, repo=repo)
