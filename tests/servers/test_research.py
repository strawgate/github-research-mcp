from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

import pytest
from fastmcp.client import Client, FastMCPTransport
from fastmcp.server import FastMCP
from inline_snapshot import snapshot

from github_research_mcp.clients.github import GitHubResearchClient
from github_research_mcp.servers.research import ResearchServer
from tests.conftest import (
    E2EIssue,
    E2EPullRequest,
    E2ERepository,
    E2ERepositoryFiles,
    dump_call_tool_result_for_snapshot,
    dump_list_for_snapshot,
    dump_structured_content_for_snapshot,
)

if TYPE_CHECKING:
    from fastmcp.client.client import CallToolResult


def test_init(github_research_client: GitHubResearchClient) -> None:
    research_server = ResearchServer(research_client=github_research_client)
    assert research_server is not None


@pytest.fixture
def research_server(github_research_client: GitHubResearchClient) -> ResearchServer:
    return ResearchServer(research_client=github_research_client)


@pytest.fixture
def research_mcp(fastmcp: FastMCP, research_server: ResearchServer) -> FastMCP[Any]:
    return research_server.register_tools(fastmcp=fastmcp)


@pytest.fixture
async def research_mcp_client(research_mcp: FastMCP[Any]) -> AsyncGenerator[Client[FastMCPTransport], Any]:
    async with Client[FastMCPTransport](transport=research_mcp) as research_mcp_client:
        list_tools = await research_mcp_client.list_tools()
        assert list_tools is not None

        yield research_mcp_client


async def test_list_tools(research_mcp_client: Client[FastMCPTransport]) -> None:
    list_tools = await research_mcp_client.list_tools()
    assert dump_list_for_snapshot(list_tools, exclude_keys=["inputSchema", "outputSchema", "meta"]) == snapshot(
        [
            {
                "name": "get_repository",
                "description": "Get high-level information about a GitHub repository like the name, description, and other metadata.",
            },
            {"name": "get_issue", "description": "Get an issue."},
            {"name": "get_pull_request", "description": "Get a pull request."},
            {"name": "search_issues", "description": "Search for issues in a GitHub repository by the provided keywords."},
            {
                "name": "search_pull_requests",
                "description": "Search for pull requests in a GitHub repository by the provided keywords.",
            },
            {"name": "get_files", "description": "Get the contents of files from a GitHub repository, optionally truncating the content."},
            {
                "name": "find_file_paths",
                "description": "Find files in a GitHub repository by their names/paths. Does not search file contents.",
            },
            {"name": "search_code_by_keywords", "description": "Search for code in a GitHub repository by the provided keywords."},
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
        ]
    )


async def test_get_repository(research_mcp_client: Client[FastMCPTransport], e2e_repository: E2ERepository) -> None:
    result: CallToolResult = await research_mcp_client.call_tool(
        "get_repository",
        arguments={"owner": e2e_repository.owner, "repo": e2e_repository.repo},
    )
    assert dump_call_tool_result_for_snapshot(result) == snapshot(
        {
            "content": [
                {
                    "type": "text",
                    "text": '{"name":"github-issues-e2e-test","description":null,"fork":false,"url":"https://api.github.com/repos/strawgate/github-issues-e2e-test","stars":0,"homepage_url":null,"language":"Python","default_branch":"main","topics":[],"archived":false,"created_at":"2025-09-05T23:02:41Z","updated_at":"2025-09-10T03:25:10Z","pushed_at":"2025-09-10T03:25:06Z","license":null}',
                    "annotations": None,
                    "meta": None,
                }
            ],
            "structured_content": {
                "result": {
                    "name": "github-issues-e2e-test",
                    "description": None,
                    "fork": False,
                    "url": "https://api.github.com/repos/strawgate/github-issues-e2e-test",
                    "stars": 0,
                    "homepage_url": None,
                    "language": "Python",
                    "default_branch": "main",
                    "topics": [],
                    "archived": False,
                    "created_at": "2025-09-05T23:02:41Z",
                    "updated_at": "2025-09-10T03:25:10Z",
                    "pushed_at": "2025-09-10T03:25:06Z",
                    "license": None,
                }
            },
        }
    )


async def test_get_issue(research_mcp_client: Client[FastMCPTransport], e2e_issue: E2EIssue) -> None:
    result: CallToolResult = await research_mcp_client.call_tool(
        "get_issue",
        arguments={"owner": e2e_issue.owner, "repo": e2e_issue.repo, "issue_number": e2e_issue.issue_number},
    )
    assert dump_structured_content_for_snapshot(result) == snapshot(
        {
            "result": {
                "issue": {
                    "number": 14,
                    "url": "https://github.com/strawgate/github-issues-e2e-test/issues/14",
                    "title": "[FEATURE] Enhance `generate_philosophical_variable_name` with context",
                    "body": """\
## ✨ New Visions for the Digital Realm

*"Every feature is a new path, a new possibility in the journey of code."*

### Describe the Feature
The `generate_philosophical_variable_name` function in `src/utils.py` currently replaces keywords or adds a generic philosophical prefix. This is a good start, but it could be enhanced to consider the *context* of the variable's usage within the code.

For example, a variable named `count` in a loop might become `quantum_measurement_of_iteration`, while `count` in a database query might become `cosmic_tally_of_records`.

### Why is this Feature Needed?
Context-aware philosophical naming would provide more relevant and profound insights, deepening the existential coding experience. It moves beyond simple keyword replacement to a more nuanced understanding of the variable's role.

### Proposed Solution
- Modify `generate_philosophical_variable_name` to accept an additional `context` argument (e.g., the line of code where the variable is used, or the function it's within).
- Implement logic to analyze the context and choose a more appropriate philosophical mapping or prefix.
- This might involve simple regex matching for surrounding keywords (e.g., `for`, `while`, `db.query`).

### Philosophical Reflection
True understanding comes not just from the word itself, but from its relationship to the surrounding text. By considering context, we move closer to a holistic understanding of the code's essence, reflecting the interconnectedness of all things in the digital realm.

---

*Remember: Every feature is a step towards a more enlightened digital future. Embrace the creation, and the wisdom will follow.*\
""",
                    "state": "OPEN",
                    "state_reason": None,
                    "is_pr": False,
                    "author": {"user_type": "User", "login": "strawgate"},
                    "author_association": "OWNER",
                    "created_at": "2025-09-13T18:11:09+00:00",
                    "updated_at": "2025-09-13T18:11:09+00:00",
                    "closed_at": None,
                    "labels": [],
                    "assignees": [],
                    "owner": "strawgate",
                    "repository": "github-issues-e2e-test",
                },
                "comments": [],
                "related": [],
            }
        }
    )


async def test_get_pull_request(research_mcp_client: Client[FastMCPTransport], e2e_pull_request: E2EPullRequest) -> None:
    result: CallToolResult = await research_mcp_client.call_tool(
        "get_pull_request",
        arguments={
            "owner": e2e_pull_request.owner,
            "repo": e2e_pull_request.repo,
            "pull_request_number": e2e_pull_request.pull_request_number,
        },
    )
    assert dump_structured_content_for_snapshot(result) == snapshot(
        {
            "result": {
                "pull_request": {
                    "url": "https://github.com/strawgate/github-issues-e2e-test/pull/2",
                    "number": 2,
                    "title": "this is a test pull request",
                    "body": """\
it has a description\r
\r
it has a related issue #1\
""",
                    "state": "OPEN",
                    "is_pr": True,
                    "merged": False,
                    "author": {"user_type": "User", "login": "strawgate"},
                    "created_at": "2025-09-05T23:04:07+00:00",
                    "updated_at": "2025-09-05T23:04:24+00:00",
                    "closed_at": None,
                    "merged_at": None,
                    "merge_commit": None,
                    "labels": [{"name": "bug"}],
                    "assignees": [{"user_type": "User", "login": "strawgate"}],
                    "owner": "strawgate",
                    "repository": "github-issues-e2e-test",
                },
                "comments": [
                    {
                        "url": "https://github.com/strawgate/github-issues-e2e-test/pull/2#issuecomment-3259982958",
                        "body": "it also has a comment",
                        "author": {"user_type": "User", "login": "strawgate"},
                        "author_association": "OWNER",
                        "created_at": "2025-09-05T23:04:24+00:00",
                        "updated_at": "2025-09-05T23:04:24+00:00",
                        "owner": "strawgate",
                        "repository": "github-issues-e2e-test",
                        "issue_number": 2,
                        "comment_id": 3259982958,
                    }
                ],
                "related": [],
            }
        }
    )


async def test_find_file_paths(research_mcp_client: Client[FastMCPTransport], e2e_repository: E2ERepository) -> None:
    result: CallToolResult = await research_mcp_client.call_tool(
        "find_file_paths",
        arguments={
            "owner": e2e_repository.owner,
            "repo": e2e_repository.repo,
            "include_patterns": ["*README.md", "*CONTRIBUTORS.md"],
            "exclude_patterns": ["*.txt"],
        },
    )
    assert dump_structured_content_for_snapshot(result) == snapshot(
        {"directories": [], "files": ["CONTRIBUTORS.md", "README.md"], "truncated": False}
    )


async def test_get_files(research_mcp_client: Client[FastMCPTransport], e2e_files: E2ERepositoryFiles) -> None:
    result: CallToolResult = await research_mcp_client.call_tool(
        "get_files",
        arguments={
            "owner": e2e_files.owner,
            "repo": e2e_files.repo,
            "paths": e2e_files.paths,
            "truncate_lines": 10,
            "truncate_characters": 100,
        },
    )
    assert dump_call_tool_result_for_snapshot(result) == snapshot(
        {
            "content": [
                {
                    "type": "text",
                    "text": '[{"path":"README.md","content":{"1":"# G.I.T.H.U.B. - The Existential Code Companion","2":""},"total_lines":75,"truncated":false},{"path":"CONTRIBUTORS.md","content":{"1":"# Contributors","2":"","3":"This project exists thanks to all the people who contribute.","4":"","5":"## Core Team","6":""},"total_lines":37,"truncated":false}]',
                    "annotations": None,
                    "meta": None,
                }
            ],
            "structured_content": {
                "result": [
                    {
                        "path": "README.md",
                        "content": {"1": "# G.I.T.H.U.B. - The Existential Code Companion", "2": ""},
                        "total_lines": 75,
                        "truncated": False,
                    },
                    {
                        "path": "CONTRIBUTORS.md",
                        "content": {
                            "1": "# Contributors",
                            "2": "",
                            "3": "This project exists thanks to all the people who contribute.",
                            "4": "",
                            "5": "## Core Team",
                            "6": "",
                        },
                        "total_lines": 37,
                        "truncated": False,
                    },
                ]
            },
        }
    )


async def test_get_readmes(research_mcp_client: Client[FastMCPTransport], e2e_repository: E2ERepository) -> None:
    result: CallToolResult = await research_mcp_client.call_tool(
        "get_readmes",
        arguments={"owner": e2e_repository.owner, "repo": e2e_repository.repo, "truncate_lines": 10},
    )
    assert dump_structured_content_for_snapshot(result) == snapshot(
        {
            "result": [
                {
                    "path": "AGENTS.md",
                    "content": {
                        "1": "# G.I.T.H.U.B. AI Agents Documentation",
                        "2": "",
                        "3": '*"In the digital realm, we are not alone. Our code is watched over by digital spirits of wisdom and contemplation."*',
                        "4": "",
                        "5": "This document describes the existential AI agents and automated systems that guide your coding journey in G.I.T.H.U.B.",
                        "6": "",
                        "7": "## Agent Overview",
                        "8": "",
                        "9": "### The Philosopher Agent",
                        "10": "- **Purpose**: Existential code analysis and philosophical guidance",
                    },
                    "total_lines": 88,
                    "truncated": False,
                },
                {
                    "path": "CONTRIBUTING.md",
                    "content": {
                        "1": "# Contributing to G.I.T.H.U.B. - The Existential Code Companion",
                        "2": "",
                        "3": '*"Every contribution is a step on the path of digital enlightenment. Welcome, fellow seeker of code wisdom."*',
                        "4": "",
                        "5": "Thank you for your interest in contributing to G.I.T.H.U.B.! This document provides guidelines for those brave souls who wish to join us on this journey of existential coding.",
                        "6": "",
                        "7": "## Getting Started",
                        "8": "",
                        "9": "### Prerequisites",
                        "10": "- Python 3.13 or higher",
                    },
                    "total_lines": 105,
                    "truncated": False,
                },
                {
                    "path": "CONTRIBUTORS.md",
                    "content": {
                        "1": "# Contributors",
                        "2": "",
                        "3": "This project exists thanks to all the people who contribute.",
                        "4": "",
                        "5": "## Core Team",
                        "6": "",
                        "7": "- **Test User** - *Project Lead* - [@testuser](https://github.com/testuser)",
                        "8": "- **Jane Developer** - *Core Developer* - [@janedev](https://github.com/janedev)",
                        "9": "- **Bob Maintainer** - *Maintainer* - [@bobmaintainer](https://github.com/bobmaintainer)",
                        "10": "",
                    },
                    "total_lines": 37,
                    "truncated": False,
                },
                {
                    "path": "README.md",
                    "content": {
                        "1": "# G.I.T.H.U.B. - The Existential Code Companion",
                        "2": "",
                        "3": "**Generally Introspective Text Handler for Unrealized Brilliance**",
                        "4": "",
                        "5": "An AI-powered code editor extension that doesn't just check for syntax errors, but also prompts you with philosophical questions about your code's purpose and your life choices as a developer.",
                        "6": "",
                        "7": "## What is G.I.T.H.U.B.?",
                        "8": "",
                        "9": "G.I.T.H.U.B. is more than just another code linter. It's your existential coding companion that asks the deep questions:",
                        "10": "",
                    },
                    "total_lines": 75,
                    "truncated": False,
                },
            ]
        }
    )


async def test_get_file_extension_statistics(research_mcp_client: Client[FastMCPTransport], e2e_repository: E2ERepository) -> None:
    result: CallToolResult = await research_mcp_client.call_tool(
        "get_file_extension_statistics",
        arguments={"owner": e2e_repository.owner, "repo": e2e_repository.repo},
    )
    assert dump_structured_content_for_snapshot(result) == snapshot(
        {
            "result": [
                {"extension": "py", "count": 10},
                {"extension": "md", "count": 9},
                {"extension": "gitignore", "count": 1},
                {"extension": "python-version", "count": 1},
                {"extension": "ini", "count": 1},
                {"extension": "toml", "count": 1},
            ]
        }
    )


async def test_search_issues(research_mcp_client: Client[FastMCPTransport], e2e_repository: E2ERepository) -> None:
    result: CallToolResult = await research_mcp_client.call_tool(
        "search_issues",
        arguments={"owner": e2e_repository.owner, "repo": e2e_repository.repo, "keywords": ["philosophy"]},
    )
    assert dump_structured_content_for_snapshot(result) == snapshot(
        {
            "result": [
                {
                    "issue": {
                        "number": 6,
                        "url": "https://github.com/strawgate/github-issues-e2e-test/issues/6",
                        "title": "[ENLIGHTENMENT] The Illusion of Perfect Code",
                        "body": """\
## 🧘 Your Digital Enlightenment Journey

*"Every developer's journey is unique, but the destination is the same: understanding."*

### Your Journey
I often find myself striving for perfect code, spending hours on minor optimizations or refactoring that yields little practical benefit.

### Key Insights
I've realized that 'perfect' is a subjective and often unattainable goal in software development.

### Current State
My pursuit of perfection sometimes hinders progress and leads to burnout. The Zen Master's wisdom on 'Perfect code is an illusion; beautiful code is reality' resonates deeply.

### Future Aspirations
I aim to embrace the philosophy of 'beautiful code' over 'perfect code', focusing on maintainability, readability, and functionality while accepting inherent imperfections.

### Advice for Others
How do others balance the desire for perfection with the need for progress? What practices help in letting go of the pursuit of an unattainable ideal?

---

*Remember: Every journey is valid, every insight is valuable, and every step forward is progress on the path to digital enlightenment.*\
""",
                        "state": "OPEN",
                        "state_reason": None,
                        "is_pr": False,
                        "author": {"user_type": "User", "login": "strawgate"},
                        "author_association": "OWNER",
                        "created_at": "2025-09-13T18:10:37+00:00",
                        "updated_at": "2025-09-13T18:10:37+00:00",
                        "closed_at": None,
                        "labels": [],
                        "assignees": [],
                        "owner": "strawgate",
                        "repository": "github-issues-e2e-test",
                    },
                    "comments": [],
                    "related": [],
                }
            ]
        }
    )


async def test_search_pull_requests(research_mcp_client: Client[FastMCPTransport], e2e_repository: E2ERepository) -> None:
    result: CallToolResult = await research_mcp_client.call_tool(
        "search_pull_requests",
        arguments={"owner": e2e_repository.owner, "repo": e2e_repository.repo, "keywords": ["test"]},
    )
    assert dump_structured_content_for_snapshot(result) == snapshot(
        {
            "result": [
                {
                    "pull_request": {
                        "url": "https://github.com/strawgate/github-issues-e2e-test/pull/2",
                        "number": 2,
                        "title": "this is a test pull request",
                        "body": """\
it has a description\r
\r
it has a related issue #1\
""",
                        "state": "OPEN",
                        "is_pr": True,
                        "merged": False,
                        "author": {"user_type": "User", "login": "strawgate"},
                        "created_at": "2025-09-05T23:04:07+00:00",
                        "updated_at": "2025-09-05T23:04:24+00:00",
                        "closed_at": None,
                        "merged_at": None,
                        "merge_commit": None,
                        "labels": [{"name": "bug"}],
                        "assignees": [{"user_type": "User", "login": "strawgate"}],
                        "owner": "strawgate",
                        "repository": "github-issues-e2e-test",
                    },
                    "comments": [
                        {
                            "url": "https://github.com/strawgate/github-issues-e2e-test/pull/2#issuecomment-3259982958",
                            "body": "it also has a comment",
                            "author": {"user_type": "User", "login": "strawgate"},
                            "author_association": "OWNER",
                            "created_at": "2025-09-05T23:04:24+00:00",
                            "updated_at": "2025-09-05T23:04:24+00:00",
                            "owner": "strawgate",
                            "repository": "github-issues-e2e-test",
                            "issue_number": 2,
                            "comment_id": 3259982958,
                        }
                    ],
                    "related": [],
                }
            ]
        }
    )
