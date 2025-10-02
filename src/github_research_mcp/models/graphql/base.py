from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class BaseGqlQuery(BaseModel, ABC):  # pyright: ignore[reportUnsafeMultipleInheritance]
    @staticmethod
    @abstractmethod
    def graphql_fragments() -> set[str]: ...

    @staticmethod
    @abstractmethod
    def graphql_query() -> str: ...


def extract_nodes(value: Any) -> list[Any]:  # pyright: ignore[reportAny]
    if isinstance(value, dict):
        nodes: Any | None = value.get("nodes")  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        if isinstance(nodes, list):
            return nodes  # pyright: ignore[reportUnknownVariableType]

    msg = f"Expected a list of nodes, got {value}"
    raise ValueError(msg)


class Nodes[T](BaseModel):
    nodes: list[T]
