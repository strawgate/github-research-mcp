from datetime import datetime
from textwrap import dedent
from typing import Any, override

from pydantic import AliasChoices, BaseModel, Field, field_serializer, field_validator

from github_research_mcp.models.graphql.base import BaseGqlQuery, extract_nodes
from github_research_mcp.models.graphql.fragments import (
    Actor,
    Issue,
    PullRequest,
    trim_comment_body,
)


class Comment(BaseModel):
    """A comment on an issue or pull request."""

    body: str
    author: Actor
    author_association: str = Field(validation_alias="authorAssociation")

    @field_serializer("body")
    def serialize_body(self, value: str) -> str:
        return trim_comment_body(value)

    @staticmethod
    def graphql_fragments() -> set[str]:
        fragment = """
            fragment gqlComment on IssueComment {
                body
                author {
                    ...gqlActor
                }
                authorAssociation
            }
            """
        return {dedent(text=fragment), *Actor.graphql_fragments()}


class IssueStub(BaseModel):
    number: int
    title: str
    created_at: datetime = Field(validation_alias="createdAt")
    state: str

    @field_serializer("created_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()

    @staticmethod
    def graphql_fragments() -> set[str]:
        fragment = """
            fragment gqlIssueStub on Issue {
                number
                title
                createdAt
                state
            }
            """
        return {dedent(text=fragment)}


class PullRequestStub(BaseModel):
    number: int
    title: str
    created_at: datetime = Field(validation_alias="createdAt")
    state: str

    @field_serializer("created_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()

    @staticmethod
    def graphql_fragments() -> set[str]:
        fragment = """
            fragment gqlPullRequestStub on PullRequest {
                number
                title
                createdAt
                state
            }
            """
        return {dedent(text=fragment)}


class TimelineItem(BaseModel):
    # actor: Actor
    # created_at: datetime = Field(validation_alias="createdAt")
    source: IssueStub | PullRequestStub = Field(validation_alias=AliasChoices("source", "subject"))

    # @field_serializer("created_at")
    # def serialize_datetime(self, value: datetime | None) -> str | None:
    #     if value is None:
    #         return None
    #     return value.isoformat()

    @staticmethod
    def graphql_fragments() -> set[str]:
        return {*Actor.graphql_fragments(), *IssueStub.graphql_fragments(), *PullRequestStub.graphql_fragments()}


class GqlPullRequestWithDetails(PullRequest):
    comments: list[Comment]
    timeline_items: list[TimelineItem] = Field(validation_alias=AliasChoices("timelineItems", "timeline_items"))

    @field_validator("comments", mode="before")
    @classmethod
    def flatten_comments(cls, value: Any) -> list[Comment]:  # pyright: ignore[reportAny]
        return extract_nodes(value)

    @field_validator("timeline_items", mode="before")
    @classmethod
    def flatten_timeline_items(cls, value: Any) -> list[TimelineItem]:  # pyright: ignore[reportAny]
        nodes = extract_nodes(value)
        # remove nodes which are empty dictionaries
        return [node for node in nodes if node != {}]  # pyright: ignore[reportAny]

    @staticmethod
    @override
    def graphql_fragments() -> set[str]:
        base_fragments: set[str] = PullRequest.graphql_fragments()

        return {*base_fragments, *Comment.graphql_fragments(), *TimelineItem.graphql_fragments()}

    def to_pull_request(self) -> PullRequest:
        return PullRequest(**self.model_dump())  # pyright: ignore[reportAny]


class GqlGetPullRequestRepository(BaseModel):
    pull_request: GqlPullRequestWithDetails | None = Field(validation_alias="issueOrPullRequest")

    @field_validator("pull_request", mode="before")
    @classmethod
    def remove_empty_pull_request(cls, value: Any) -> Any | None:  # pyright: ignore[reportAny]
        return value if value else None

    @staticmethod
    def graphql_fragments() -> set[str]:
        return {*GqlPullRequestWithDetails.graphql_fragments()}


class GqlGetPullRequest(BaseGqlQuery):
    repository: GqlGetPullRequestRepository

    @staticmethod
    @override
    def graphql_fragments() -> set[str]:
        return GqlGetPullRequestRepository.graphql_fragments()

    @staticmethod
    @override
    def graphql_query() -> str:
        fragments = "\n".join(GqlGetPullRequestRepository.graphql_fragments())

        query = """
            query GqlGetPullRequest(
                $owner: String!
                $repo: String!
                $pull_request_number: Int!
                $limit_comments: Int!
                $limit_events: Int!
            ) {
                repository(owner: $owner, name: $repo) {
                    issueOrPullRequest(number: $pull_request_number) {
                        ... on PullRequest {
                            ...gqlPullRequest

                            comments(last: $limit_comments) {
                                nodes {
                                    ...gqlComment
                                }
                            }
                            timelineItems( itemTypes: [CROSS_REFERENCED_EVENT, REFERENCED_EVENT], last: $limit_events) {
                                nodes {
                                    ... on CrossReferencedEvent {
                                        actor {
                                            ...gqlActor
                                        }
                                        createdAt
                                        source {
                                            ... on Issue {
                                                ...gqlIssueStub
                                            }
                                            ... on PullRequest {
                                                ...gqlPullRequestStub
                                            }
                                        }
                                    }
                                    ... on ReferencedEvent {
                                        actor {
                                            ...gqlActor
                                        }
                                        createdAt
                                        subject {
                                            ... on Issue {
                                                ...gqlIssueStub
                                        }
                                            ... on PullRequest {
                                                ...gqlPullRequestStub
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """
        query = dedent(text=query)

        return fragments + "\n" + query

    @staticmethod
    def to_graphql_query_variables(
        owner: str, repo: str, pull_request_number: int, limit_comments: int, limit_events: int
    ) -> dict[str, Any]:
        return {
            "owner": owner,
            "repo": repo,
            "pull_request_number": pull_request_number,
            "limit_comments": limit_comments,
            "limit_events": limit_events,
        }


class GqlIssueWithDetails(Issue):
    comments: list[Comment]
    timeline_items: list[TimelineItem] = Field(validation_alias=AliasChoices("timelineItems", "timeline_items"))

    @field_validator("comments", mode="before")
    @classmethod
    def flatten_comments(cls, value: Any) -> list[Comment]:  # pyright: ignore[reportAny]
        return extract_nodes(value)

    @field_validator("timeline_items", mode="before")
    @classmethod
    def flatten_timeline_items(cls, value: Any) -> list[TimelineItem]:  # pyright: ignore[reportAny]
        nodes = extract_nodes(value)
        # remove nodes which are empty dictionaries
        return [node for node in nodes if node != {}]  # pyright: ignore[reportAny]

    @staticmethod
    @override
    def graphql_fragments() -> set[str]:
        base_fragments: set[str] = Issue.graphql_fragments()

        return {*base_fragments, *Comment.graphql_fragments(), *TimelineItem.graphql_fragments()}

    def to_issue(self) -> Issue:
        return Issue(**self.model_dump())  # pyright: ignore[reportAny]


class GqlGetIssueRepository(BaseModel):
    issue: GqlIssueWithDetails | None = Field(validation_alias="issueOrPullRequest")

    @field_validator("issue", mode="before")
    @classmethod
    def remove_empty_issue(cls, value: Any) -> Any | None:  # pyright: ignore[reportAny]
        return value if value else None

    @staticmethod
    def graphql_fragments() -> set[str]:
        return {*GqlIssueWithDetails.graphql_fragments()}


class GqlGetIssue(BaseGqlQuery):
    repository: GqlGetIssueRepository

    @staticmethod
    @override
    def graphql_fragments() -> set[str]:
        return GqlGetIssueRepository.graphql_fragments()

    @staticmethod
    @override
    def graphql_query() -> str:
        fragments = "\n".join(GqlGetIssueRepository.graphql_fragments())

        query = """
            query GqlGetIssue(
                $owner: String!
                $repo: String!
                $issue_number: Int!
                $limit_comments: Int!
                $limit_events: Int!
            ) {
                repository(owner: $owner, name: $repo) {
                    issueOrPullRequest(number: $issue_number) {
                        ... on Issue {
                            ...gqlIssue

                            comments(last: $limit_comments) {
                                nodes {
                                    ...gqlComment
                                }
                            }
                            timelineItems( itemTypes: [CROSS_REFERENCED_EVENT, REFERENCED_EVENT], last: $limit_events) {
                                nodes {
                                    ... on CrossReferencedEvent {
                                        actor {
                                            ...gqlActor
                                        }
                                        createdAt
                                        source {
                                            ... on Issue {
                                                ...gqlIssueStub
                                            }
                                            ... on PullRequest {
                                                ...gqlPullRequestStub
                                            }
                                        }
                                    }
                                    ... on ReferencedEvent {
                                        actor {
                                            ...gqlActor
                                        }
                                        createdAt
                                        subject {
                                            ... on Issue {
                                                ...gqlIssueStub
                                        }
                                            ... on PullRequest {
                                                ...gqlPullRequestStub
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """
        query = dedent(text=query)

        return fragments + "\n" + query

    @staticmethod
    def to_graphql_query_variables(owner: str, repo: str, issue_number: int, limit_comments: int, limit_events: int) -> dict[str, Any]:
        return {
            "owner": owner,
            "repo": repo,
            "issue_number": issue_number,
            "limit_comments": limit_comments,
            "limit_events": limit_events,
        }


class GqlSearchIssues(BaseGqlQuery):
    search: list[GqlIssueWithDetails]

    @field_validator("search", mode="before")
    @classmethod
    def flatten_search(cls, value: Any) -> list[GqlIssueWithDetails]:  # pyright: ignore[reportAny]
        return extract_nodes(value)

    @staticmethod
    @override
    def graphql_fragments() -> set[str]:
        return {*GqlIssueWithDetails.graphql_fragments()}

    @staticmethod
    @override
    def graphql_query() -> str:
        fragments = "\n".join(GqlSearchIssues.graphql_fragments())
        query = """
            query GqlSearchIssues(
                $search_query: String!
                $limit_issues: Int!
                $limit_comments: Int!
                $limit_events: Int!
            ) {
                search(query: $search_query, type: ISSUE, first: $limit_issues) {
                    issueCount
                    nodes {
                        ... on Issue {
                            ...gqlIssue
                            comments(last: $limit_comments) {
                                nodes {
                                    ...gqlComment
                                }
                            }
                            timelineItems( itemTypes: [CROSS_REFERENCED_EVENT, REFERENCED_EVENT], last: $limit_events) {
                                nodes {
                                    ... on CrossReferencedEvent {
                                        actor {
                                            ...gqlActor
                                        }
                                        createdAt
                                        source {
                                            ... on Issue {
                                                ...gqlIssueStub
                                            }
                                            ... on PullRequest {
                                                ...gqlPullRequestStub
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """
        query = dedent(text=query)

        return fragments + "\n" + query

    @staticmethod
    def to_graphql_query_variables(query: str, limit_issues: int, limit_comments: int, limit_events: int) -> dict[str, Any]:
        return {
            "search_query": query,
            "limit_issues": limit_issues,
            "limit_comments": limit_comments,
            "limit_events": limit_events,
        }


class GqlSearchPullRequests(BaseGqlQuery):
    search: list[GqlPullRequestWithDetails]

    @field_validator("search", mode="before")
    @classmethod
    def flatten_search(cls, value: Any) -> list[GqlPullRequestWithDetails]:  # pyright: ignore[reportAny]
        return extract_nodes(value)

    @staticmethod
    @override
    def graphql_fragments() -> set[str]:
        return {*GqlPullRequestWithDetails.graphql_fragments()}

    @staticmethod
    @override
    def graphql_query() -> str:
        fragments = "\n".join(GqlSearchPullRequests.graphql_fragments())
        query = """
            query GqlSearchPullRequests(
                $search_query: String!
                $limit_pull_requests: Int!
                $limit_comments: Int!
                $limit_events: Int!
            ) {
                search(query: $search_query, type: ISSUE, first: $limit_pull_requests) {
                    issueCount
                    nodes {
                        ... on PullRequest {
                            ...gqlPullRequest
                            comments(last: $limit_comments) {
                                nodes {
                                    ...gqlComment
                                }
                            }
                            timelineItems( itemTypes: [CROSS_REFERENCED_EVENT, REFERENCED_EVENT], last: $limit_events) {
                                nodes {
                                    ... on CrossReferencedEvent {
                                        actor {
                                            ...gqlActor
                                        }
                                        createdAt
                                        source {
                                            ... on Issue {
                                                ...gqlIssueStub
                                            }
                                            ... on PullRequest {
                                                ...gqlPullRequestStub
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """

        query = dedent(text=query)

        return fragments + "\n" + query

    @staticmethod
    def to_graphql_query_variables(query: str, limit_pull_requests: int, limit_comments: int, limit_events: int) -> dict[str, Any]:
        return {
            "search_query": query,
            "limit_pull_requests": limit_pull_requests,
            "limit_comments": limit_comments,
            "limit_events": limit_events,
        }
