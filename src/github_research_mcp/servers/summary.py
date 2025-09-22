import asyncio
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Self

import yaml
from fastmcp import FastMCP
from fastmcp.tools import Tool
from mcp.types import ModelHint, ModelPreferences, SamplingMessage
from pydantic import BaseModel, Field

from github_research_mcp.clients.models.github import Repository, RepositoryFileWithContent
from github_research_mcp.models.repository.tree import (
    PrunedRepositoryTree,
    RepositoryFileCountEntry,
    RepositoryTree,
)
from github_research_mcp.sampling.utility import new_user_sampling_message, structured_sample
from github_research_mcp.servers.models.summary import (
    InformationRequestForSummary,
)
from github_research_mcp.servers.prompts.summarize_repository import SUMMARIZE_SYSTEM_PROMPT
from github_research_mcp.servers.research import ResearchServer
from github_research_mcp.servers.shared.annotations import OWNER, REPO

if TYPE_CHECKING:
    from types import CoroutineType


class RepositorySummary(Repository):
    """A summary of a repository."""

    summary: str = Field(description="The summary of the repository.")

    @classmethod
    def from_repository(cls, repository: Repository, summary: str) -> Self:
        return cls(**repository.model_dump(), summary=summary)


SUMMARY_README_LIMIT_LINES = 2000
SUMMARY_README_LIMIT_CHARACTERS = 60000
SUMMARY_FILE_EXTENSION_STATISTICS_TOP_N = 30
SUMMARY_REPOSITORY_TREE_DEPTH = 8

SUMMARY_LIMIT_FETCH_FILES_PER_ROUND = 35
SUMMARY_LIMIT_CODE_KEYWORDS_SEARCHES_PER_ROUND = 2
SUMMARY_LIMIT_FIND_FILE_PATHS_PER_ROUND = 5

SUMMARY_LIMITS: dict[str, int] = {
    "limit_fetch_files": SUMMARY_LIMIT_FETCH_FILES_PER_ROUND,
    "limit_code_keywords_searches": SUMMARY_LIMIT_CODE_KEYWORDS_SEARCHES_PER_ROUND,
    "limit_find_file_paths": SUMMARY_LIMIT_FIND_FILE_PATHS_PER_ROUND,
}


def dump_model_as_yaml(model: BaseModel | Sequence[BaseModel], /) -> str:
    if isinstance(model, BaseModel):
        return yaml.safe_dump(model.model_dump(), sort_keys=False, indent=1, width=400)

    return "\n".join([yaml.safe_dump(item.model_dump(), sort_keys=False, indent=1, width=400) for item in model])


class SummaryServer(ResearchServer):
    """A Research Server that provides additional tools for summarization."""

    def register_tools(self, fastmcp: FastMCP[Any]) -> FastMCP[Any]:
        super().register_tools(fastmcp=fastmcp)

        fastmcp.add_tool(tool=Tool.from_function(fn=self.summarize_repository))

        return fastmcp

    async def summarize_repository(self, owner: OWNER, repo: REPO) -> RepositorySummary:
        """Summarize a repository."""

        self.logger.info(f"Summarizing repository {owner}/{repo}. Gathering repository information.")

        repository: Repository = await self.research_client.get_repository(owner=owner, repo=repo)

        tasks: tuple[
            CoroutineType[Any, Any, list[RepositoryFileWithContent]],
            CoroutineType[Any, Any, RepositoryTree],
            CoroutineType[Any, Any, list[RepositoryFileCountEntry]],
        ] = (
            self.get_readmes(
                owner=owner, repo=repo, truncate_lines=SUMMARY_README_LIMIT_LINES, truncate_characters=SUMMARY_README_LIMIT_CHARACTERS
            ),
            self.research_client.get_repository_tree(owner=owner, repo=repo),
            self.get_file_extension_statistics(owner=owner, repo=repo),
        )

        readmes, repository_tree, file_extension_statistics = await asyncio.gather(*tasks)

        gathered_files: list[str] = [readme.path for readme in readmes]

        request_limit_text = (
            f"You may request up to {SUMMARY_LIMIT_FETCH_FILES_PER_ROUND} files to fetch, "
            f"You may request up to {SUMMARY_LIMIT_CODE_KEYWORDS_SEARCHES_PER_ROUND} code keywords searches, and "
            f"You may request up to {SUMMARY_LIMIT_FIND_FILE_PATHS_PER_ROUND} find file requests. Each find file paths request "
            "can include an unlimited number of include and exclude clauses."
        )

        user_prompt: str = f"""# Repository Information
The following is the information about the repository:

## Metadata
{dump_model_as_yaml(repository)}

## Repository Readmes
The first {SUMMARY_README_LIMIT_LINES} lines / {SUMMARY_README_LIMIT_CHARACTERS} characters of the
following readmes were gathered for your summary:
{dump_model_as_yaml(readmes)}

## Repository Most Common File Extensions
The following is the {SUMMARY_FILE_EXTENSION_STATISTICS_TOP_N} most common file extensions in the repository:
{dump_model_as_yaml(file_extension_statistics)}

## Repository Layout
The following are the files available in the root of the repository:
{repository_tree.files}

The following is first {SUMMARY_REPOSITORY_TREE_DEPTH} levels deep of the repository:
{dump_model_as_yaml(PrunedRepositoryTree.from_repository_tree(repository_tree, depth=SUMMARY_REPOSITORY_TREE_DEPTH).directories)}

# Your first request for files and searches
It's now time to fetch files, perform searches, and find files by name/path that you will use to
provide a summary of the repository. This is your change to get a high-level understanding of the repository by sampling a broad range of
the most important files and searching for a broad range of the most important keywords.

You should focus on reading the main entrypoints, documentation, important library files, configuration files,
and other high-signal files.

{request_limit_text}

You have already gathered the following files, do not request them again:
```
{gathered_files}
```
"""
        messages: list[SamplingMessage] = [new_user_sampling_message(content=user_prompt)]

        self.logger.info(f"Summarizing repository {owner}/{repo}. Asking for first round of files and searches.")

        information_request, assistant_message = await structured_sample(
            system_prompt=SUMMARIZE_SYSTEM_PROMPT,
            messages=messages,
            response_model=InformationRequestForSummary,
            max_tokens=4000,
            temperature=0.2,
            model_preferences=ModelPreferences(hints=[ModelHint(name="gemini-2.5-flash")]),
        )

        fetched_files, keywords, find_file_paths = await information_request.gather(
            research_client=self.research_client,
            owner=owner,
            repo=repo,
            repository_tree=repository_tree,
            already_fetched_files=gathered_files,
            logger=self.logger,
            **SUMMARY_LIMITS,
        )

        [gathered_files.append(file.path) for file in fetched_files for file in file.files]

        round_one_result_message = f"""# First Round Result
The following files and searches were performed per your request:

## Requested Files
{dump_model_as_yaml(fetched_files)}

## Requested Code Keyword Searches
{dump_model_as_yaml(keywords)}

## Requested Files by Name/Path
{dump_model_as_yaml(find_file_paths)}

# Second Round Request Files and Searches

The first search focused on getting a high-level understanding of the repository by sampling a broad range of the most important
files and searches including main entrypoints, documentation, important library files, configuration files, and other high-signal files.

This second search is your last chance to locate any remaining missing pieces of information that you need to provide the
summary. This is not the time to read 15 files about a single topic. Consider what files, keywords, classes, workflows, APIs,
etc that you discovered in your first search that are important to the summary. Do you need to learn more about them? Is anything
big missing? What information would you need to be successful working in this repository?

Carefully review your system prompt, your goal and objectives, and the information you have already obtained. This is your last chance
to fill in any gaps in your understanding of the repository so that you can provide a complete and self-contained summary.

{request_limit_text}

Do not perform any searches that you have already performed in the first round. Do not request any files that you have already gathered
in the first round. Do not search for any file paths that you have already searched for in the first round.
"""

        messages.extend([assistant_message, new_user_sampling_message(content=round_one_result_message)])

        self.logger.info(f"Summarizing repository {owner}/{repo}. Asking for second round of files and searches.")

        information_request, assistant_message = await structured_sample(
            system_prompt=SUMMARIZE_SYSTEM_PROMPT,
            messages=messages,
            response_model=InformationRequestForSummary,
            max_tokens=4000,
            temperature=0.2,
            model_preferences=ModelPreferences(hints=[ModelHint(name="gemini-2.5-flash")]),
        )

        fetched_files, keywords, find_file_paths = await information_request.gather(
            research_client=self.research_client,
            logger=self.logger,
            owner=owner,
            repo=repo,
            repository_tree=repository_tree,
            already_fetched_files=gathered_files,
            **SUMMARY_LIMITS,
        )

        [gathered_files.append(file.path) for file in fetched_files for file in file.files]

        round_two_result_message = f"""# Second Round Result

The following files and searches were performed per your request:

## Requested Files
{dump_model_as_yaml(fetched_files)}

## Requested Code Keyword Searches
{dump_model_as_yaml(keywords)}

## Requested Files by Name/Path
{dump_model_as_yaml(find_file_paths)}

Please provide the summary of the repository. Your response should be the summary, complete and self-contained and should not mention
from our conversation here. Do not start your response with something like "Here is the summary of the repository:" and do not include
any other text other than the summary. Once you have provided a really great summary, we will continue with our conversation.

QUALITY CHECKLIST (self-verify before returning):
- No redundant facts across sections; use cross-refs instead of repetition.
- Each bullet carries multiple facts (2-4) via colons/semicolons/parentheses.
- ≤1 citation per bullet (max 2 if strictly necessary and orthogonal).
- Do not include examples, meta-instructions, or this prompt text.
- No placeholders/TODOs (e.g., “we should check X”);"""

        messages.extend([assistant_message, new_user_sampling_message(content=round_two_result_message)])

        self.logger.info(f"Summarizing repository {owner}/{repo}. Producing summary.")

        summary, _ = await structured_sample(
            system_prompt=SUMMARIZE_SYSTEM_PROMPT,
            messages=messages,
            response_model=str,
            temperature=0.2,
            max_tokens=10000,
            model_preferences=ModelPreferences(hints=[ModelHint(name="gemini-2.5-flash")]),
        )

        self.logger.info(f"Summarizing repository {owner}/{repo}. Completed summary.")

        return RepositorySummary.from_repository(repository=repository, summary=summary)
