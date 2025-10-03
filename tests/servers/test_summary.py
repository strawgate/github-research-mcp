from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest
from fastmcp.client import Client, FastMCPTransport
from fastmcp.client.client import CallToolResult
from fastmcp.server import FastMCP
from inline_snapshot import snapshot

from github_research_mcp.clients.github import GitHubResearchClient
from github_research_mcp.servers.code import CodeServer
from github_research_mcp.servers.research import ResearchServer
from github_research_mcp.servers.summary import SummaryServer
from tests.conftest import E2ERepository, dump_list_for_snapshot


def write_summary_to_file(summary: str, owner: str, repo: str):
    samples_dir = Path(__file__).parent.parent.parent / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    with Path(samples_dir / f"{owner}-{repo}.md").open("w") as f:
        _ = f.write(summary)


def get_result_from_call_tool_result(call_tool_result: CallToolResult) -> dict[str, Any]:
    assert call_tool_result.structured_content is not None
    assert isinstance(call_tool_result.structured_content, dict)
    return call_tool_result.structured_content


def get_summary_from_result(call_tool_result: CallToolResult) -> str:
    result = get_result_from_call_tool_result(call_tool_result=call_tool_result)

    summary = result.get("summary")
    assert summary is not None
    return summary  # pyright: ignore[reportAny]


@pytest.fixture
def code_server() -> Generator[CodeServer, Any, None]:
    with TemporaryDirectory() as temp_dir:
        code_server = CodeServer(clone_dir=Path(temp_dir))
        yield code_server


async def test_init(github_research_client: GitHubResearchClient, code_server: CodeServer) -> None:
    summary_server = SummaryServer(
        research_server=ResearchServer(research_client=github_research_client),
        code_server=code_server,
    )
    assert summary_server is not None


@pytest.fixture
def summary_server(github_research_client: GitHubResearchClient, code_server: CodeServer) -> SummaryServer:
    return SummaryServer(
        research_server=ResearchServer(research_client=github_research_client),
        code_server=code_server,
    )


@pytest.fixture
def summary_mcp(fastmcp: FastMCP, summary_server: SummaryServer) -> FastMCP[Any]:
    return summary_server.register_tools(fastmcp=fastmcp)


@pytest.fixture
async def summary_mcp_client(summary_mcp: FastMCP[Any]) -> AsyncGenerator[Client[FastMCPTransport], Any]:
    async with Client[FastMCPTransport](transport=summary_mcp) as summary_mcp_client:
        yield summary_mcp_client


async def test_list_tools(summary_mcp_client: Client[FastMCPTransport]) -> None:
    list_tools = await summary_mcp_client.list_tools()
    assert dump_list_for_snapshot(list_tools, exclude_keys=["inputSchema", "outputSchema", "meta"]) == snapshot(
        [{"name": "summarize_repository"}]
    )


async def test_summarize_repository(summary_mcp_client: Client[FastMCPTransport], e2e_repository: E2ERepository) -> None:
    call_tool_result: CallToolResult = await summary_mcp_client.call_tool(
        "summarize_repository",
        arguments={"owner": e2e_repository.owner, "repo": e2e_repository.repo},
    )

    summary = get_summary_from_result(call_tool_result=call_tool_result)
    assert summary is not None
    assert len(summary) > 500
    write_summary_to_file(summary=summary, owner=e2e_repository.owner, repo=e2e_repository.repo)


@pytest.mark.skip_on_ci
async def test_summarize_repository_elastic_beats(summary_mcp_client: Client[FastMCPTransport]) -> None:
    owner = "elastic"
    repo = "beats"

    call_tool_result: CallToolResult = await summary_mcp_client.call_tool(
        "summarize_repository",
        arguments={"owner": owner, "repo": repo},
    )

    summary = get_summary_from_result(call_tool_result=call_tool_result)
    assert summary is not None
    assert len(summary) > 500
    write_summary_to_file(summary=summary, owner=owner, repo=repo)


@pytest.mark.skip_on_ci
async def test_summarize_repository_elastic_agent(summary_mcp_client: Client[FastMCPTransport]) -> None:
    owner = "elastic"
    repo = "agent"

    call_tool_result: CallToolResult = await summary_mcp_client.call_tool(
        "summarize_repository",
        arguments={"owner": owner, "repo": repo},
    )

    summary = get_summary_from_result(call_tool_result=call_tool_result)
    assert summary is not None
    assert len(summary) > 500
    write_summary_to_file(summary=summary, owner=owner, repo=repo)


@pytest.mark.skip_on_ci
async def test_summarize_repository_elastic_ecs(summary_mcp_client: Client[FastMCPTransport]) -> None:
    owner = "elastic"
    repo = "ecs"

    call_tool_result: CallToolResult = await summary_mcp_client.call_tool(
        "summarize_repository",
        arguments={"owner": owner, "repo": repo},
    )

    summary = get_summary_from_result(call_tool_result=call_tool_result)
    assert summary is not None
    assert len(summary) > 500
    write_summary_to_file(summary=summary, owner=owner, repo=repo)


@pytest.mark.skip_on_ci
async def test_summarize_repository_elastic_elasticsearch(summary_mcp_client: Client[FastMCPTransport]) -> None:
    owner = "elastic"
    repo = "elasticsearch"

    call_tool_result: CallToolResult = await summary_mcp_client.call_tool(
        "summarize_repository",
        arguments={"owner": owner, "repo": repo},
    )

    summary = get_summary_from_result(call_tool_result=call_tool_result)
    assert summary is not None
    assert len(summary) > 500
    write_summary_to_file(summary=summary, owner=owner, repo=repo)


@pytest.mark.skip_on_ci
async def test_summarize_repository_elastic_kibana(summary_mcp_client: Client[FastMCPTransport]) -> None:
    owner = "elastic"
    repo = "kibana"

    call_tool_result: CallToolResult = await summary_mcp_client.call_tool(
        "summarize_repository",
        arguments={"owner": owner, "repo": repo},
    )

    summary = get_summary_from_result(call_tool_result=call_tool_result)
    assert summary is not None
    assert len(summary) > 500
    write_summary_to_file(summary=summary, owner=owner, repo=repo)


@pytest.mark.skip_on_ci
async def test_summarize_repository_elastic_logstash(summary_mcp_client: Client[FastMCPTransport]) -> None:
    owner = "elastic"
    repo = "logstash"

    call_tool_result: CallToolResult = await summary_mcp_client.call_tool(
        "summarize_repository",
        arguments={"owner": owner, "repo": repo},
    )

    summary = get_summary_from_result(call_tool_result=call_tool_result)
    assert summary is not None
    assert len(summary) > 500
    write_summary_to_file(summary=summary, owner=owner, repo=repo)
