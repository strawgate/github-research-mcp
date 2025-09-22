"""The entrypoint for the publicly hosted Agents.md Generator MCP Server."""

import asyncio
import os
from typing import Literal

import asyncclick as click
from fastmcp import FastMCP
from fastmcp.server.middleware.logging import StructuredLoggingMiddleware

from github_research_mcp.clients.cache import get_cache_backend
from github_research_mcp.clients.github import GitHubResearchClient
from github_research_mcp.sampling.handler import get_sampling_handler
from github_research_mcp.servers.public import PublicServer
from github_research_mcp.vendored.caching import MethodSettings, ResponseCachingMiddleware

ONE_WEEK_IN_SECONDS = 60 * 60 * 24 * 7

minimum_stars_env: str | None = os.getenv("MINIMUM_STARS")
minimum_stars: int = int(minimum_stars_env) if minimum_stars_env else 10

owner_allowlist_env: str | None = os.getenv("OWNER_ALLOWLIST")
owner_allowlist: list[str] = [owner.strip() for owner in (owner_allowlist_env.split(",") if owner_allowlist_env else [])]

mcp = FastMCP[None](
    name="Agents.md Generator",
    sampling_handler=get_sampling_handler(),
    sampling_handler_behavior="always",
)

github_client: GitHubResearchClient = GitHubResearchClient()

public_server: PublicServer = PublicServer(
    research_client=github_client,
    minimum_stars=minimum_stars,
    owner_allowlist=owner_allowlist,
)

public_server.register_tools(fastmcp=mcp)

mcp.add_middleware(middleware=StructuredLoggingMiddleware(include_payloads=True))

mcp.add_middleware(
    middleware=ResponseCachingMiddleware(
        cache_backend=get_cache_backend(),
        method_settings=MethodSettings(
            call_tool={
                "ttl": ONE_WEEK_IN_SECONDS,
            },
        ),
    )
)


@click.command()
@click.option(
    "--mcp-transport", type=click.Choice(["stdio", "streamable-http"]), default="stdio", help="The transport to run the MCP server on"
)
async def cli(mcp_transport: Literal["stdio", "streamable-http"]):
    await mcp.run_async(transport=mcp_transport)


def run_mcp():
    asyncio.run(cli())


if __name__ == "__main__":
    run_mcp()
