import os
from collections.abc import AsyncGenerator, Sequence
from typing import Any, overload

import pytest
from fastmcp import FastMCP
from fastmcp.client.client import CallToolResult
from fastmcp.experimental.sampling.handlers.base import BaseLLMSamplingHandler
from fastmcp.server.middleware.logging import StructuredLoggingMiddleware
from githubkit.github import GitHub
from openai import OpenAI
from pydantic import BaseModel

from github_research_mcp.clients.github import get_githubkit_client
from github_research_mcp.vendored.google_genai import GoogleGenaiSamplingHandler

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")


@pytest.fixture
def openai_client() -> OpenAI:
    return OpenAI(api_key=OPENAI_KEY, base_url=OPENAI_BASE_URL)


@pytest.fixture
async def githubkit_client() -> AsyncGenerator[GitHub[Any], Any]:
    githubkit_client = get_githubkit_client()

    async with githubkit_client:
        yield githubkit_client


@pytest.fixture
def github_client(githubkit_client: GitHub[Any]) -> GitHub[Any]:
    return githubkit_client


@pytest.fixture
def sampling_handler() -> BaseLLMSamplingHandler:
    return GoogleGenaiSamplingHandler(default_model=OPENAI_MODEL or "gemini-2.5-flash")


@pytest.fixture
def logging_middleware() -> StructuredLoggingMiddleware:
    return StructuredLoggingMiddleware(include_payloads=True)


# E2E Test Data


class E2ERepository(BaseModel):
    owner: str
    repo: str


class E2EIssue(BaseModel):
    owner: str
    repo: str
    issue_number: int


class E2EPullRequest(BaseModel):
    owner: str
    repo: str
    pull_request_number: int


class E2ERepositoryFile(BaseModel):
    owner: str
    repo: str
    path: str
    ref: str


class E2ERepositoryFiles(BaseModel):
    owner: str
    repo: str
    paths: list[str]
    ref: str


@pytest.fixture
def e2e_repository() -> E2ERepository:
    """Points to the github-issues-e2e-test repository."""
    return E2ERepository(owner="strawgate", repo="github-issues-e2e-test")


@pytest.fixture
def e2e_missing_repository() -> E2ERepository:
    """Points to a missing repository."""
    return E2ERepository(owner="strawgate", repo="missing")


@pytest.fixture
def e2e_issue(e2e_repository: E2ERepository) -> E2EIssue:
    """Points to a valid issue in the github-issues-e2e-test repository."""
    return E2EIssue(owner=e2e_repository.owner, repo=e2e_repository.repo, issue_number=14)


@pytest.fixture
def e2e_missing_issue(e2e_repository: E2ERepository) -> E2EIssue:
    """Points to a missing issue in the github-issues-e2e-test repository."""
    return E2EIssue(owner=e2e_repository.owner, repo=e2e_repository.repo, issue_number=100000)


@pytest.fixture
def e2e_pull_request(e2e_repository: E2ERepository) -> E2EPullRequest:
    """Points to a valid pull request in the github-issues-e2e-test repository."""
    return E2EPullRequest(owner=e2e_repository.owner, repo=e2e_repository.repo, pull_request_number=2)


@pytest.fixture
def e2e_missing_pull_request(e2e_repository: E2ERepository) -> E2EPullRequest:
    """Points to a missing pull request in the github-issues-e2e-test repository."""
    return E2EPullRequest(owner=e2e_repository.owner, repo=e2e_repository.repo, pull_request_number=100000)


@pytest.fixture
def e2e_file(e2e_repository: E2ERepository) -> E2ERepositoryFile:
    """Points to a valid file on the default branch of the github-issues-e2e-test repository."""
    return E2ERepositoryFile(owner=e2e_repository.owner, repo=e2e_repository.repo, path="README.md", ref="main")


@pytest.fixture
def e2e_files(e2e_repository: E2ERepository) -> E2ERepositoryFiles:
    """Points to a missing file in the github-issues-e2e-test repository."""
    return E2ERepositoryFiles(owner=e2e_repository.owner, repo=e2e_repository.repo, paths=["README.md", "CONTRIBUTORS.md"], ref="main")


@pytest.fixture
def e2e_file_from_ref(e2e_repository: E2ERepository) -> E2ERepositoryFile:
    """Points to a valid file on a specific ref of the github-issues-e2e-test repository."""
    return E2ERepositoryFile(owner=e2e_repository.owner, repo=e2e_repository.repo, path="test.md", ref="strawgate-patch-1")


@pytest.fixture
def e2e_file_from_missing_ref(e2e_repository: E2ERepository) -> E2ERepositoryFile:
    """Points to a missing file on a specific ref of the github-issues-e2e-test repository."""
    return E2ERepositoryFile(owner=e2e_repository.owner, repo=e2e_repository.repo, path="missing", ref="strawgate-patch-1000000")


@pytest.fixture
def fastmcp(sampling_handler: BaseLLMSamplingHandler, logging_middleware: StructuredLoggingMiddleware):
    return FastMCP(
        name="GitHub Research MCP",
        sampling_handler=sampling_handler,
        middleware=[logging_middleware],
    )


def handle_exclude_keys(dictionary: dict[str, Any], exclude_keys: list[str] | None = None) -> dict[str, Any]:
    if exclude_keys is None:
        return dictionary
    return {key: value for key, value in dictionary.items() if key not in exclude_keys}


@overload
def dump_for_snapshot(
    basemodel: None,
    /,
    exclude_keys: list[str] | None = None,
    exclude_none: bool = True,
    **dump_kwargs: Any,
) -> None:
    return None


@overload
def dump_for_snapshot(
    basemodel: BaseModel,
    /,
    exclude_keys: list[str] | None = None,
    exclude_none: bool = True,
    **dump_kwargs: Any,
) -> dict[str, Any]:
    return handle_exclude_keys(basemodel.model_dump(exclude_none=exclude_none, **dump_kwargs), exclude_keys)


def dump_for_snapshot(
    basemodel: None | BaseModel,
    /,
    exclude_keys: list[str] | None = None,
    exclude_none: bool = True,
    **dump_kwargs: Any,
) -> dict[str, Any] | None:
    if basemodel is None:
        return None

    return handle_exclude_keys(basemodel.model_dump(exclude_none=exclude_none, **dump_kwargs), exclude_keys)


def dump_list_for_snapshot(
    basemodel: None | Sequence[BaseModel],
    /,
    exclude_keys: list[str] | None = None,
    exclude_none: bool = True,
    **dump_kwargs: Any,
) -> list[dict[str, Any]] | None:
    if basemodel is None:
        return []

    return [dump_for_snapshot(item, exclude_keys, exclude_none, **dump_kwargs) for item in basemodel]


def dump_call_tool_result_for_snapshot(
    call_tool_result: CallToolResult,
    /,
) -> dict[str, Any]:
    return {
        "content": [item.model_dump() for item in call_tool_result.content],
        "structured_content": call_tool_result.structured_content,
    }
