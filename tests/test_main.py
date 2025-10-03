from collections.abc import AsyncGenerator
from typing import Any

import pytest
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from inline_snapshot import snapshot

from github_research_mcp.main import mcp
from tests.conftest import dump_list_for_snapshot


def test_main():
    assert mcp is not None


@pytest.fixture
async def main_mcp_client() -> AsyncGenerator[Client[FastMCPTransport], Any]:
    async with Client[FastMCPTransport](transport=mcp) as mcp_client:
        yield mcp_client


async def test_list_tools(main_mcp_client: Client[FastMCPTransport]):
    list_tools = await main_mcp_client.list_tools()
    assert dump_list_for_snapshot(list_tools, exclude_keys=["inputSchema", "outputSchema", "meta"]) == snapshot(
        [
            {
                "name": "get_repository",
                "description": "Get high-level information about a GitHub repository like the name, description, and other metadata.",
            },
            {"name": "get_issue", "description": "Get an issue."},
            {
                "name": "get_pull_request",
                "description": "Get a pull request. Pull request bodies, comment bodies, and related items are truncated to reduce the response size but can be retrieved using the `get_pull_request` tool.",
            },
            {"name": "get_pull_request_diff", "description": "Get the diff from a pull request."},
            {
                "name": "search_issues",
                "description": "Search for issues in a GitHub repository by the provided keywords. Issue bodies, comment bodies, and related items are truncated to reduce the response size but can be retrieved using the `get_issue` tool.",
            },
            {"name": "search_pull_requests", "description": "Search for pull requests in a GitHub repository by the provided keywords."},
            {
                "name": "get_readmes",
                "description": """\
Retrieve any asciidoc (.adoc, .asciidoc), markdown (.md, .markdown), and other text files (.txt, .rst) in the repository.

If files are fetched recursively, the files at the root of the repository will be prioritized.\
""",
            },
            {
                "name": "get_file_extension_statistics",
                "description": "Count the different file extensions found in a GitHub repository to identify the most common file types.",
            },
            {"name": "get_file", "description": "Get a file from the main branch of a repository."},
            {"name": "get_files", "description": "Get multiple files from the main branch of a repository (up to 20 files)."},
            {"name": "find_files", "description": "Find files (names/paths, not contents!) in the repository."},
            {
                "name": "search_code",
                "description": """\
Search the code in the default branch of the repository.

Up to 5 matches per file will be returned, Search is not case-sensitive, and up to 4 lines of context will
be returned before and after the match. Globs are similar to the globs used with `grep` on the command line.

`Patterns` are searched in the contents of the code. Do not use patterns to search for file paths or file names.

For example, `python` will search for Python files, and `java` will search for Java files.
If not provided, common types are excluded by default (binary files, lock files, etc).\
""",
            },
            {
                "name": "get_file_types_for_search",
                "description": """\
Get the list of file types that can be used in the `include_types` and `exclude_types` arguments of a
code search or find files.\
""",
            },
            {"name": "summarize_repository"},
        ]
    )
