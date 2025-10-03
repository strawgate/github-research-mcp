import os
from logging import Logger
from pathlib import Path
from typing import Literal

import click
from fastmcp import FastMCP
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.utilities.logging import get_logger

from github_research_mcp.clients.github import GitHubResearchClient
from github_research_mcp.sampling.handler import get_sampling_handler
from github_research_mcp.servers.code import CodeServer
from github_research_mcp.servers.research import ResearchServer
from github_research_mcp.servers.summary import SummaryServer

logger: Logger = get_logger(name=__name__)

enable_summaries: bool = not bool(os.getenv("DISABLE_SUMMARIES"))

mcp: FastMCP[None] = FastMCP[None](
    name="GitHub Research MCP",
    sampling_handler=get_sampling_handler() if enable_summaries else None,
)

mcp.add_middleware(middleware=LoggingMiddleware(include_payloads=True, logger=logger))

research_server: ResearchServer = ResearchServer(research_client=GitHubResearchClient(), logger=logger)
_ = research_server.register_tools(fastmcp=mcp)

if enable_summaries:
    code_server: CodeServer = CodeServer(logger=logger, clone_dir=Path("code_server"))
    _ = code_server.register_tools(mcp=mcp)

    summary_server: SummaryServer = SummaryServer(research_server=research_server, code_server=code_server, logger=logger)
    _ = summary_server.register_tools(fastmcp=mcp)


@click.command()
@click.option(
    "--mcp-transport",
    type=click.Choice(["stdio", "streamable-http"]),
    default="stdio",
    help="The transport to run the MCP server on",
)
def run_mcp(mcp_transport: Literal["stdio", "streamable-http"]):
    mcp.run(transport=mcp_transport)


if __name__ == "__main__":
    run_mcp()
