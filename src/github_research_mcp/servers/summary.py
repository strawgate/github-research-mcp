import asyncio
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Self, override

import yaml
from fastmcp import FastMCP
from fastmcp.client import Client
from fastmcp.tools import Tool
from fastmcp.tools.tool_transform import ArgTransform, TransformedTool
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
from github_research_mcp.servers.prompts.summarize_repository import SUMMARIZE_SYSTEM_PROMPT
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


class SummaryServer(ResearchServer):
    """A Research Server that provides additional tools for summarization."""

    @override
    def register_tools(self, fastmcp: FastMCP[Any]) -> FastMCP[Any]:
        _ = super().register_tools(fastmcp=fastmcp)

        _ = fastmcp.add_tool(tool=Tool.from_function(fn=self.summarize_repository))

        return fastmcp

    def require_sampling_support(self) -> None:
        """Raise a SamplingSupportRequiredError if the client does not support sampling."""

        if not sampling_is_supported():
            self.logger.warning(
                "A connected client does not support sampling. Sampling support is required to use the summarization tools."
            )

            raise SamplingSupportRequiredError

    async def _summary_tools_client(self, owner: OWNER, repo: REPO) -> Client[Any]:
        fastmcp = FastMCP[Any](name="Summary Tools Client")

        passthrough_tools: dict[str, TransformedTool] = self.passthrough_tools()

        owner_repo_args = {
            "owner": ArgTransform(default=owner, hide=True),
            "repo": ArgTransform(default=repo, hide=True),
        }

        tools = [
            TransformedTool.from_tool(
                tool=passthrough_tools["get_files"],
                transform_args={
                    "truncate_characters": ArgTransform(hide=True),
                    "truncate_lines": ArgTransform(hide=True),
                    **owner_repo_args,
                },
            ),
            TransformedTool.from_tool(
                tool=passthrough_tools["find_file_paths"], transform_args={"ref": ArgTransform(hide=True), **owner_repo_args}
            ),
            TransformedTool.from_tool(tool=passthrough_tools["search_code_by_keywords"], transform_args=owner_repo_args),
        ]

        [fastmcp.add_tool(tool=tool) for tool in tools]

        return Client[Any](transport=fastmcp)

    async def summarize_repository(self, owner: OWNER, repo: REPO) -> RepositorySummary:
        """Summarize a repository with tools."""

        self.require_sampling_support()

        self.logger.info(f"Summarizing repository {owner}/{repo}. Gathering repository information.")

        tools_client = await self._summary_tools_client(owner=owner, repo=repo)

        repository: Repository = await self.research_client.get_repository(owner=owner, repo=repo)

        tasks: tuple[
            CoroutineType[Any, Any, list[RepositoryFileWithContent]],
            CoroutineType[Any, Any, RepositoryTree],
            CoroutineType[Any, Any, list[RepositoryFileCountEntry]],
        ] = (
            self.get_readmes(owner=owner, repo=repo),
            self.research_client.get_repository_tree(owner=owner, repo=repo),
            self.get_file_extension_statistics(owner=owner, repo=repo, top_n=SUMMARY_EXTENSION_STATISTICS_TOP_N),
        )

        readmes, repository_tree, file_extension_statistics = await asyncio.gather(*tasks)

        readme_names: list[str] = [readme.path for readme in readmes]

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

# Tool Usage and Rounds

Each time you are prompted to select tools is called a "round".

You should use all 10 available tool calls per round:
- You may request 4 distinct calls to the `get_files` tool per round.
    Each call to `get_files` can target up to 8 files meaning you can request up to 40 files per round.
- You may request 4 distinct calls to the `find_file_paths` tool per round.
- You may request 2 distinct calls to the `search_code_by_keywords` tool per round.

Do not request files you have already received. You have already been given the following files:
{readme_names}
"""

        messages: list[SamplingMessage] = [new_user_sampling_message(content=user_prompt)]

        new_messages: list[SamplingMessage] = await multi_turn_tool_calling_sample(
            system_prompt=SUMMARIZE_SYSTEM_PROMPT,
            messages=messages,
            client=tools_client,
            max_tokens=4000,
            temperature=0.3,
            max_tool_calls=10,
            parallel_tool_calls=True,
            max_turns=2,
            model_preferences=ModelPreferences(hints=[ModelHint(name="gemini-2.5-flash")]),
        )

        time_to_summarize = new_user_sampling_message(content="You will now summarize the repository.")

        messages.extend([*new_messages, time_to_summarize])

        self.logger.info(f"Summarizing repository {owner}/{repo}. Producing summary.")

        summary, _ = await sample(
            system_prompt=SUMMARIZE_SYSTEM_PROMPT,
            messages=messages,
            max_tokens=6000,
            temperature=0.1,
            model_preferences=ModelPreferences(hints=[ModelHint(name="gemini-2.5-flash")]),
        )

        return RepositorySummary.from_repository(repository=repository, summary=summary)
