from typing import Any

import pytest
from fastmcp import Client, FastMCP
from fastmcp.experimental.sampling.handlers.openai import BaseLLMSamplingHandler
from pydantic import BaseModel, Field

from github_research_mcp.sampling.utility import new_sampling_message, structured_sample, tool_calling_sample
from tests.servers.test_public import get_result_from_call_tool_result


@pytest.fixture
async def tool_server() -> FastMCP[Any]:
    fastmcp = FastMCP[Any](name="Test Server")

    @fastmcp.tool
    async def test_tool(arg1: str, arg2: int) -> str:
        return f"Hello, world! {arg1} {arg2}"

    @fastmcp.tool
    async def test_tool2(arg1: str, arg2: int) -> str:
        return f"Hello, world! {arg1} {arg2}"

    return fastmcp


class AMadeUpPerson(BaseModel):
    name: str = Field(description="The name of a made up person.")
    age: int = Field(description="The age of a made up person.")


@pytest.fixture
async def sampling_server(sampling_handler: BaseLLMSamplingHandler, tool_server: FastMCP[Any]) -> FastMCP[Any]:
    fastmcp = FastMCP[Any](
        name="Test Server",
        sampling_handler=sampling_handler,
    )

    @fastmcp.tool
    async def test_structured_sampling() -> AMadeUpPerson:
        made_up_person, _ = await structured_sample(
            system_prompt="You are a helpful assistant.",
            messages=[new_sampling_message("user", "Return a person object with name John and age 30.")],
            response_model=AMadeUpPerson,
        )

        return made_up_person

    @fastmcp.tool
    async def test_sampling_tool_calling() -> str:
        client = Client[Any](transport=tool_server)

        await tool_calling_sample(
            system_prompt="You are a helpful assistant.",
            messages=[new_sampling_message("user", "Call all available tools please.")],
            client=client,
        )

        return "All tools called successfully."

    return fastmcp


async def test_tool_sample(sampling_server: FastMCP[Any]):
    async with Client[Any](transport=sampling_server) as client:
        await client.call_tool(
            name="test_sampling_tool_calling",
        )


async def test_structured_sample(sampling_server: FastMCP[Any]):
    async with Client[Any](transport=sampling_server) as client:
        call_tool_result = await client.call_tool(
            name="test_structured_sampling",
        )

        result = get_result_from_call_tool_result(call_tool_result)

        assert result is not None
        assert result["name"] == "John"
        assert result["age"] == 30
