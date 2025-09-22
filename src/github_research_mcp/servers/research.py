from logging import Logger
from typing import TYPE_CHECKING, Annotated, Any

from fastmcp.server import FastMCP
from fastmcp.tools import Tool
from fastmcp.tools.tool_transform import ArgTransform, TransformedTool
from fastmcp.utilities.logging import get_logger
from pydantic import Field

from github_research_mcp.clients.github import GitHubResearchClient
from github_research_mcp.clients.models.github import RepositoryFileWithContent
from github_research_mcp.models.repository.tree import RepositoryFileCountEntry, RepositoryTree
from github_research_mcp.servers.shared.annotations import (
    FIND_FILES_DEPTH_ARG_TRANSFORM,
    LIMIT_COMMENTS_ARG_TRANSFORM,
    LIMIT_RELATED_ITEMS_ARG_TRANSFORM,
    OWNER,
    OWNER_ARG_TRANSFORM,
    REPO,
    REPO_ARG_TRANSFORM,
    TRUNCATE_CHARACTERS,
    TRUNCATE_CHARACTERS_ARG_TRANSFORM,
    TRUNCATE_LINES,
    TRUNCATE_LINES_ARG_TRANSFORM,
)

if TYPE_CHECKING:
    from github_research_mcp.clients.github import FindFilePathsResult

DEFAULT_TRUNCATE_LINES = 500
DEFAULT_TRUNCATE_CHARACTERS = 20000
DEFAULT_TOP_N_EXTENSIONS = 50
DEFAULT_README_LIMIT = 20

DEFAULT_LIMIT_GET_ISSUE_COMMENTS = 50
DEFAULT_LIMIT_GET_ISSUE_RELATED_ITEMS = 10

DEFAULT_LIMIT_GET_PULL_REQUEST_COMMENTS = 50
DEFAULT_LIMIT_GET_PULL_REQUEST_RELATED_ITEMS = 10

DEFAULT_LIMIT_SEARCH_ISSUES = 50
DEFAULT_LIMIT_SEARCH_ISSUE_COMMENTS = 50
DEFAULT_LIMIT_SEARCH_ISSUE_RELATED_ITEMS = 10

DEFAULT_LIMIT_SEARCH_PULL_REQUESTS = 50
DEFAULT_LIMIT_SEARCH_PULL_REQUEST_COMMENTS = 50
DEFAULT_LIMIT_SEARCH_PULL_REQUEST_RELATED_ITEMS = 10


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
        passthrough_tools = self.passthrough_tools()

        for tool in passthrough_tools:
            fastmcp.add_tool(tool=tool)

        fastmcp.add_tool(tool=Tool.from_function(fn=self.get_readmes))
        fastmcp.add_tool(tool=Tool.from_function(fn=self.get_file_extension_statistics))

        return fastmcp

    def passthrough_tools(self) -> list[Tool]:
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
            description="Search for issues in a GitHub repository by the provided keywords.",
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
            description="Get a pull request.",
            transform_args={
                **owner_repo_args,
                "pull_request_number": description(
                    "The number of the GitHub pull request to get. Will return an error if called on an Issue."
                ),
                **limits_args,
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
                "include_pull_request_diff": description("Whether to include the diff of the pull request in the search results."),
            },
        )

        get_files_tool = TransformedTool.from_tool(
            tool=Tool.from_function(fn=self.research_client.get_files),
            description="Get the contents of files from a GitHub repository, optionally truncating the content.",
            transform_args={
                **owner_repo_args,
                "paths": description("The full paths of the files (i.e: `README.md`, `docs/index.md`) to retrieve the contents of."),
                "truncate_lines": TRUNCATE_LINES_ARG_TRANSFORM,
                "truncate_characters": TRUNCATE_CHARACTERS_ARG_TRANSFORM,
                **error_on_not_found_args,
            },
        )

        find_files_tool = TransformedTool.from_tool(
            tool=Tool.from_function(fn=self.research_client.find_file_paths),
            description="Find files in a GitHub repository by their names/paths.",
            transform_args={
                **owner_repo_args,
                "include_patterns": description(
                    "The patterns to check file paths against. File paths matching any of these patterns will be included in the results."
                ),
                "exclude_patterns": description(
                    "The patterns to check file paths against. "
                    "File paths matching any of these patterns will be excluded from the results. "
                    "If None, no files will be excluded. Exclude patterns take precedence over include patterns."
                ),
                "include_exclude_is_regex": description("Whether the include and exclude patterns provided should be evaluated as regex."),
                "depth": FIND_FILES_DEPTH_ARG_TRANSFORM,
            },
        )

        search_code_tool = TransformedTool.from_tool(
            tool=Tool.from_function(fn=self.research_client.search_code_by_keywords),
            description="Search for code in a GitHub repository by the provided keywords.",
            transform_args={
                **owner_repo_args,
                "keywords": description("The keywords to use to search for code."),
            },
        )

        return [
            get_repository_tool,
            get_issue_tool,
            get_pull_request_tool,
            search_issues_tool,
            search_pull_requests_tool,
            get_files_tool,
            find_files_tool,
            search_code_tool,
        ]

    async def get_readmes(
        self,
        owner: OWNER,
        repo: REPO,
        depth: Annotated[int, "The depth of the tree to search for readmes. If not provided, only the root directory will be searched."]
        | None = None,
        truncate_lines: TRUNCATE_LINES = DEFAULT_TRUNCATE_LINES,
        truncate_characters: TRUNCATE_CHARACTERS = DEFAULT_TRUNCATE_CHARACTERS,
        limit_results: int = DEFAULT_README_LIMIT,
    ) -> list[RepositoryFileWithContent]:
        """Retrieve any asciidoc (.adoc, .asciidoc), markdown (.md, .markdown), and other text files (.txt, .rst) in the repository.

        If files are fetched recursively, the files at the root of the repository will be prioritized."""

        find_file_paths_result: FindFilePathsResult = await self.research_client.find_file_paths(
            owner=owner,
            repo=repo,
            include_patterns=[".md", ".markdown", ".adoc", ".asciidoc", ".txt", ".rst"],
            exclude_patterns=[],
            depth=depth or 0,
        )

        file_paths: list[str] = find_file_paths_result.matching_file_paths.file_paths()[:limit_results]

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
