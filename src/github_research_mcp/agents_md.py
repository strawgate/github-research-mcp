"""The entrypoint for the publicly hosted Agents.md Generator MCP Server."""

import os
from logging import Logger
from pathlib import Path
from typing import Literal

import click
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.server import FastMCP
from fastmcp.tools import Tool
from fastmcp.utilities.logging import configure_logging, get_logger

from github_research_mcp.clients.cache import get_cache_backend
from github_research_mcp.clients.github import GitHubResearchClient
from github_research_mcp.sampling.handler import get_sampling_handler
from github_research_mcp.servers.code import CodeServer
from github_research_mcp.servers.research import ResearchServer
from github_research_mcp.servers.summary import RepositorySummary, SummaryServer
from github_research_mcp.utilities.stars import check_minimum_stars, check_owner_allowlist, default_minimum_stars
from github_research_mcp.vendored.caching import CacheProtocol, MethodSettings, ResponseCachingMiddleware

logger: Logger = get_logger(__name__)

configure_logging()

clone_dir: Path = Path(os.getenv("CLONE_DIR", "tmp"))
if not clone_dir.exists():
    clone_dir.mkdir(parents=True, exist_ok=True)

ONE_WEEK_IN_SECONDS = 60 * 60 * 24 * 7

research_server: ResearchServer = ResearchServer(research_client=GitHubResearchClient())
summary_server: SummaryServer = SummaryServer(research_server=research_server, code_server=CodeServer())


async def generate_agents_md(owner: str, repo: str) -> RepositorySummary:
    if not await check_minimum_stars(research_client=research_server.research_client, owner=owner, repo=repo) and not check_owner_allowlist(
        owner=owner
    ):
        msg = (
            f"Repository {owner}/{repo} is not eligible for AGENTS.md generation, "
            f"it has less than {default_minimum_stars} stars and is not explicitly allowlisted."
        )
        raise ValueError(msg)

    return await summary_server.summarize_repository(owner=owner, repo=repo)


cache_backend: CacheProtocol = get_cache_backend()
response_caching_middleware: ResponseCachingMiddleware = ResponseCachingMiddleware(
    cache_backend=cache_backend,
    method_settings=MethodSettings(
        call_tool={
            "ttl": ONE_WEEK_IN_SECONDS,
        },
    ),
)

mcp: FastMCP[None] = FastMCP[None](
    name="Agents.md Generator",
    sampling_handler=get_sampling_handler(),
    sampling_handler_behavior="always",
    tools=[Tool.from_function(fn=generate_agents_md)],
    middleware=[LoggingMiddleware(include_payloads=True, logger=logger), response_caching_middleware],
)


@click.command()
@click.option(
    "--mcp-transport", type=click.Choice(["stdio", "streamable-http"]), default="stdio", help="The transport to run the MCP server on"
)
def run_mcp(mcp_transport: Literal["stdio", "streamable-http"]):
    mcp.run(transport=mcp_transport)


if __name__ == "__main__":
    run_mcp()
