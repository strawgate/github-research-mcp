from collections.abc import AsyncGenerator
from typing import Any

import pytest
from dirty_equals import IsInt, IsStr
from fastmcp import FastMCP
from fastmcp.client import Client
from fastmcp.client.client import CallToolResult
from fastmcp.client.transports import FastMCPTransport
from fastmcp.exceptions import ToolError
from inline_snapshot import snapshot

from github_research_mcp.clients.github import GitHubResearchClient
from github_research_mcp.servers.public import PublicServer
from tests.conftest import E2ERepository


def get_result_from_call_tool_result(call_tool_result: CallToolResult) -> dict[str, Any]:
    assert call_tool_result.structured_content is not None
    assert isinstance(call_tool_result.structured_content, dict)
    return call_tool_result.structured_content


def test_init(github_research_client: GitHubResearchClient) -> None:
    public_server = PublicServer(research_client=github_research_client)
    assert public_server is not None


@pytest.fixture
def public_server(github_research_client: GitHubResearchClient) -> PublicServer:
    return PublicServer(research_client=github_research_client)


@pytest.fixture
def public_mcp_server(fastmcp: FastMCP, public_server: PublicServer) -> FastMCP[Any]:
    return public_server.register_tools(fastmcp=fastmcp)


@pytest.fixture
async def public_mcp_client(public_mcp_server: FastMCP[Any]) -> AsyncGenerator[Client[FastMCPTransport], Any]:
    async with Client[FastMCPTransport](transport=public_mcp_server) as fastmcp_client:
        yield fastmcp_client


async def test_generate_agents_md(public_mcp_client: Client[FastMCPTransport], public_server: PublicServer, e2e_repository: E2ERepository):
    public_server.minimum_stars = 0

    call_tool_result = await public_mcp_client.call_tool(
        "generate_agents_md",
        arguments={"owner": e2e_repository.owner, "repo": e2e_repository.repo},
    )

    assert get_result_from_call_tool_result(call_tool_result=call_tool_result) == snapshot(
        {
            "name": "github-issues-e2e-test",
            "description": None,
            "fork": False,
            "url": "https://api.github.com/repos/strawgate/github-issues-e2e-test",
            "stars": IsInt(),
            "homepage_url": None,
            "language": "Python",
            "default_branch": "main",
            "topics": [],
            "archived": False,
            "created_at": IsStr(),
            "updated_at": IsStr(),
            "pushed_at": IsStr(),
            "license": None,
            "summary": IsStr(min_length=100),
        }
    )


async def test_public_server_summarize_ineligible(
    public_mcp_client: Client[FastMCPTransport], public_server: PublicServer, e2e_repository: E2ERepository
):
    public_server.minimum_stars = 10

    with pytest.raises(ToolError) as e:
        await public_mcp_client.call_tool(
            "generate_agents_md",
            arguments={"owner": e2e_repository.owner, "repo": e2e_repository.repo},
        )

    assert str(e.exconly()) == snapshot(
        "fastmcp.exceptions.ToolError: Error calling tool 'generate_agents_md': Repository strawgate/github-issues-e2e-test is not eligible for AGENTS.md generation, it has less than 10 stars and is not explicitly allowlisted."
    )


async def test_public_server_summarize_ineligible_allowlisted(
    public_mcp_client: Client[FastMCPTransport], public_server: PublicServer, e2e_repository: E2ERepository
):
    public_server.minimum_stars = 10
    public_server.owner_allowlist = ["strawgate"]

    context = await public_mcp_client.call_tool(
        "generate_agents_md",
        arguments={"owner": e2e_repository.owner, "repo": e2e_repository.repo},
    )

    assert get_result_from_call_tool_result(call_tool_result=context) == snapshot(
        {
            "name": "github-issues-e2e-test",
            "description": None,
            "fork": False,
            "url": "https://api.github.com/repos/strawgate/github-issues-e2e-test",
            "stars": IsInt(),
            "homepage_url": None,
            "language": "Python",
            "default_branch": "main",
            "topics": [],
            "archived": False,
            "created_at": IsStr(),
            "updated_at": IsStr(),
            "pushed_at": IsStr(),
            "license": None,
            "summary": IsStr(min_length=100),
        }
    )
