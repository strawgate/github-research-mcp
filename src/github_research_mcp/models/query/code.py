from collections.abc import Sequence
from typing import Self, override

from github_research_mcp.models.query.base import (
    AssigneeQualifier,
    AuthorQualifier,
    BaseQuery,
    IssueTypeQualifier,
    KeywordQualifier,
    LabelQualifier,
    LanguageQualifier,
    OwnerQualifier,
    PathQualifier,
    RepoQualifier,
    StateQualifier,
    SymbolQualifier,
)

SimpleCodeSearchQualifierTypes = (
    AssigneeQualifier
    | AuthorQualifier
    | IssueTypeQualifier
    | LabelQualifier
    | PathQualifier
    | LanguageQualifier
    | OwnerQualifier
    | RepoQualifier
    | StateQualifier
    | SymbolQualifier
)

AdvancedCodeSearchQualifierTypes = KeywordQualifier | OwnerQualifier | RepoQualifier | SymbolQualifier


class CodeSearchQuery(BaseQuery[SimpleCodeSearchQualifierTypes, AdvancedCodeSearchQualifierTypes]):
    """The `CodeSearchQuery` operator searches for code."""

    @override
    def to_query(self) -> str:
        query = super().to_query()
        return f"{query}"

    @classmethod
    def from_repo_or_owner(
        cls, owner: str | None = None, repo: str | None = None, qualifiers: Sequence[SimpleCodeSearchQualifierTypes] | None = None
    ) -> Self:
        query_qualifiers: list[SimpleCodeSearchQualifierTypes] = []

        if owner is not None:
            if repo is None:
                query_qualifiers.append(OwnerQualifier(owner=owner))
            else:
                query_qualifiers.append(RepoQualifier(owner=owner, repo=repo))

        if qualifiers:
            query_qualifiers.extend(qualifiers)

        return cls(qualifiers=query_qualifiers)
