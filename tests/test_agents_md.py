import os
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

import pytest
from fastmcp import FastMCP
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from inline_snapshot import snapshot

from github_research_mcp.agents_md import new_mcp_server
from tests.conftest import dump_list_for_snapshot

if TYPE_CHECKING:
    from fastmcp.client.client import CallToolResult


@pytest.fixture
def agents_md_mcp() -> FastMCP[Any]:
    os.environ["OWNER_ALLOWLIST"] = "strawgate"
    return new_mcp_server()


@pytest.fixture
async def agents_md_mcp_client(agents_md_mcp: FastMCP[Any]) -> AsyncGenerator[Client[FastMCPTransport], Any]:
    async with Client[FastMCPTransport](transport=agents_md_mcp) as agents_md_mcp_client:
        yield agents_md_mcp_client


async def test_agents_md_mcp_client(agents_md_mcp_client: Client[FastMCPTransport]) -> None:
    list_tools = await agents_md_mcp_client.list_tools()
    assert dump_list_for_snapshot(list_tools, exclude_keys=["outputSchema", "meta"]) == snapshot(
        [
            {
                "name": "generate_agents_md",
                "inputSchema": {
                    "properties": {"owner": {"type": "string"}, "repo": {"type": "string"}},
                    "required": ["owner", "repo"],
                    "type": "object",
                },
            }
        ]
    )


async def test_agents_md_mcp_client_generate_agents_md(agents_md_mcp_client: Client[FastMCPTransport]) -> None:
    result: CallToolResult = await agents_md_mcp_client.call_tool(
        "generate_agents_md",
        arguments={"owner": "strawgate", "repo": "github-issues-e2e-test"},
    )
    assert result.structured_content is not None
