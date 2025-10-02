from datetime import datetime
from textwrap import dedent
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, computed_field, field_serializer, field_validator
from pydantic.aliases import AliasChoices

from github_research_mcp.models.graphql.base import extract_nodes


def owner_repository_from_url(url: str) -> tuple[str, str]:
    """Get owner and repository from URL."""
    if "/" not in url:
        msg = f"URL must be in format 'https://github.com/owner/repository', got: {url}"
        raise ValueError(msg)
    if not url.startswith("https://github.com/"):
        msg = f"URL must be in format 'https://github.com/owner/repository', got: {url}"
        raise ValueError(msg)

    parsed_url = urlparse(url)
    owner = parsed_url.path.split("/")[1]
    repository = parsed_url.path.split("/")[2]

    return owner, repository


def owner_repository_issue_number_from_url(url: str) -> tuple[str, str, int]:
    """Get owner, repository, and issue number from URL."""
    if "/" not in url:
        msg = f"URL must be in format 'https://github.com/owner/repository/issues/number', got: {url}"
        raise ValueError(msg)

    if not url.startswith("https://github.com/"):
        msg = f"URL must be in format 'https://github.com/owner/repository/issues/number', got: {url}"
        raise ValueError(msg)

    parsed_url = urlparse(url)
    owner = parsed_url.path.split("/")[1]
    repository = parsed_url.path.split("/")[2]
    issue_number = parsed_url.path.split("/")[4]

    return owner, repository, int(issue_number)


def get_comment_id_from_url(url: str) -> int:
    """Parses the comment ID from the URL:
    https://github.com/strawgate/github-issues-e2e-test/issues/1#issuecomment-3259977946
    """

    parsed_url = urlparse(url)
    comment_id = parsed_url.fragment.split("-")[1]
    return int(comment_id)


def dedent_set(fragments: set[str]) -> set[str]:
    return {dedent(text=fragment) for fragment in fragments}


class Actor(BaseModel):
    """A user, bot, or app on GitHub."""

    user_type: str
    login: str

    @staticmethod
    def graphql_fragments() -> set[str]:
        fragment = """
            fragment gqlActor on Actor {
                __typename
                user_type: __typename
                login
            }
            """
        return {dedent(text=fragment)}


class Comment(BaseModel):
    """A comment on an issue or pull request."""

    url: str
    body: str
    author: Actor
    author_association: str = Field(validation_alias="authorAssociation")
    created_at: datetime = Field(validation_alias="createdAt")
    updated_at: datetime = Field(validation_alias="updatedAt")

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()

    @computed_field
    @property
    def owner(self) -> str:
        owner, _ = owner_repository_from_url(self.url)
        return owner

    @computed_field
    @property
    def repository(self) -> str:
        _, repository = owner_repository_from_url(self.url)
        return repository

    @computed_field
    @property
    def issue_number(self) -> int:
        _, _, issue_number = owner_repository_issue_number_from_url(self.url)
        return issue_number

    @computed_field
    @property
    def comment_id(self) -> int:
        return get_comment_id_from_url(self.url)

    @staticmethod
    def graphql_fragments() -> set[str]:
        fragment = """
            fragment gqlComment on IssueComment {
                body
                url
                author {
                    ...gqlActor
                }
                authorAssociation
                createdAt
                updatedAt
            }
            """
        return {dedent(text=fragment), *Actor.graphql_fragments()}


class Label(BaseModel):
    """A label on an issue or pull request."""

    name: str

    @staticmethod
    def graphql_fragments() -> set[str]:
        fragment = """
            fragment gqlLabelName on Label {
                name
            }
            """
        return {dedent(text=fragment)}


class Issue(BaseModel):
    """An issue on GitHub."""

    number: int
    url: str
    title: str
    body: str
    state: str

    author: Actor
    author_association: str = Field(validation_alias=AliasChoices("authorAssociation", "author_association"))
    created_at: datetime = Field(validation_alias=AliasChoices("createdAt", "created_at"))
    closed_at: datetime | None = Field(default=None, validation_alias=AliasChoices("closedAt", "closed_at"))

    labels: list[Label]

    assignees: list[Actor]

    @computed_field
    @property
    def owner(self) -> str:
        owner, _ = owner_repository_from_url(self.url)
        return owner

    @computed_field
    @property
    def repository(self) -> str:
        _, repository = owner_repository_from_url(self.url)
        return repository

    @field_validator("labels", "assignees", mode="before")
    @classmethod
    def flatten_labels_and_assignees(cls, value: Any) -> Any:  # pyright: ignore[reportAny]
        return extract_nodes(value)

    @field_serializer("created_at", "closed_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()

    @staticmethod
    def graphql_fragments() -> set[str]:
        fragment = """
            fragment gqlIssue on Issue {
                number
                url
                title
                body
                state
                author {
                    ...gqlActor
                }
                authorAssociation
                createdAt
                labels(first: 10) {
                    nodes {
                        ...gqlLabelName
                    }
                }
                assignees(first: 5) {
                    nodes {
                        ...gqlActor
                    }
                }
            }
            """
        return {dedent(text=fragment), *Actor.graphql_fragments(), *Label.graphql_fragments()}


class MergeCommit(BaseModel):
    oid: str


class PullRequest(BaseModel):
    """A pull request on GitHub."""

    url: str
    number: int
    title: str
    body: str
    state: str
    merged: bool
    author: Actor
    created_at: datetime = Field(validation_alias=AliasChoices("createdAt", "created_at"))
    closed_at: datetime | None = Field(default=None, validation_alias=AliasChoices("closedAt", "closed_at"))
    merged_at: datetime | None = Field(default=None, validation_alias=AliasChoices("mergedAt", "merged_at"))
    merge_commit: MergeCommit | None = Field(validation_alias=AliasChoices("mergeCommit", "merge_commit"))

    labels: list[Label]

    assignees: list[Actor]

    @computed_field
    @property
    def owner(self) -> str:
        owner, _ = owner_repository_from_url(self.url)
        return owner

    @computed_field
    @property
    def repository(self) -> str:
        _, repository = owner_repository_from_url(self.url)
        return repository

    @field_validator("labels", "assignees", mode="before")
    @classmethod
    def flatten_labels_and_assignees(cls, value: Any) -> Any:  # pyright: ignore[reportAny]
        return extract_nodes(value)

    @field_serializer("created_at", "closed_at", "merged_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()

    @staticmethod
    def graphql_fragments() -> set[str]:
        fragment = """
            fragment gqlPullRequest on PullRequest {
                number
                url
                title
                body
                state
                authorAssociation
                author {
                    ...gqlActor
                }
                createdAt
                merged
                mergedAt
                mergeCommit {
                    oid
                }
                closedAt
                labels(first: 10) {
                    nodes {
                    ...gqlLabelName
                    }
                }
                assignees(first: 5) {
                    nodes {
                    ...gqlActor
                    }
                }
            }
            """
        return {dedent(text=fragment), *Actor.graphql_fragments(), *Label.graphql_fragments()}
