import asyncio
import os
from typing import Literal

import asyncclick as click
from fastmcp import FastMCP
from fastmcp.utilities.logging import get_logger

from github_research_mcp.sampling.handler import get_sampling_handler
from github_research_mcp.servers.research import ResearchServer

logger = get_logger(__name__)

disable_sampling = os.getenv("DISABLE_SAMPLING")

mcp = FastMCP[None](
    name="GitHub Research MCP",
    sampling_handler=None if disable_sampling else get_sampling_handler(),
)

repository_server: ResearchServer = ResearchServer(logger=logger)

repository_server.register_tools(fastmcp=mcp)


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
