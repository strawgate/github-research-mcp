from datetime import datetime
from typing import Literal, Self

from githubkit.versions.v2022_11_28.models import CodeSearchResultItem as GitHubKitCodeSearchResultItem
from githubkit.versions.v2022_11_28.models import (
    ContentFile as GitHubKitContentFile,
)
from githubkit.versions.v2022_11_28.models import DiffEntry as GitHubKitDiffEntry
from githubkit.versions.v2022_11_28.models import (
    FullRepository as GitHubKitFullRepository,
)
from githubkit.versions.v2022_11_28.models import (
    GitRef as GitHubKitGitRef,
)
from githubkit.versions.v2022_11_28.models import (
    LicenseSimple as GitHubKitLicenseSimple,
)
from pydantic import BaseModel, ConfigDict, Field, RootModel

from github_research_mcp.models import Comment, Issue, PullRequest
from github_research_mcp.models.graphql.queries import (
    GqlGetIssueOrPullRequestsWithDetails,
    GqlIssueWithDetails,
    GqlSearchIssueOrPullRequestsWithDetails,
)
from github_research_mcp.servers.shared.utility import decode_content

DEFAULT_TRUNCATE_CONTENT_LINES = 500
DEFAULT_TRUNCATE_CONTENT_CHARACTERS = 20000

DEFAULT_README_TRUNCATE_CONTENT_LINES = 2000
DEFAULT_README_TRUNCATE_CONTENT_CHARACTERS = 60000


class FileLines(RootModel[dict[int, str]]):
    """A dictionary of line numbers and content pairs."""

    @classmethod
    def from_text(cls, text: str) -> Self:
        text_lines = text.split("\n")

        file_lines = {i + 1: line for i, line in enumerate(text_lines)}

        return cls(root=file_lines)

    def truncate(self, truncate_lines: int, truncate_characters: int) -> Self:
        total_characters: int = 0
        new_lines: dict[int, str] = {}

        for line_number, line in self.root.items():
            if line_number > truncate_lines:
                break

            total_characters += len(line)
            if total_characters > truncate_characters:
                break

            new_lines[line_number] = line

        return self.model_copy(update={"root": new_lines})


class RepositoryLicense(BaseModel):
    """A repository license."""

    name: str = Field(description="The name of the license.")
    url: str | None = Field(description="The URL of the license.")

    @classmethod
    def from_license_simple(cls, license_simple: GitHubKitLicenseSimple) -> Self:
        return cls(name=license_simple.name, url=license_simple.url)


class Repository(BaseModel):
    """A repository."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(description="The name of the repository.")
    description: str | None = Field(description="The description of the repository.")
    fork: bool = Field(description="Whether the repository is a fork.")
    url: str = Field(description="The URL of the repository.")
    stars: int = Field(description="The number of stars the repository has.")
    homepage_url: str | None = Field(description="The homepage URL of the repository.")
    language: str | None = Field(description="The language of the repository.")
    default_branch: str = Field(description="The default branch of the repository.")
    topics: list[str] = Field(
        description="The topics of the repository.",
    )
    archived: bool = Field(description="Whether the repository is archived.")
    created_at: datetime = Field(description="The date and time the repository was created.")
    updated_at: datetime = Field(description="The date and time the repository was updated.")
    pushed_at: datetime = Field(description="The date and time the repository was pushed to.")
    license: RepositoryLicense | None = Field(description="The license information of the repository.")

    @classmethod
    def from_full_repository(cls, full_repository: GitHubKitFullRepository) -> Self:
        repository_license = (
            RepositoryLicense.from_license_simple(license_simple=full_repository.license_) if full_repository.license_ else None
        )
        return cls(
            name=full_repository.name,
            description=full_repository.description,
            fork=full_repository.fork,
            url=full_repository.url,
            stars=full_repository.stargazers_count,
            homepage_url=full_repository.homepage,
            language=full_repository.language,
            default_branch=full_repository.default_branch,
            topics=full_repository.topics or [],
            archived=full_repository.archived,
            created_at=full_repository.created_at,
            updated_at=full_repository.updated_at,
            pushed_at=full_repository.pushed_at,
            license=repository_license,
        )


class RepositoryFileWithContent(BaseModel):
    """A file with its path and content."""

    path: str = Field(description="The path of the file.")
    content: FileLines = Field(description="The content of the file.")
    total_lines: int = Field(description="The total number of lines in the file.")
    truncated: bool = Field(default=False, description="Whether the content has been truncated.")

    @classmethod
    def from_content_file(
        cls,
        content_file: GitHubKitContentFile,
        truncate_lines: int = DEFAULT_TRUNCATE_CONTENT_LINES,
        truncate_characters: int = DEFAULT_TRUNCATE_CONTENT_CHARACTERS,
    ) -> Self:
        decoded_content = decode_content(content_file.content)

        file_lines = FileLines.from_text(text=decoded_content)

        return cls(path=content_file.path, content=file_lines, total_lines=len(file_lines.root)).truncate(
            truncate_lines=truncate_lines, truncate_characters=truncate_characters
        )

    def truncate(self, truncate_lines: int, truncate_characters: int) -> Self:
        return self.model_copy(
            update={"content": self.content.truncate(truncate_lines=truncate_lines, truncate_characters=truncate_characters)}
        )


class RepositoryFileWithLineMatches(BaseModel):
    """A file with its path and line matches from a search result."""

    path: str = Field(description="The path of the file.")
    matches: list[str] = Field(description="The fragments of the file that match the search query.")
    keywords: list[str] = Field(description="The keywords from the search that match the file.")

    @classmethod
    def from_code_search_result_item(cls, code_search_result_item: GitHubKitCodeSearchResultItem) -> Self:
        if not code_search_result_item.text_matches:
            msg = f"Expected a list of SearchResultTextMatchesItems, got {type(code_search_result_item.text_matches)}"
            raise TypeError(msg)

        keyword_matches: set[str] = set()
        text_matches: list[str] = []

        for text_match in code_search_result_item.text_matches:
            if matches := text_match.matches:
                keyword_matches.update(match.text for match in matches if match.text)

            if text_match.fragment:
                text_matches.append(text_match.fragment)

        return cls(path=code_search_result_item.path, matches=text_matches, keywords=list(keyword_matches))


class GitReference(BaseModel):
    """A git reference."""

    name: str = Field(description="The name of the reference.")
    sha: str = Field(description="The SHA of the reference.")
    ref_type: str = Field(description="The type of the reference.")

    @classmethod
    def from_git_ref(cls, git_ref: GitHubKitGitRef) -> Self:
        return cls(name=git_ref.ref, sha=git_ref.object_.sha, ref_type=git_ref.object_.type)


class PullRequestFileDiff(BaseModel):
    path: str = Field(description="The path of the file.")
    status: Literal["added", "removed", "modified", "renamed", "copied", "changed", "unchanged"] = Field(
        description="The status of the file."
    )
    patch: str | None = Field(default=None, description="The patch of the file.")
    previous_filename: str | None = Field(default=None, description="The previous filename of the file.")
    truncated: bool = Field(default=False, description="Whether the patch has been truncated to reduce response size.")

    @classmethod
    def from_diff_entry(cls, diff_entry: GitHubKitDiffEntry, truncate: int = 100) -> Self:
        pr_file_diff: Self = cls(
            path=diff_entry.filename,
            status=diff_entry.status,
            patch=diff_entry.patch if diff_entry.patch else None,
            previous_filename=diff_entry.previous_filename if diff_entry.previous_filename else None,
        )

        return pr_file_diff.truncate(truncate=truncate)

    @property
    def lines(self) -> list[str]:
        return self.patch.split("\n") if self.patch else []

    def truncate(self, truncate: int) -> Self:
        lines: list[str] = self.lines

        if len(lines) > truncate:
            lines = lines[:truncate]
            return self.model_copy(update={"patch": "\n".join(lines), "truncated": True})

        return self


class PullRequestDiff(BaseModel):
    file_diffs: list[PullRequestFileDiff] = Field(description="The diff of the pull request.")

    @classmethod
    def from_diff_entries(cls, diff_entries: list[GitHubKitDiffEntry], truncate: int = 100) -> Self:
        return cls(
            file_diffs=[PullRequestFileDiff.from_diff_entry(diff_entry=diff_entry, truncate=truncate) for diff_entry in diff_entries]
        )


class IssueOrPullRequestWithDetails(BaseModel):
    issue_or_pr: Issue | PullRequest = Field(description="The issue or pull request.")
    diff: PullRequestDiff | None = Field(default=None, description="The diff, if it's a pull request.")
    comments: list[Comment] = Field(description="The comments on the issue or pull request.")
    related: list[Issue | PullRequest] = Field(description="The related issues or pull requests.")

    @classmethod
    def from_gql_get_issue_or_pull_requests_with_details(
        cls,
        gql_get_issue_or_pull_requests_with_details: GqlGetIssueOrPullRequestsWithDetails,
    ) -> Self:
        gql_issue_or_pull_request = gql_get_issue_or_pull_requests_with_details.repository.issue_or_pull_request

        issue_or_pull_request = (
            gql_issue_or_pull_request.to_issue()
            if isinstance(gql_issue_or_pull_request, GqlIssueWithDetails)
            else gql_issue_or_pull_request.to_pull_request()
        )

        return cls(
            issue_or_pr=issue_or_pull_request,
            comments=gql_issue_or_pull_request.comments.nodes,
            related=[node.source for node in gql_issue_or_pull_request.timeline_items.nodes],
        )

    @classmethod
    def from_gql_search_issue_or_pull_requests_with_details(
        cls, gql_search_issue_or_pull_requests_with_details: GqlSearchIssueOrPullRequestsWithDetails
    ) -> list[Self]:
        results = []

        for node in gql_search_issue_or_pull_requests_with_details.search.nodes:
            issue_or_pull_request = node.to_issue() if isinstance(node, GqlIssueWithDetails) else node.to_pull_request()

            results.append(
                cls(
                    issue_or_pr=issue_or_pull_request,
                    comments=node.comments.nodes,
                    related=[node.source for node in node.timeline_items.nodes],
                )
            )

        return results


class IssueWithDetails(BaseModel):
    issue: Issue = Field(description="The issue.")
    comments: list[Comment] = Field(description="The comments on the issue.")
    related: list[Issue | PullRequest] = Field(description="The related issues.")

    @classmethod
    def from_issue_or_pull_request_with_details(cls, issue_or_pull_request_with_details: IssueOrPullRequestWithDetails) -> Self:
        if not isinstance(issue_or_pull_request_with_details.issue_or_pr, Issue):
            msg = "Issue or pull request is not an issue."
            raise TypeError(msg)

        return cls(
            issue=issue_or_pull_request_with_details.issue_or_pr,
            comments=issue_or_pull_request_with_details.comments,
            related=issue_or_pull_request_with_details.related,
        )


class PullRequestWithDetails(BaseModel):
    pull_request: PullRequest = Field(description="The pull request.")
    comments: list[Comment] = Field(description="The comments on the pull request.")
    related: list[Issue | PullRequest] = Field(description="The related issues.")

    @classmethod
    def from_issue_or_pull_request_with_details(cls, issue_or_pull_request_with_details: IssueOrPullRequestWithDetails) -> Self:
        if not isinstance(issue_or_pull_request_with_details.issue_or_pr, PullRequest):
            msg = "Issue or pull request is not a pull request."
            raise TypeError(msg)

        return cls(
            pull_request=issue_or_pull_request_with_details.issue_or_pr,
            comments=issue_or_pull_request_with_details.comments,
            related=issue_or_pull_request_with_details.related,
        )


class TitleByIssueOrPullRequestInfo(RootModel[dict[str, str]]):
    @classmethod
    def from_issues_or_pull_requests_with_details(cls, issues_or_pull_requests_with_details: list[IssueOrPullRequestWithDetails]) -> Self:
        # sort by issue or pull request number
        issues_or_pull_requests_with_details.sort(key=lambda x: x.issue_or_pr.number)

        return cls.from_issues_or_pull_requests(
            issues_or_pull_requests=[issue_or_pull_request.issue_or_pr for issue_or_pull_request in issues_or_pull_requests_with_details]
        )

    @classmethod
    def from_issues_or_pull_requests(cls, issues_or_pull_requests: list[Issue | PullRequest]) -> Self:
        issues_or_pull_requests_by_info = {}

        for issue_or_pull_request in issues_or_pull_requests:
            key = "issue" if isinstance(issue_or_pull_request, Issue) else "pull_request"
            key: str = f"{key}:{issue_or_pull_request.number}"

            issues_or_pull_requests_by_info[key] = issue_or_pull_request.title

        return cls(root=issues_or_pull_requests_by_info)


# class RequestFilesForSummary(BaseModel):
#     """A request for files from the repository."""

#     file_requests: list[DirectoryRequest] = Field(description="Requests for files from the repository.")

#     @property
#     def files(self) -> list[str]:
#         return [file for file_request in self.file_requests for file in file_request.files]

#     def trim(self, remove_files: list[str], truncate: int) -> list[str]:
#         return [file for file in self.files if file not in remove_files][:truncate]
