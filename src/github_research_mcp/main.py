import asyncio
import os
from typing import Literal

import asyncclick as click
from fastmcp import FastMCP
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.utilities.logging import get_logger

from github_research_mcp.sampling.handler import get_sampling_handler
from github_research_mcp.servers.research import ResearchServer
from github_research_mcp.servers.summary import SummaryServer

logger = get_logger(__name__)

disable_summaries: bool = bool(os.getenv("DISABLE_SUMMARIES"))

mcp: FastMCP[None] = FastMCP[None](
    name="GitHub Research MCP",
    sampling_handler=None if disable_summaries else get_sampling_handler(),
)

mcp.add_middleware(middleware=LoggingMiddleware(include_payloads=True, logger=logger))

server: ResearchServer | SummaryServer

if disable_summaries:
    server = ResearchServer(logger=logger)
    logger.info("Running in research mode. Summaries are disabled.")
else:
    server = SummaryServer(logger=logger)
    logger.info("Running in summary mode. Summaries are enabled.")

server.register_tools(fastmcp=mcp)


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
