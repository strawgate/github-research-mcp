import asyncio
from collections.abc import Sequence
from logging import Logger
from typing import TYPE_CHECKING, Any, Self

import yaml
from fastmcp.client import Client
from fastmcp.server.server import FastMCP
from fastmcp.tools import Tool
from fastmcp.tools.tool_transform import ArgTransformConfig, ToolTransformConfig
from fastmcp.utilities.logging import get_logger
from mcp.types import ModelHint, ModelPreferences, SamplingMessage
from pydantic import BaseModel, Field

from github_research_mcp.clients.models.github import Repository, RepositoryFileWithContent
from github_research_mcp.models.repository.tree import (
    PrunedRepositoryTree,
    RepositoryFileCountEntry,
    RepositoryTree,
)
from github_research_mcp.sampling.utility import (
    multi_turn_tool_calling_sample,
    new_user_sampling_message,
    sample,
    sampling_is_supported,
)
from github_research_mcp.servers.code import CodeServer
from github_research_mcp.servers.prompts.summarize_repository import OUTPUT_FORMAT, SUMMARIZE_SYSTEM_PROMPT
from github_research_mcp.servers.research import (
    DEFAULT_TRUNCATE_README_CHARACTERS,
    DEFAULT_TRUNCATE_README_LINES,
    ResearchServer,
)
from github_research_mcp.servers.shared.annotations import OWNER, REPO
from github_research_mcp.servers.shared.errors import SamplingSupportRequiredError

if TYPE_CHECKING:
    from types import CoroutineType

SUMMARY_REPOSITORY_TREE_DEPTH = 4
SUMMARY_EXTENSION_STATISTICS_TOP_N = 20


class RepositorySummary(Repository):
    """A summary of a repository."""

    summary: str = Field(description="The summary of the repository.")

    @classmethod
    def from_repository(cls, repository: Repository, summary: str) -> Self:
        return cls(**repository.model_dump(), summary=summary)  # pyright: ignore[reportAny]


def dump_model_as_yaml(model: BaseModel | Sequence[BaseModel], /) -> str:
    if isinstance(model, BaseModel):
        return yaml.safe_dump(model.model_dump(), sort_keys=False, indent=1, width=400)

    return "\n".join([yaml.safe_dump(item.model_dump(), sort_keys=False, indent=1, width=400) for item in model])


class SummaryServer:
    """A Research Server that provides additional tools for summarization."""

    def __init__(self, research_server: ResearchServer, code_server: CodeServer, logger: Logger | None = None):
        self.logger: Logger = logger or get_logger(name=__name__)
        self.research_server: ResearchServer = research_server
        self.code_server: CodeServer = code_server

    def register_tools(self, fastmcp: FastMCP[Any]) -> FastMCP[Any]:
        _ = fastmcp.add_tool(tool=Tool.from_function(fn=self.summarize_repository))

        return fastmcp

    def require_sampling_support(self) -> None:
        """Raise a SamplingSupportRequiredError if the client does not support sampling."""

        if not sampling_is_supported():
            self.logger.warning(
                "A connected client does not support sampling. Sampling support is required to use the summarization tools."
            )

            raise SamplingSupportRequiredError

    async def _get_info_for_summary(self, repository: Repository, owner: OWNER, repo: REPO) -> str:
        tasks: tuple[
            CoroutineType[Any, Any, list[RepositoryFileWithContent]],
            CoroutineType[Any, Any, RepositoryTree],
            CoroutineType[Any, Any, list[RepositoryFileCountEntry]],
        ] = (
            self.research_server.get_readmes(owner=owner, repo=repo),
            self.research_server.research_client.get_repository_tree(owner=owner, repo=repo),
            self.research_server.get_file_extension_statistics(owner=owner, repo=repo, top_n=SUMMARY_EXTENSION_STATISTICS_TOP_N),
        )

        readmes, repository_tree, file_extension_statistics = await asyncio.gather(*tasks)

        user_prompt: str = f"""# Repository Information
The following is the information about the repository:

## Metadata
{dump_model_as_yaml(repository)}

## Repository Readmes
The first {DEFAULT_TRUNCATE_README_LINES} lines / {DEFAULT_TRUNCATE_README_CHARACTERS} characters of the
following readmes were gathered for your summary:
{dump_model_as_yaml(readmes)}

## Repository Most Common File Extensions
The following are the {SUMMARY_EXTENSION_STATISTICS_TOP_N} most common file extensions in the repository:
{dump_model_as_yaml(file_extension_statistics)}

## Repository Layout
The following are the files available in the root of the repository:
{repository_tree.files}

The following is first {SUMMARY_REPOSITORY_TREE_DEPTH} levels deep of the repository:
{dump_model_as_yaml(PrunedRepositoryTree.from_repository_tree(repository_tree, depth=SUMMARY_REPOSITORY_TREE_DEPTH).directories)}
"""

        return user_prompt

    def _code_server_tools_client(self, owner: OWNER, repo: REPO) -> Client[Any]:
        if not self.code_server:
            msg = "Code server is not set"
            raise ValueError(msg)

        owner_repo_transform_config = ToolTransformConfig(
            arguments={
                "owner": ArgTransformConfig(default=owner, hide=True),
                "repo": ArgTransformConfig(default=repo, hide=True),
            }
        )

        fastmcp: FastMCP[Any] = FastMCP[Any](
            name="Code Server Tools Client",
            tool_transformations={
                "get_file": owner_repo_transform_config,
                "get_files": owner_repo_transform_config,
                "find_files": owner_repo_transform_config,
                "search_code": owner_repo_transform_config,
                "get_file_types_for_search": ToolTransformConfig(enabled=False),
            },
        )

        _ = self.code_server.register_tools(mcp=fastmcp)

        return Client[Any](transport=fastmcp)

    async def summarize_repository(self, owner: OWNER, repo: REPO) -> RepositorySummary:
        repository: Repository = await self.research_server.research_client.get_repository(owner=owner, repo=repo)

        tools_client = self._code_server_tools_client(owner=owner, repo=repo)

        initial_user_prompt = await self._get_info_for_summary(repository=repository, owner=owner, repo=repo)

        instructions = """
# Tool Usage and Rounds

Each time you are prompted to select tools is called a "round". You have 5 rounds to complete your research.

You can call up to 15 tools per round:
- You may request 10 distinct calls to the `get_files` tool per round.
    Each call to `get_files` can target up to 8 files meaning you can request up to 80 files per round.
- You may request 5 distinct calls to the `find_files` tool per round.
- You may request 5 distinct calls to the `search_code` tool per round.

You will not be providing the summary yet. You are only gathering information.
"""

        messages: list[SamplingMessage] = [
            new_user_sampling_message(content=initial_user_prompt),
        ]

        self.logger.info(f"Summarizing repository {owner}/{repo}. Starting tool calling.")

        new_messages: list[SamplingMessage] = await multi_turn_tool_calling_sample(
            system_prompt=SUMMARIZE_SYSTEM_PROMPT,
            messages=[*messages, new_user_sampling_message(content=instructions)],
            client=tools_client,
            max_tokens=4000,
            temperature=0.3,
            max_tool_calls=10,
            parallel_tool_calls=True,
            max_turns=5,
            model_preferences=ModelPreferences(hints=[ModelHint(name="gemini-2.5-flash")]),
        )

        self.logger.info(f"Summarizing repository {owner}/{repo}. Tool calling complete. Starting summary.")

        messages.extend([*new_messages, new_user_sampling_message(content="You will now summarize the repository.")])

        summary, _ = await sample(
            system_prompt=SUMMARIZE_SYSTEM_PROMPT,
            messages=[*messages, new_user_sampling_message(content="Remember the desired output format " + OUTPUT_FORMAT)],
            max_tokens=6000,
            temperature=0.1,
            model_preferences=ModelPreferences(hints=[ModelHint(name="gemini-2.5-flash")]),
        )

        self.logger.info(f"Summarizing repository {owner}/{repo}. Summary complete.")

        return RepositorySummary.from_repository(repository=repository, summary=summary)
