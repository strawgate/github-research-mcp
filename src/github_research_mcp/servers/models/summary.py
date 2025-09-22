import asyncio
from logging import Logger
from typing import Self

from pydantic import BaseModel, Field, field_validator

from github_research_mcp.clients.github import FindFilePathsResult, GitHubResearchClient, SearchCodeResult
from github_research_mcp.clients.models.github import RepositoryFileWithContent, RepositoryFileWithLineMatches
from github_research_mcp.models.repository.tree import (
    RepositoryTree,
)

TRUNCATE_FILE_CONTENT_LINES = 500
TRUNCATE_FILE_CONTENT_CHARACTERS = 20000


class CodeKeywordsSearchRequest(BaseModel):
    """A request for a code keyword search."""

    keywords: list[str] = Field(
        description=(
            "Up to 6 keywords (words or phrases) to search for in the code files. "
            "All keywords must match exactly for an item to match and be returned in the search results. "
        )
    )

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: list[str]) -> list[str]:
        return v[:6]

    async def execute(self, research_client: GitHubResearchClient, owner: str, repo: str) -> "CodeKeywordsSearchResponse":
        search_code_result: SearchCodeResult = await research_client.search_code_by_keywords(
            owner=owner,
            repo=repo,
            keywords=set(self.keywords),
        )
        return CodeKeywordsSearchResponse(**self.model_dump(), matches=search_code_result.matches)

    @classmethod
    def prune_requests(cls, requests: list[Self] | None, limit_requests: int) -> list[Self]:
        if requests is None:
            return []

        return requests[:limit_requests]


class CodeKeywordsSearchResponse(CodeKeywordsSearchRequest):
    """A response to a code keyword search request."""

    matches: list[RepositoryFileWithLineMatches] = Field(description="The matches from the code keyword search.")


class FetchFileContentsRequest(BaseModel):
    """A request for a file from the repository. The suffixes are joined against the path prefix to form the file paths.
    Suffixes can be a file name or a path relative to the path prefix.

    Do not request more files than you have been given permission to request. For files at the root, leave the `path_prefix` null.

    Note: A request with zero path_suffixes will be ignored.
    """

    path_prefix: str | None = Field(description="A common path prefix for the files to get the content of.")
    path_suffixes: list[str] = Field(
        description=("The names or paths relative to the `path_prefix` of the files to get the content of. Must not be empty.")
    )

    @property
    def file_paths(self) -> list[str]:
        return [f"{self.path_prefix}/{file}" for file in self.path_suffixes] if self.path_prefix else self.path_suffixes

    async def execute(self, research_client: GitHubResearchClient, owner: str, repo: str) -> "FetchFileContentsResponse":
        files: list[RepositoryFileWithContent] = await research_client.get_files(
            owner=owner,
            repo=repo,
            paths=self.file_paths,
            truncate_lines=TRUNCATE_FILE_CONTENT_LINES,
            truncate_characters=TRUNCATE_FILE_CONTENT_CHARACTERS,
        )
        return FetchFileContentsResponse(**self.model_dump(), files=files)

    @classmethod
    def prune_requests(
        cls, requests: list[Self] | None, limit_total_files: int, repository_tree: RepositoryTree, already_fetched_files: list[str]
    ) -> list[Self]:
        if requests is None:
            return []

        keep_requests: list[Self] = []

        all_files_in_tree: list[str] = repository_tree.file_paths()

        for request in requests:
            current_count = sum([len(request.file_paths) for request in keep_requests])
            remaining_limit = limit_total_files - current_count

            relevant_path_suffixes: list[str] = []

            for path_suffix in request.path_suffixes:
                path = f"{request.path_prefix}/{path_suffix}" if request.path_prefix else path_suffix

                if path not in already_fetched_files and path in all_files_in_tree:
                    relevant_path_suffixes.append(path_suffix)

            if len(relevant_path_suffixes) + current_count > limit_total_files:
                keep_requests.append(request.model_copy(update={"path_suffixes": relevant_path_suffixes[:remaining_limit]}))
                break

            keep_requests.append(request.model_copy(update={"path_suffixes": relevant_path_suffixes}))

        return keep_requests


class FetchFileContentsResponse(FetchFileContentsRequest):
    files: list[RepositoryFileWithContent] = Field(description="The files from the repository.")


class FindFilePathsRequest(BaseModel):
    """Search for files by their names/paths and return a list of matching file paths. Literal matches only, no regex or wildcards.
    Useful if the repository tree is limited to a specific depth. Returns only the file paths that match, does not return the file contents.

    And the following would find all files named `RequestService.java` or `RequestService.kt` regardless of their location in the repository
    ```json
    {
        "include": ["RequestService.java", "RequestService.kt"]
    }
    ```

    The following would return all yml files in the repository:
    ```json
    {
        "include": [".yml"]
    }
    ```

    To get all the files under the `src/main/java/com/example` directory, you could use the following:
    ```json
    {
        "include": ["src/main/java/com/example"]
    }
    ```
    """

    include: list[str] = Field(
        description=(
            "The file name or path fragments to include in the search. This is not regex and does not support wildcards."
            "Maximum of 5 include patterns."
        ),
    )
    exclude: list[str] | None = Field(
        default=None,
        description=(
            "An optional list of file name or path fragments to exclude from the search. If None, no files will be excluded. "
            "This is not regex and does not support wildcards."
            "Exclude patterns take precedence over include patterns."
            "Maximum of 5 exclude patterns."
        ),
    )

    @field_validator("include")
    @classmethod
    def validate_include(cls, v: list[str]) -> list[str]:
        # Remove any asterisks from the include patterns
        return [pattern.replace("*", "") for pattern in v][:5]

    @field_validator("exclude")
    @classmethod
    def validate_exclude(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        return [pattern.replace("*", "") for pattern in v][:5]

    async def execute(self, research_client: GitHubResearchClient, owner: str, repo: str) -> "FindFilePathsResponse":
        find_file_paths_result: FindFilePathsResult = await research_client.find_file_paths(
            owner=owner, repo=repo, include_patterns=self.include, exclude_patterns=self.exclude, limit_results=50
        )
        return FindFilePathsResponse(**self.model_dump(), found_file_paths=find_file_paths_result.matching_file_paths)

    @classmethod
    def prune_requests(cls, requests: list[Self] | None, limit_requests: int) -> list[Self]:
        if requests is None:
            return []

        return requests[:limit_requests]


class FindFilePathsResponse(FindFilePathsRequest):
    """A response to a file path search request."""

    found_file_paths: RepositoryTree = Field(description="The file paths found by the file path search.")


class InformationRequestForSummary(BaseModel):
    """A request for information from the repository."""

    code_keyword_searches: list[CodeKeywordsSearchRequest] | None = Field(
        default=None,
        description=(
            "An optional list of requests to search for code keywords in the repository. "
            "Each entry will return its own set of matches which match the keywords in the request."
        ),
    )
    find_file_paths: list[FindFilePathsRequest] | None = Field(
        default=None,
        description=(
            "An optional list of requests to locate files by their names/paths. "
            "Each entry will return its own set of file paths which match the include and exclude patterns in the request. "
        ),
    )
    fetch_file_contents: list[FetchFileContentsRequest] | None = Field(
        default=None,
        description=(
            "An optional list of requests to fetch files from the repository. "
            "Each entry will return its own set of files which match the path prefixes and path suffixes in the request."
        ),
    )

    async def gather(
        self,
        research_client: GitHubResearchClient,
        owner: str,
        repo: str,
        repository_tree: RepositoryTree,
        already_fetched_files: list[str],
        limit_fetch_files: int,
        limit_code_keywords_searches: int,
        limit_find_file_paths: int,
        logger: Logger,
    ) -> tuple[list[FetchFileContentsResponse], list[CodeKeywordsSearchResponse], list[FindFilePathsResponse]]:
        fetch_file_requests: list[FetchFileContentsRequest] = FetchFileContentsRequest.prune_requests(
            requests=self.fetch_file_contents,
            limit_total_files=limit_fetch_files,
            repository_tree=repository_tree,
            already_fetched_files=already_fetched_files,
        )
        code_keyword_searches_requests: list[CodeKeywordsSearchRequest] = CodeKeywordsSearchRequest.prune_requests(
            requests=self.code_keyword_searches,
            limit_requests=limit_code_keywords_searches,
        )
        find_file_paths_requests: list[FindFilePathsRequest] = FindFilePathsRequest.prune_requests(
            requests=self.find_file_paths,
            limit_requests=limit_find_file_paths,
        )
        msg = (
            f"Gathering information for request for {owner}/{repo}: "
            f"Files to fetch: {fetch_file_requests}, "
            f"Code keyword searches: {code_keyword_searches_requests}, "
            f"File paths to find: {find_file_paths_requests}"
        )

        logger.info(msg)

        async with asyncio.TaskGroup() as task_group:
            fetch_file_tasks = [
                task_group.create_task(request.execute(research_client=research_client, owner=owner, repo=repo))
                for request in fetch_file_requests
            ]
            code_keyword_searches_tasks = [
                task_group.create_task(request.execute(research_client=research_client, owner=owner, repo=repo))
                for request in code_keyword_searches_requests
            ]
            find_file_paths_tasks = [
                task_group.create_task(request.execute(research_client=research_client, owner=owner, repo=repo))
                for request in find_file_paths_requests
            ]

        fetch_file_results = get_results_log_exceptions(results=fetch_file_tasks, logger=logger)
        fetch_file_result_count = sum([len(fetch_file_result.files) for fetch_file_result in fetch_file_results])

        code_keyword_searches_results = get_results_log_exceptions(results=code_keyword_searches_tasks, logger=logger)
        code_keyword_searches_result_count = sum(
            [len(code_keyword_search_result.matches) for code_keyword_search_result in code_keyword_searches_results]
        )
        find_file_paths_results = get_results_log_exceptions(results=find_file_paths_tasks, logger=logger)
        find_file_paths_result_count = sum(
            [find_file_path_result.found_file_paths.count_files for find_file_path_result in find_file_paths_results]
        )

        msg = (
            f"Completed information request for {owner}/{repo}: "
            f"Fetched {fetch_file_result_count} files, "
            f"Found {code_keyword_searches_result_count} code keyword matches, "
            f"Found {find_file_paths_result_count} file paths"
        )

        logger.info(msg)

        return fetch_file_results, code_keyword_searches_results, find_file_paths_results


def get_result_log_exceptions[T](result: asyncio.Task[T], logger: Logger) -> T | None:
    try:
        return result.result()
    except Exception as e:
        logger.exception(f"Error getting result from task: {e}")
        return None


def get_results_log_exceptions[T](results: list[asyncio.Task[T]], logger: Logger) -> list[T]:
    task_results = [get_result_log_exceptions(result=result, logger=logger) for result in results]
    return [result for result in task_results if result is not None]
