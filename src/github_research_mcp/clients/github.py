import asyncio
import os
from collections.abc import Awaitable, Callable, Sequence
from logging import Logger, getLogger
from typing import TYPE_CHECKING, Any, Literal, overload

from githubkit import GitHub as GitHubKit
from githubkit.auth.token import TokenAuthStrategy
from githubkit.exception import GitHubException as GitHubKitGitHubException
from githubkit.exception import GraphQLFailed as GitHubKitGraphQLFailed
from githubkit.exception import RequestFailed as GitHubKitRequestFailed
from githubkit.response import Response
from githubkit.response import Response as GitHubKitResponse
from githubkit.retry import RetryChainDecision, RetryRateLimit, RetryServerError
from githubkit.versions.v2022_11_28.models import ContentFile as GitHubKitContentFile
from pydantic import BaseModel

from github_research_mcp.clients.errors.github import RequestError, ResourceNotFoundError, ResourceTypeMismatchError
from github_research_mcp.clients.models.github import (
    GitReference,
    PullRequestDiff,
    Repository,
    RepositoryFileWithContent,
    RepositoryFileWithLineMatches,
)
from github_research_mcp.models.graphql.base import BaseGqlQuery
from github_research_mcp.models.graphql.issue_or_pull_request import (
    GqlGetIssue,
    GqlGetPullRequest,
    GqlIssueWithDetails,
    GqlPullRequestWithDetails,
    GqlSearchIssues,
    GqlSearchPullRequests,
)
from github_research_mcp.models.repository.tree import FilteredRepositoryTree, PrunedRepositoryTree, RepositoryTree

if TYPE_CHECKING:
    from types import CoroutineType

    from githubkit.versions.v2022_11_28.models import GitTree as GitHubKitGitTree
    from githubkit.versions.v2022_11_28.models import SearchCodeGetResponse200 as GitHubKitSearchCodeGetResponse200

NOT_FOUND_ERROR = 404

GITHUBKIT_RESPONSE_TYPE = BaseModel | Sequence[BaseModel]


def escape_keywords(keywords: set[str]) -> list[str]:
    # escape backslashes with more backslashes
    escaped_keywords = [keyword.replace("\\", "\\\\") for keyword in keywords]

    # escape quotes with backslashes
    escaped_keywords = [keyword.replace('"', '\\"') for keyword in escaped_keywords]

    return [f'"{keyword}"' for keyword in escaped_keywords]


def build_query(
    owner: str, repo: str, keywords: set[str], is_issue: bool = False, is_pull_request: bool = False, all_keywords: bool = False
) -> str:
    query_parts: list[str] = [
        f"repo:{owner}/{repo}",
    ]

    if is_issue:
        query_parts.append("is:issue")
    elif is_pull_request:
        query_parts.append("is:pr")

    # Wrap and escape keywords

    escaped_keywords = escape_keywords(keywords)

    if len(escaped_keywords) == 1:
        query_parts.append(escaped_keywords[0])
    elif all_keywords:
        query_parts.append("(" + " AND ".join(escaped_keywords) + ")")
    else:
        query_parts.append("(" + " OR ".join(escaped_keywords) + ")")

    return " ".join(query_parts)


def extract_response[T: GITHUBKIT_RESPONSE_TYPE](response: Response[T], /) -> T:
    """Extract the response from a response."""

    return response.parsed_data


TRUNCATION_MARKER = "... [the middle portion has been truncated, retrieve object directly to get the full body]"


def get_github_token() -> str:
    env_vars: set[str] = {"GITHUB_TOKEN", "GITHUB_PERSONAL_ACCESS_TOKEN"}
    for env_var in env_vars:
        if env_var in os.environ:
            return os.environ[env_var]
    msg = "GITHUB_TOKEN or GITHUB_PERSONAL_ACCESS_TOKEN must be set"
    raise ValueError(msg)


def get_githubkit_client() -> GitHubKit[Any]:
    # Retry server errors up to 3 times
    retry_server_error = RetryServerError()

    # Retry rate limit errors up to 2 times
    retry_rate_limit = RetryRateLimit(max_retry=3)

    retry_chain = RetryChainDecision(
        retry_server_error,
        retry_rate_limit,
    )

    return GitHubKit[TokenAuthStrategy](auth=TokenAuthStrategy(token=get_github_token()), auto_retry=retry_chain)


DEFAULT_ISSUE_COMMENTS_LIMIT = 5
DEFAULT_ISSUE_RELATED_ITEMS_LIMIT = 5
DEFAULT_ISSUES_OR_PULL_REQUESTS_LIMIT = 20
DEFAULT_ISSUE_BODY_SIZE = 1600
DEFAULT_COMMENT_BODY_SIZE = 600

DEFAULT_TRUNCATE_LINES = 300
DEFAULT_TRUNCATE_CHARACTERS = 4000

DEFAULT_FIND_FILES_LIMIT = 100


def trim_body(body: str, max_length: int) -> str:
    """If the body is longer than the max length, we take the first max_length / 2 characters and the last max_length / 2 characters."""

    if len(body) > max_length:
        first_half = body[: max_length // 2]
        middle_truncated_marker = TRUNCATION_MARKER + " ... "
        last_half = body[-max_length // 2 :]
        return (first_half + "\n\n" + middle_truncated_marker + "\n\n" + last_half).strip()

    return body.strip()


def trim_comment_body(body: str, max_length: int) -> str:
    """If the body is longer than the max length, we take the first max_length / 2 characters and the last max_length / 2 characters."""
    return trim_body(body, max_length)


class GitHubResearchClient:
    githubkit_client: GitHubKit[Any]
    logger: Logger

    log_requests: bool
    log_responses: bool
    log_on_error: bool

    def __init__(
        self,
        githubkit_client: GitHubKit[Any] | None = None,
        logger: Logger | None = None,
        log_requests: bool = True,
        log_responses: bool = False,
        log_on_error: bool = True,
    ):
        self.githubkit_client = githubkit_client or get_githubkit_client()
        self.logger = logger or getLogger(__name__)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_on_error = log_on_error

    def _get_loggers(
        self, log_request: bool | None = None, log_response: bool | None = None, log_on_error: bool | None = None
    ) -> tuple[Callable[[str], Any], Callable[[str], Any], Callable[[BaseException | str], Any]]:
        request_logger = self.logger.info if log_request or self.log_requests else self.logger.debug
        response_logger = self.logger.info if log_response or self.log_responses else self.logger.debug
        error_logger = self.logger.exception if log_on_error or self.log_on_error else self.logger.debug
        return request_logger, response_logger, error_logger

    @overload
    async def _perform_graphql_query[T: BaseGqlQuery](
        self,
        query_model: type[T],
        variables: dict[str, Any],
        log_request: bool | None = None,
        log_response: bool | None = None,
        log_on_error: bool | None = None,
        error_on_not_found: Literal[True] = True,
    ) -> T: ...

    @overload
    async def _perform_graphql_query[T: BaseGqlQuery](
        self,
        query_model: type[T],
        variables: dict[str, Any],
        log_request: bool | None = None,
        log_response: bool | None = None,
        log_on_error: bool | None = None,
        error_on_not_found: Literal[False] = False,
    ) -> T | None: ...

    async def _perform_graphql_query[T: BaseGqlQuery](
        self,
        query_model: type[T],
        variables: dict[str, Any],
        log_request: bool | None = None,
        log_response: bool | None = None,
        log_on_error: bool | None = None,
        error_on_not_found: bool | None = None,
    ) -> T | None:
        """Perform a GraphQL query and return the response as a model."""

        request_logger, response_logger, error_logger = self._get_loggers(
            log_request=log_request, log_response=log_response, log_on_error=log_on_error
        )

        request_logger(f"Executing GraphQL query {query_model.__name__} with variables {variables}")

        try:
            raw_response = await self.githubkit_client.async_graphql(
                query=query_model.graphql_query(),
                variables=variables,
            )
        except GitHubKitGraphQLFailed as e:
            if errors := e.response.errors:
                messages = ". ".join([error.message for error in errors])

                if any(error.type == "NOT_FOUND" for error in errors):
                    if error_on_not_found:
                        error_logger(
                            f"Resource not found executing GraphQL query {query_model.__name__} with variables {variables}: {messages}"
                        )
                        raise ResourceNotFoundError(action=f"Get {query_model.__name__}", extra_info={"graphql_errors": messages}) from e

                    return None

                error_logger(f"Error executing GraphQL query {query_model.__name__} with variables {variables}: {messages}")

                raise RequestError(action=f"Get {query_model.__name__}", extra_info={"graphql_errors": messages}) from e

            raise RequestError(action=f"Get {query_model.__name__}", message="Unknown error: " + str(e)) from e

        response_logger(f"Completed GraphQL query {query_model.__name__} for with variables {variables}.")

        return query_model.model_validate(raw_response)

    @overload
    async def _perform_rest_request[T: GITHUBKIT_RESPONSE_TYPE](
        self,
        action: str,
        log_request: bool | None = None,
        log_response: bool | None = None,
        log_on_error: bool | None = None,
        error_on_not_found: Literal[False] = False,
        *,
        method: Callable[..., Awaitable[GitHubKitResponse[T]]],
        **request_args: Any,  # pyright: ignore[reportAny]
    ) -> T | None: ...

    @overload
    async def _perform_rest_request[T: GITHUBKIT_RESPONSE_TYPE](
        self,
        action: str,
        log_request: bool | None = None,
        log_response: bool | None = None,
        log_on_error: bool | None = None,
        error_on_not_found: Literal[True] = True,
        *,
        method: Callable[..., Awaitable[GitHubKitResponse[T]]],
        **request_args: Any,  # pyright: ignore[reportAny]
    ) -> T: ...

    async def _perform_rest_request[T: GITHUBKIT_RESPONSE_TYPE](
        self,
        action: str,
        log_request: bool | None = None,
        log_response: bool | None = None,
        log_on_error: bool | None = None,
        error_on_not_found: bool | None = None,
        *,
        method: Callable[..., Awaitable[GitHubKitResponse[T]]],
        **request_args: Any,  # pyright: ignore[reportAny]
    ) -> T | None:
        """Perform a request and extract the response.

        Args:
            action: The action being performed.
            log_request: Whether to log the request.
            log_response: Whether to log the response.
            log_on_error: Whether to log on error.
            error_on_not_found: Whether to raise an error if the resource is not found.

        Raises:
            ResourceNotFoundError: If the resource is not found and error_on_not_found is True.
            ClientRequestError: If the request fails.
            ClientError: If the request fails.
        """

        request_logger, response_logger, error_logger = self._get_loggers(
            log_request=log_request, log_response=log_response, log_on_error=log_on_error
        )

        request_logger(f"Performing {action} using {method.__name__} with kwargs {request_args}")

        try:
            response: GitHubKitResponse[T] = await method(**request_args)
        except GitHubKitRequestFailed as e:
            if e.response.status_code == NOT_FOUND_ERROR:
                if error_on_not_found:
                    raise ResourceNotFoundError(action=action, resource=e.request.url.path) from e

                return None

            error_logger(f"RequestFailed error performing {action} using {method.__name__} with kwargs {request_args}: {e}")

            raise RequestError(action=action, message=str(e)) from e
        except GitHubKitGitHubException as e:
            error_logger(f"Error performing {action} using {method.__name__} with kwargs {request_args}: {e}")

            raise RequestError(action=action, message=str(e)) from e

        extracted_response = extract_response(response)

        response_logger(f"Extracted response for {action} using {method.__name__} with kwargs {request_args}: {extracted_response}")

        return extracted_response

    def _remove_exceptions[T: GITHUBKIT_RESPONSE_TYPE](self, results: Sequence[T | BaseException | None], /) -> list[T | None]:
        return [result for result in results if result is not None and not isinstance(result, BaseException)]

    def _remove_none[T: GITHUBKIT_RESPONSE_TYPE](self, results: Sequence[T | None], /) -> list[T]:
        return [result for result in results if result is not None]

    @overload
    async def get_repository(self, owner: str, repo: str, error_on_not_found: Literal[True] = True) -> Repository: ...

    @overload
    async def get_repository(self, owner: str, repo: str, error_on_not_found: Literal[False] = False) -> Repository | None: ...

    async def get_repository(
        self,
        owner: str,
        repo: str,
        error_on_not_found: bool = False,
    ) -> Repository | None:
        """Get a repository."""

        if githubkit_repository := await self._perform_rest_request(
            action="Get repository",
            log_request=True,
            error_on_not_found=error_on_not_found,
            method=self.githubkit_client.rest.repos.async_get,
            owner=owner,
            repo=repo,
        ):
            return Repository.from_full_repository(full_repository=githubkit_repository)

        return None

    @overload
    async def get_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        limit_comments: int = DEFAULT_ISSUE_COMMENTS_LIMIT,
        limit_related_items: int = DEFAULT_ISSUE_RELATED_ITEMS_LIMIT,
        error_on_not_found: Literal[True] = True,
    ) -> GqlIssueWithDetails: ...

    @overload
    async def get_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        limit_comments: int = DEFAULT_ISSUE_COMMENTS_LIMIT,
        limit_related_items: int = DEFAULT_ISSUE_RELATED_ITEMS_LIMIT,
        error_on_not_found: Literal[False] = False,
    ) -> GqlIssueWithDetails | None: ...

    async def get_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        limit_comments: int = DEFAULT_ISSUE_COMMENTS_LIMIT,
        limit_related_items: int = DEFAULT_ISSUE_RELATED_ITEMS_LIMIT,
        error_on_not_found: bool = False,
    ) -> GqlIssueWithDetails | None:
        """Get an issue."""

        query_variables = GqlGetIssue.to_graphql_query_variables(
            owner=owner,
            repo=repo,
            issue_number=issue_number,
            limit_comments=limit_comments,
            limit_events=limit_related_items,
        )

        gql_get_issue: GqlGetIssue | None = await self._perform_graphql_query(
            query_model=GqlGetIssue,
            variables=query_variables,
            error_on_not_found=error_on_not_found,
        )

        if not gql_get_issue:
            return None

        if not gql_get_issue.repository.issue and error_on_not_found:
            raise ResourceNotFoundError(action="Get issue", resource=f"{owner}/{repo}/{issue_number}")

        return gql_get_issue.repository.issue

    @overload
    async def get_pull_request(
        self,
        owner: str,
        repo: str,
        pull_request_number: int,
        limit_comments: int = DEFAULT_ISSUE_COMMENTS_LIMIT,
        limit_related_items: int = DEFAULT_ISSUE_RELATED_ITEMS_LIMIT,
        error_on_not_found: Literal[True] = True,
    ) -> GqlPullRequestWithDetails: ...

    @overload
    async def get_pull_request(
        self,
        owner: str,
        repo: str,
        pull_request_number: int,
        limit_comments: int = DEFAULT_ISSUE_COMMENTS_LIMIT,
        limit_related_items: int = DEFAULT_ISSUE_RELATED_ITEMS_LIMIT,
        error_on_not_found: Literal[False] = False,
    ) -> GqlPullRequestWithDetails | None: ...

    async def get_pull_request(
        self,
        owner: str,
        repo: str,
        pull_request_number: int,
        limit_comments: int = DEFAULT_ISSUE_COMMENTS_LIMIT,
        limit_related_items: int = DEFAULT_ISSUE_RELATED_ITEMS_LIMIT,
        error_on_not_found: bool = False,
    ) -> GqlPullRequestWithDetails | None:
        """Get a pull request."""

        query_variables = GqlGetPullRequest.to_graphql_query_variables(
            owner=owner,
            repo=repo,
            pull_request_number=pull_request_number,
            limit_comments=limit_comments,
            limit_events=limit_related_items,
        )

        gql_get_pull_request: GqlGetPullRequest | None = await self._perform_graphql_query(
            query_model=GqlGetPullRequest,
            variables=query_variables,
            error_on_not_found=error_on_not_found,
        )

        if not gql_get_pull_request:
            return None

        if not gql_get_pull_request.repository.pull_request and error_on_not_found:
            raise ResourceNotFoundError(action="Get pull request", resource=f"{owner}/{repo}/{pull_request_number}")

        return gql_get_pull_request.repository.pull_request

    @overload
    async def get_pull_request_diff(
        self, owner: str, repo: str, pull_request_number: int, truncate: int = 100, error_on_not_found: Literal[False] = False
    ) -> PullRequestDiff | None: ...

    @overload
    async def get_pull_request_diff(
        self, owner: str, repo: str, pull_request_number: int, truncate: int = 100, error_on_not_found: Literal[True] = True
    ) -> PullRequestDiff: ...

    async def get_pull_request_diff(
        self,
        owner: str,
        repo: str,
        pull_request_number: int,
        truncate: int = 100,
        error_on_not_found: bool = False,
    ) -> PullRequestDiff | None:
        """Get the diff of a pull request."""

        if response := await self._perform_rest_request(
            action="Get pull request diff",
            log_request=True,
            error_on_not_found=error_on_not_found,
            method=self.githubkit_client.rest.pulls.async_list_files,
            owner=owner,
            repo=repo,
            pull_number=pull_request_number,
        ):
            return PullRequestDiff.from_diff_entries(diff_entries=response, truncate=truncate)

        return None

    async def get_default_branch(self, owner: str, repo: str) -> str:
        """Get the default branch of a repository."""

        repository: Repository = await self.get_repository(owner=owner, repo=repo, error_on_not_found=True)

        return repository.default_branch

    @overload
    async def get_git_ref(self, owner: str, repo: str, ref: str, error_on_not_found: Literal[False] = False) -> GitReference | None: ...

    @overload
    async def get_git_ref(self, owner: str, repo: str, ref: str, error_on_not_found: Literal[True] = True) -> GitReference: ...

    async def get_git_ref(self, owner: str, repo: str, ref: str, error_on_not_found: bool = False) -> GitReference | None:
        """Get details about a git ref from the repository.

        Args:
            owner: The owner of the repository.
            repo: The name of the repository.
            ref: The ref of the branch or tag to get the details from.
            error_on_not_found: Whether to raise an error if the ref is not found.
        """

        if git_ref := await self._perform_rest_request(
            action="Get git ref",
            log_request=True,
            error_on_not_found=error_on_not_found,
            method=self.githubkit_client.rest.git.async_get_ref,
            owner=owner,
            repo=repo,
            ref=ref,
        ):
            return GitReference.from_git_ref(git_ref=git_ref)

        return None

    @overload
    async def get_file(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str | None = None,
        truncate_lines: int = DEFAULT_TRUNCATE_LINES,
        truncate_characters: int = DEFAULT_TRUNCATE_CHARACTERS,
        error_on_not_found: bool = False,
    ) -> RepositoryFileWithContent | None: ...

    @overload
    async def get_file(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str | None = None,
        truncate_lines: int = DEFAULT_TRUNCATE_LINES,
        truncate_characters: int = DEFAULT_TRUNCATE_CHARACTERS,
        error_on_not_found: bool = True,
    ) -> RepositoryFileWithContent: ...

    async def get_file(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str | None = None,
        truncate_lines: int = DEFAULT_TRUNCATE_LINES,
        truncate_characters: int = DEFAULT_TRUNCATE_CHARACTERS,
        error_on_not_found: bool = False,
    ) -> RepositoryFileWithContent | None:
        """Get a file from a repository.

        Args:
            owner: The owner of the repository.
            repo: The name of the repository.
            path: The path of the file.
            ref: The ref of the branch or tag to get the file from. If not provided, the default branch will be used.
            truncate_lines: The number of lines to truncate the file to.
            truncate_characters: The number of characters to truncate the file to.
            error_on_not_found: Whether to raise an error if the file is not found.
        """

        if ref is None:
            ref = await self.get_default_branch(owner=owner, repo=repo)

        if file := await self._perform_rest_request(
            action="Get file",
            log_request=True,
            error_on_not_found=error_on_not_found,
            method=self.githubkit_client.rest.repos.async_get_content,
            owner=owner,
            repo=repo,
            path=path,
            ref=ref,
        ):
            if not isinstance(file, GitHubKitContentFile):
                raise ResourceTypeMismatchError(
                    action="Get file", resource=path, expected_type=GitHubKitContentFile, actual_type=type(file)
                )

            return RepositoryFileWithContent.from_content_file(
                content_file=file, truncate_lines=truncate_lines, truncate_characters=truncate_characters
            )

        return None

    async def get_files(
        self,
        owner: str,
        repo: str,
        paths: list[str],
        ref: str | None = None,
        truncate_lines: int = DEFAULT_TRUNCATE_LINES,
        truncate_characters: int = DEFAULT_TRUNCATE_CHARACTERS,
        error_on_not_found: bool = False,
    ) -> list[RepositoryFileWithContent]:
        """Get multiple files from a repository.

        Args:
            owner: The owner of the repository.
            repo: The name of the repository.
            paths: The paths of the files.
            ref: The ref of the branch or tag to get the files from. If not provided, the default branch will be used.
            truncate_lines: The number of lines to truncate the files to.
            truncate_characters: The number of characters to truncate the files to.
            error_on_not_found: Whether to raise an error if the files are not found.
        """

        if not paths:
            return []

        tasks: list[CoroutineType[Any, Any, RepositoryFileWithContent | None]] = [
            self.get_file(
                owner=owner,
                repo=repo,
                path=path,
                ref=ref,
                truncate_lines=truncate_lines,
                truncate_characters=truncate_characters,
                error_on_not_found=error_on_not_found,
            )
            for path in paths
        ]

        results: list[RepositoryFileWithContent | None] = await asyncio.gather(*tasks)

        return self._remove_none(results)

    async def find_file_paths(
        self,
        *,
        owner: str,
        repo: str,
        ref: str | None = None,
        include_patterns: list[str],
        exclude_patterns: list[str] | None = None,
        depth: int | None = None,
        limit_results: int = DEFAULT_FIND_FILES_LIMIT,
    ) -> RepositoryTree:
        """Find files in a GitHub repository by their names/paths. Does not search file contents.

        Args:
            owner: The owner of the repository.
            repo: The name of the repository.
            ref: The ref of the branch or tag to get the tree from. If not provided, the default branch will be used.
            include_patterns: The patterns to check file paths against. Supports single asterisk and question mark
                              wildcards using fnmatch syntax.
            exclude_patterns: The patterns to check file paths against. Supports single asterisk and question mark
                              wildcards using fnmatch syntax. If None, no files will be excluded.
                              Exclude patterns take precedence over include patterns.
            depth: The depth of the tree to search. If not provided, the tree will be searched in its entirety.
                              Depth 0 is the root directory.
            limit_results: The maximum number of results to return.
        """

        if ref is None:
            ref = await self.get_default_branch(owner=owner, repo=repo)

        repository_tree: RepositoryTree = await self.get_repository_tree(owner=owner, repo=repo, ref=ref, depth=depth)

        return FilteredRepositoryTree.from_repository_tree(
            repository_tree=repository_tree,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        ).truncate(limit_results=limit_results)

    async def get_repository_tree(
        self,
        owner: str,
        repo: str,
        ref: str | None = None,
        depth: int | None = None,
    ) -> RepositoryTree:
        """Get the tree of a repository.

        Args:
            owner: The owner of the repository.
            repo: The name of the repository.
            ref: The ref of the branch or tag to get the tree from. If not provided, the default branch will be used.
            depth: The depth of the tree to get. If not provided, the tree will be returned in its entirety. Depth 0 is the root directory.
        """

        if ref is None:
            ref = await self.get_default_branch(owner=owner, repo=repo)

        recursive: bool = depth is None or depth > 0

        tree: GitHubKitGitTree = await self._perform_rest_request(
            action="Get Repository Tree",
            log_request=True,
            error_on_not_found=True,
            method=self.githubkit_client.rest.git.async_get_tree,
            owner=owner,
            repo=repo,
            tree_sha=ref or "main",
            recursive="1" if recursive else None,
        )

        repository_tree: RepositoryTree = RepositoryTree.from_git_tree(git_tree=tree)

        if depth is not None:
            return PrunedRepositoryTree.from_repository_tree(repository_tree=repository_tree, depth=depth)

        return repository_tree

    # async def search_code(
    #     self,
    #     code_search_query: CodeSearchQuery,
    #     per_page: int = 100,
    #     page: int = 1,
    # ) -> SearchCodeResult:
    #     """Execute a code search and return the results."""

    #     response: GitHubKitSearchCodeGetResponse200 = await self._perform_rest_request(
    #         action="Search code",
    #         log_request=True,
    #         error_on_not_found=True,
    #         method=self.githubkit_client.rest.search.async_code,
    #         q=code_search_query.to_query(),
    #         per_page=per_page,
    #         page=page,
    #         headers={"Accept": "application/vnd.github.text-match+json"},
    #     )

    #     matches: list[RepositoryFileWithLineMatches] = [
    #         RepositoryFileWithLineMatches.from_code_search_result_item(code_search_result_item=code_search_result_item)
    #         for code_search_result_item in response.items
    #     ]

    #     return SearchCodeResult(
    #         code_search_query=code_search_query,
    #         matches=matches,
    #     )

    async def search_code_by_keywords(
        self,
        owner: str,
        repo: str,
        keywords: set[str],
    ) -> list[RepositoryFileWithLineMatches]:
        """Search for code in a repository by the provided keywords."""

        escaped_keywords: list[str] = [f'"{keyword}"' for keyword in sorted(keywords)]

        keyword_query = " ".join(escaped_keywords)

        query: str = f"repo:{owner}/{repo} {keyword_query}"

        response: GitHubKitSearchCodeGetResponse200 = await self._perform_rest_request(
            action="Search code by keywords",
            log_request=True,
            error_on_not_found=True,
            method=self.githubkit_client.rest.search.async_code,
            q=query,
            headers={"Accept": "application/vnd.github.text-match+json"},
        )

        return [
            RepositoryFileWithLineMatches.from_code_search_result_item(code_search_result_item=code_search_result_item)
            for code_search_result_item in response.items
        ]

    async def search_pull_requests(
        self,
        query: str,
        limit_pull_requests: int = DEFAULT_ISSUES_OR_PULL_REQUESTS_LIMIT,
        limit_comments: int = DEFAULT_ISSUE_COMMENTS_LIMIT,
        limit_related_items: int = DEFAULT_ISSUE_RELATED_ITEMS_LIMIT,
        limit_pull_request_body_size: int = DEFAULT_ISSUE_BODY_SIZE,
        limit_comment_body_size: int = DEFAULT_COMMENT_BODY_SIZE,
    ) -> list[GqlPullRequestWithDetails]:
        """Search for pull requests in a repository by the provided Search Query."""

        query_variables = GqlSearchPullRequests.to_graphql_query_variables(
            query=query,
            limit_pull_requests=limit_pull_requests,
            limit_comments=limit_comments,
            limit_events=limit_related_items,
        )

        gql_search_pull_requests: GqlSearchPullRequests = await self._perform_graphql_query(
            query_model=GqlSearchPullRequests,
            variables=query_variables,
        )

        for pull_request in gql_search_pull_requests.search:
            pull_request.body = trim_body(pull_request.body, limit_pull_request_body_size)
            for comment in pull_request.comments:
                comment.body = trim_comment_body(comment.body, limit_comment_body_size)

        return gql_search_pull_requests.search

    async def search_pull_requests_by_keywords(
        self,
        owner: str,
        repo: str,
        keywords: set[str],
        all_keywords: bool = False,
        limit_pull_requests: int = DEFAULT_ISSUES_OR_PULL_REQUESTS_LIMIT,
        limit_comments: int = DEFAULT_ISSUE_COMMENTS_LIMIT,
        limit_related_items: int = DEFAULT_ISSUE_RELATED_ITEMS_LIMIT,
        limit_pull_request_body_size: int = DEFAULT_ISSUE_BODY_SIZE,
        limit_comment_body_size: int = DEFAULT_COMMENT_BODY_SIZE,
    ) -> list[GqlPullRequestWithDetails]:
        """Search for pull requests in a repository by the provided keywords.

        Args:
            owner: The owner of the repository.
            repo: The name of the repository.
            keywords: The keywords to use to search for pull requests. Up to 6 keywords are supported.
            all_keywords: Whether all keywords must be present for a result to appear in the search results.
            limit_pull_requests: The maximum number of pull requests to include in the search results.
            limit_comments: The maximum number of comments to include in the search results.
            limit_related_items: The maximum number of related items to include in the search results.
        """

        query: str = build_query(
            owner=owner,
            repo=repo,
            is_issue=False,
            is_pull_request=True,
            keywords=keywords,
            all_keywords=all_keywords,
        )

        return await self.search_pull_requests(
            query=query,
            limit_pull_requests=limit_pull_requests,
            limit_comments=limit_comments,
            limit_related_items=limit_related_items,
            limit_pull_request_body_size=limit_pull_request_body_size,
            limit_comment_body_size=limit_comment_body_size,
        )

    async def search_issues(
        self,
        query: str,
        limit_issues: int = DEFAULT_ISSUES_OR_PULL_REQUESTS_LIMIT,
        limit_comments: int = DEFAULT_ISSUE_COMMENTS_LIMIT,
        limit_related_items: int = DEFAULT_ISSUE_RELATED_ITEMS_LIMIT,
        limit_issue_body_size: int = DEFAULT_ISSUE_BODY_SIZE,
        limit_comment_body_size: int = DEFAULT_COMMENT_BODY_SIZE,
    ) -> list[GqlIssueWithDetails]:
        """Search for issues in a repository using the provided Search Query."""

        query_variables = GqlSearchIssues.to_graphql_query_variables(
            query=query,
            limit_issues=limit_issues,
            limit_comments=limit_comments,
            limit_events=limit_related_items,
        )

        gql_search_issues: GqlSearchIssues = await self._perform_graphql_query(
            query_model=GqlSearchIssues,
            variables=query_variables,
        )

        for issue in gql_search_issues.search:
            issue.body = trim_body(issue.body, limit_issue_body_size)
            for comment in issue.comments:
                comment.body = trim_comment_body(comment.body, limit_comment_body_size)

        return gql_search_issues.search

    async def search_issues_by_keywords(
        self,
        owner: str,
        repo: str,
        keywords: set[str],
        all_keywords: bool = False,
        limit_issues: int = DEFAULT_ISSUES_OR_PULL_REQUESTS_LIMIT,
        limit_comments: int = DEFAULT_ISSUE_COMMENTS_LIMIT,
        limit_related_items: int = DEFAULT_ISSUE_RELATED_ITEMS_LIMIT,
        limit_issue_body_size: int = DEFAULT_ISSUE_BODY_SIZE,
        limit_comment_body_size: int = DEFAULT_COMMENT_BODY_SIZE,
    ) -> list[GqlIssueWithDetails]:
        """Search for issues in a repository by the provided keywords.

        Args:
            owner: The owner of the repository.
            repo: The name of the repository.
            keywords: The keywords to use to search for issues. Up to 6 keywords are supported.
            all_keywords: Whether all keywords must be present for a result to appear in the search results.
            limit_issues: The maximum number of issues to include in the search results.
            limit_comments: The maximum number of comments to include in the search results.
            limit_related_items: The maximum number of related items to include in the search results.
        """

        query: str = build_query(
            owner=owner,
            repo=repo,
            keywords=keywords,
            is_issue=True,
            all_keywords=all_keywords,
        )

        return await self.search_issues(
            query=query,
            limit_issues=limit_issues,
            limit_comments=limit_comments,
            limit_related_items=limit_related_items,
            limit_issue_body_size=limit_issue_body_size,
            limit_comment_body_size=limit_comment_body_size,
        )
