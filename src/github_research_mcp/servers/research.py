from logging import Logger
from typing import Annotated, Any

from fastmcp.server import FastMCP
from fastmcp.tools import Tool
from fastmcp.tools.tool_transform import ArgTransform, TransformedTool
from fastmcp.utilities.logging import get_logger
from pydantic import Field

from github_research_mcp.clients.github import GitHubResearchClient
from github_research_mcp.clients.models.github import RepositoryFileWithContent
from github_research_mcp.models.repository.tree import RepositoryFileCountEntry, RepositoryTree
from github_research_mcp.servers.shared.annotations import (
    LIMIT_COMMENTS_ARG_TRANSFORM,
    LIMIT_RELATED_ITEMS_ARG_TRANSFORM,
    OWNER,
    OWNER_ARG_TRANSFORM,
    REPO,
    REPO_ARG_TRANSFORM,
    TRUNCATE_CHARACTERS,
    TRUNCATE_LINES,
)

DEFAULT_TRUNCATE_README_LINES = 2000
DEFAULT_TRUNCATE_README_CHARACTERS = 60000
DEFAULT_TOP_N_EXTENSIONS = 50
DEFAULT_README_LIMIT = 20


def description(description: str, /) -> ArgTransform:
    return ArgTransform(description=description)


def hide() -> ArgTransform:
    return ArgTransform(hide=True)


class ResearchServer:
    research_client: GitHubResearchClient
    logger: Logger

    def __init__(self, research_client: GitHubResearchClient | None = None, logger: Logger | None = None):
        self.logger = logger or get_logger(name=__name__)
        self.research_client = research_client or GitHubResearchClient()

    def register_tools(self, fastmcp: FastMCP[Any]) -> FastMCP[Any]:
        for tool in self.passthrough_tools().values():
            _ = fastmcp.add_tool(tool=tool)

        _ = fastmcp.add_tool(tool=Tool.from_function(fn=self.get_readmes))
        _ = fastmcp.add_tool(tool=Tool.from_function(fn=self.get_file_extension_statistics))

        return fastmcp

    def passthrough_tools(self) -> dict[str, TransformedTool]:
        owner_repo_args = {
            "owner": OWNER_ARG_TRANSFORM,
            "repo": REPO_ARG_TRANSFORM,
        }

        error_on_not_found_args = {
            "error_on_not_found": hide(),
        }

        get_repository_tool = TransformedTool.from_tool(
            tool=Tool.from_function(fn=self.research_client.get_repository),
            description="Get high-level information about a GitHub repository like the name, description, and other metadata.",
            transform_args={
                **owner_repo_args,
                **error_on_not_found_args,
            },
        )

        limits_args = {
            "limit_comments": LIMIT_COMMENTS_ARG_TRANSFORM,
            "limit_related_items": LIMIT_RELATED_ITEMS_ARG_TRANSFORM,
        }

        get_issue_tool = TransformedTool.from_tool(
            tool=Tool.from_function(fn=self.research_client.get_issue),
            description="Get an issue.",
            transform_args={
                **owner_repo_args,
                "issue_number": description("The number of the GitHub issue to get. Will return an error if called on a Pull Request."),
                **limits_args,
                **error_on_not_found_args,
            },
        )

        search_issues_tool = TransformedTool.from_tool(
            tool=Tool.from_function(fn=self.research_client.search_issues_by_keywords),
            name="search_issues",
            description="Search for issues in a GitHub repository by the provided keywords. "
            + "Issue bodies, comment bodies, and related items are truncated to reduce the response size but can be retrieved "
            + "using the `get_issue` tool.",
            transform_args={
                **owner_repo_args,
                "keywords": description("The keywords to use to search for issues."),
                "all_keywords": description("Whether all keywords must be present for a result to appear in the search results."),
                **limits_args,
                "limit_issues": description("The maximum number of issues to include in the search results."),
            },
        )

        get_pull_request_tool = TransformedTool.from_tool(
            tool=Tool.from_function(fn=self.research_client.get_pull_request),
            description="Get a pull request. "
            + "Pull request bodies, comment bodies, and related items are truncated to reduce the response size but can be retrieved "
            + "using the `get_pull_request` tool.",
            transform_args={
                **owner_repo_args,
                "pull_request_number": description(
                    "The number of the GitHub pull request to get. Will return an error if called on an Issue."
                ),
                **limits_args,
                **error_on_not_found_args,
            },
        )

        get_pull_request_diff_tool = TransformedTool.from_tool(
            tool=Tool.from_function(fn=self.research_client.get_pull_request_diff),
            description="Get the diff from a pull request.",
            transform_args={
                **owner_repo_args,
                "pull_request_number": description("The number of the GitHub pull request to get the diff of."),
                **error_on_not_found_args,
            },
        )

        search_pull_requests_tool = TransformedTool.from_tool(
            tool=Tool.from_function(fn=self.research_client.search_pull_requests_by_keywords),
            name="search_pull_requests",
            description="Search for pull requests in a GitHub repository by the provided keywords.",
            transform_args={
                **owner_repo_args,
                "keywords": description("The keywords to use to search for pull requests."),
                "all_keywords": description("Whether all keywords must be present for a result to appear in the search results."),
                **limits_args,
                "limit_pull_requests": description("The maximum number of pull requests to include in the search results."),
            },
        )

        return {
            tool.name: tool
            for tool in [
                get_repository_tool,
                get_issue_tool,
                get_pull_request_tool,
                get_pull_request_diff_tool,
                search_issues_tool,
                search_pull_requests_tool,
            ]
        }

    async def get_readmes(
        self,
        owner: OWNER,
        repo: REPO,
        depth: Annotated[int, "The depth of the tree to search for readmes. If not provided, only the root directory will be searched."]
        | None = None,
        truncate_lines: TRUNCATE_LINES = DEFAULT_TRUNCATE_README_LINES,
        truncate_characters: TRUNCATE_CHARACTERS = DEFAULT_TRUNCATE_README_CHARACTERS,
        limit_results: int = DEFAULT_README_LIMIT,
    ) -> list[RepositoryFileWithContent]:
        """Retrieve any asciidoc (.adoc, .asciidoc), markdown (.md, .markdown), and other text files (.txt, .rst) in the repository.

        If files are fetched recursively, the files at the root of the repository will be prioritized."""

        find_file_paths_result: RepositoryTree = await self.research_client.find_file_paths(
            owner=owner,
            repo=repo,
            include_patterns=["*.md", "*.markdown", "*.adoc", "*.asciidoc", "*.txt", "*.rst"],
            exclude_patterns=[],
            depth=depth or 0,
        )

        file_paths: list[str] = find_file_paths_result.file_paths()[:limit_results]

        files: list[RepositoryFileWithContent] = await self.research_client.get_files(owner=owner, repo=repo, paths=file_paths)

        return [file.truncate(truncate_lines=truncate_lines, truncate_characters=truncate_characters) for file in files]

    async def get_file_extension_statistics(
        self,
        owner: OWNER,
        repo: REPO,
        top_n: Annotated[int, Field(description="The number of top extensions to return.")] = DEFAULT_TOP_N_EXTENSIONS,
    ) -> list[RepositoryFileCountEntry]:
        """Count the different file extensions found in a GitHub repository to identify the most common file types."""

        repository_tree: RepositoryTree = await self.research_client.get_repository_tree(owner=owner, repo=repo)

        return repository_tree.count_file_extensions(top_n=top_n)
