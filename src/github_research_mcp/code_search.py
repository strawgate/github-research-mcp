"""The entrypoint for the publicly hosted Agents.md Generator MCP Server."""

import os
from pathlib import Path
from typing import Any, Literal

import click
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.server import FastMCP
from fastmcp.tools import Tool, forward_raw
from fastmcp.tools.tool import ToolResult
from fastmcp.tools.tool_transform import TransformedTool
from fastmcp.utilities.logging import configure_logging, get_logger

from github_research_mcp.clients.github import GitHubResearchClient
from github_research_mcp.sampling.handler import get_sampling_handler
from github_research_mcp.servers.code import CodeServer
from github_research_mcp.utilities.stars import check_minimum_stars, check_owner_allowlist, default_minimum_stars

configure_logging()

logger = get_logger(__name__)


def new_mcp_server():
    clone_dir: Path = Path(os.getenv("CLONE_DIR", "tmp"))
    if not clone_dir.exists():
        clone_dir.mkdir(parents=True, exist_ok=True)

    research_client: GitHubResearchClient = GitHubResearchClient()
    code_server: CodeServer = CodeServer(logger=logger, clone_dir=clone_dir)

    async def validate_code_search(owner: str, repo: str, **kwargs: Any) -> ToolResult:  # pyright: ignore[reportAny]
        if not await check_minimum_stars(research_client=research_client, owner=owner, repo=repo) and not check_owner_allowlist(
            owner=owner
        ):
            msg = (
                f"Repository {owner}/{repo} is not eligible for code search, "
                f"it has less than {default_minimum_stars} stars and is not explicitly allowlisted."
            )
            raise ValueError(msg)

        return await forward_raw(owner=owner, repo=repo, **kwargs)

    code_search_tool: Tool = Tool.from_function(fn=code_server.search_code)
    validated_code_search_tool: Tool = TransformedTool.from_tool(tool=code_search_tool, transform_fn=validate_code_search)

    return FastMCP[None](
        name="Agents.md Generator",
        sampling_handler=get_sampling_handler(),
        sampling_handler_behavior="always",
        tools=[validated_code_search_tool],
        middleware=[LoggingMiddleware(include_payloads=True, logger=get_logger(__name__))],
    )


mcp: FastMCP[None] = new_mcp_server()


@click.command()
@click.option(
    "--mcp-transport", type=click.Choice(["stdio", "streamable-http"]), default="stdio", help="The transport to run the MCP server on"
)
def run_mcp(mcp_transport: Literal["stdio", "streamable-http"]):
    mcp.run(transport=mcp_transport)


if __name__ == "__main__":
    run_mcp()
