import asyncio
from collections.abc import Sequence
from logging import Logger
from typing import TYPE_CHECKING, Any, Literal

import yaml
from fastmcp.client import Client
from fastmcp.client.client import CallToolResult
from fastmcp.server.dependencies import get_context
from fastmcp.utilities.logging import get_logger
from mcp.types import (
    AudioContent,
    ClientCapabilities,
    ContentBlock,
    ImageContent,
    ModelPreferences,
    SamplingCapability,
    SamplingMessage,
    TextContent,
    Tool,
)
from pydantic import BaseModel, Field
from pydantic_core import ValidationError

from github_research_mcp.sampling.extract import (
    ALLOWED_STRUCTURAL_SAMPLING_TYPES,
    extract_single_object_from_text,
    object_in_text_instructions,
)

if TYPE_CHECKING:
    from fastmcp.server import Context

logger = get_logger(__name__)


def dump_yaml_one(value: Any) -> str:  # pyright: ignore[reportAny]
    return yaml.safe_dump(value, indent=1, sort_keys=False, width=400)


def dump_yaml(value: Any | list[Any]) -> str:
    if isinstance(value, list):
        return "\n".join([dump_yaml_one(item) for item in value])  # pyright: ignore[reportUnknownVariableType]

    return dump_yaml_one(value)


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens for a given text."""
    return len(text) // 4


def estimate_model_tokens(basemodel: BaseModel | Sequence[BaseModel]) -> int:
    """Estimate the number of tokens for a given base model."""
    if isinstance(basemodel, Sequence):
        return sum(estimate_model_tokens(item) for item in basemodel)

    return estimate_tokens(basemodel.model_dump_json())


def get_sampling_tokens(system_prompt: str, messages: Sequence[SamplingMessage]) -> int:
    """Get the size of a sampling message."""

    system_prompt_size = len(system_prompt) // 4

    return system_prompt_size + estimate_model_tokens(basemodel=messages)


def new_sampling_message(role: Literal["user", "assistant"], content: str | list[str]) -> SamplingMessage:
    if isinstance(content, list):
        content = "\n".join(content)

    return SamplingMessage(role=role, content=TextContent(type="text", text=content))


def new_assistant_sampling_message(content: str | list[str]) -> SamplingMessage:
    return new_sampling_message("assistant", content)


def new_user_sampling_message(content: str | list[str]) -> SamplingMessage:
    return new_sampling_message("user", content)


class SamplingSupportRequiredError(Exception):
    """A sampling support required error from the GitHub Research sampling utility."""

    def __init__(self):
        super().__init__("Your client does not support sampling. Sampling support is required to use the summarization tools.")


class StructuredSamplingValidationError(Exception):
    """A structured sampling validation error from the GitHub Research sampling utility."""

    def __init__(self, message: str):
        super().__init__(message)


async def sample(
    system_prompt: str,
    messages: Sequence[SamplingMessage],
    *,
    max_tokens: int = 2000,
    temperature: float = 0.0,
    model_preferences: ModelPreferences | None = None,
) -> tuple[str, SamplingMessage]:
    """Sample a response from the server.

    Provides the text response as well as the Assistant SamplingMessage for continuing the conversation.
    """

    context: Context = get_context()

    logger.info(f"Sampling with prompt that is {get_sampling_tokens(system_prompt, messages)} tokens.")

    sampling_response: TextContent | ImageContent | AudioContent = await context.sample(
        system_prompt=system_prompt,
        messages=[*messages],
        temperature=temperature,
        max_tokens=max_tokens,
        model_preferences=model_preferences,
    )

    if not isinstance(sampling_response, TextContent):
        msg = "The sampling call failed to generate a valid text response."
        raise TypeError(msg)

    logger.info(f"Sampling response was {len(sampling_response.text) // 4} tokens.")

    assistant_message: SamplingMessage = SamplingMessage(role="assistant", content=sampling_response)

    return sampling_response.text, assistant_message


async def structured_sample[T: ALLOWED_STRUCTURAL_SAMPLING_TYPES](
    system_prompt: str,
    messages: Sequence[SamplingMessage],
    *,
    max_tokens: int = 2000,
    temperature: float = 0.0,
    model_preferences: ModelPreferences | None = None,
    response_model: type[T],
    retries: int = 3,
) -> tuple[T, SamplingMessage]:
    """Sample a response from the server. Optionally produce a structured response.
    Provides an Assistant SamplingMessage as well as the response for continuing the conversation.

    Args:
        system_prompt: The system prompt to use for the sampling.
        messages: The messages to use for the sampling.
        max_tokens: The maximum number of tokens to generate.
        temperature: The temperature to use for the sampling.
        model_preferences: The model preferences to use for the sampling.
        response_model: The response model to use for the sampling.

    Returns:
        A tuple of a BaseModel and a SamplingMessage.
    """

    json_schema_instructions: SamplingMessage = new_user_sampling_message(
        content=object_in_text_instructions(object_type=response_model, require=True)
    )

    extra_messages: list[SamplingMessage] = [json_schema_instructions]

    for retry in range(retries):
        response, assistant_message = await sample(
            system_prompt=system_prompt,
            messages=[*messages, *extra_messages],
            temperature=temperature,
            max_tokens=max_tokens,
            model_preferences=model_preferences,
        )

        try:
            return extract_single_object_from_text(response, object_type=response_model), assistant_message
        except ValidationError as e:
            msg = (
                f"The sampling call failed to generate a valid structured response (retry {retry + 1} of {retries}). Please try again: {e}"
            )
            logger.warning(msg)

            extra_messages.extend([assistant_message, new_user_sampling_message(content=msg)])

    raise StructuredSamplingValidationError(
        message=f"The sampling call failed to generate a valid structured response in {retries} retries."
    )


class SamplingToolCallRequest(BaseModel):
    """A request to call a tool."""

    tool_call_id: str = Field(description="The ID of the tool call. Can be anything as long as it is unique.")
    tool_name: str = Field(description="The name of the tool to call.")
    arguments: dict[str, Any] = Field(description="The arguments to pass to the tool.")

    async def execute(self, client: Client[Any], logger: Logger | None = None) -> "SamplingToolCallResult":
        logger = logger or get_logger(__name__)

        logger.info(f"Calling tool {self.tool_name}: id:{self.tool_call_id} with arguments {self.arguments}.")

        call_tool_result: CallToolResult = await client.call_tool(
            name=self.tool_name,
            arguments=self.arguments,
            raise_on_error=False,
        )

        sampling_tool_call_result: SamplingToolCallResult = SamplingToolCallResult.from_call_tool_result(
            sampling_tool_call_request=self, call_tool_result=call_tool_result
        )

        logger.info(f"Tool {self.tool_name}: id:{self.tool_call_id} returned {sampling_tool_call_result.result_tokens()} tokens.")

        return sampling_tool_call_result


class MultipleSamplingToolCallsRequests(BaseModel):
    """A request for a batch of tool calls."""

    tool_calls: list[SamplingToolCallRequest]
    done: bool = Field(description="Set to true if you are done making tool calls.")


class SamplingToolCallResult(SamplingToolCallRequest):
    result: list[ContentBlock] | dict[str, Any] | Any

    @classmethod
    def from_call_tool_result(
        cls, sampling_tool_call_request: SamplingToolCallRequest, call_tool_result: CallToolResult
    ) -> "SamplingToolCallResult":
        result: dict[str, Any]

        if call_tool_result.structured_content:
            result = call_tool_result.structured_content

            if "result" in result:
                result = result["result"]  # pyright: ignore[reportAny]

        else:
            result = {"result": [content_block.model_dump() for content_block in call_tool_result.content]}

        return cls(
            tool_call_id=sampling_tool_call_request.tool_call_id,
            tool_name=sampling_tool_call_request.tool_name,
            arguments=sampling_tool_call_request.arguments,
            result=result,
        )

    def to_markdown(self) -> str:
        results_text: str = dump_yaml(self.result)
        return f"""# Tool Call `{self.tool_name}`: id:{self.tool_call_id}
## Results
``````yaml
{results_text}
``````
"""

    def to_sampling_message(self) -> SamplingMessage:
        return SamplingMessage(role="user", content=TextContent(type="text", text=self.to_markdown()))

    def result_tokens(self) -> int:
        return len(self.to_markdown()) // 4


def format_tool_schemas(tools: list[Tool]) -> str:
    return "\n".join([tool.model_dump_json(indent=1, exclude={"outputSchema", "meta", "annotations", "title"}) for tool in tools])


async def tool_calling_sample(
    system_prompt: str,
    client: Client[Any],
    messages: Sequence[SamplingMessage],
    *,
    max_tokens: int = 2000,
    temperature: float = 0.0,
    model_preferences: ModelPreferences | None = None,
    max_tool_calls: int = 5,
    parallel_tool_calls: bool = False,
) -> tuple[SamplingMessage, list[SamplingMessage], bool]:
    """Sample a response from the server."""

    async with client as connected_client:
        tools: list[Tool] = await connected_client.list_tools()

        tool_instructions_text: str = f"""
The following tools are available to call:
``````json
{format_tool_schemas(tools)}
``````

You may now call up to {max_tool_calls} tools.
"""

        tool_instructions: SamplingMessage = new_user_sampling_message(content=tool_instructions_text)

        tool_calls_request, assistant_message = await structured_sample(
            system_prompt=system_prompt,
            messages=[*messages, tool_instructions],
            temperature=temperature,
            max_tokens=max_tokens,
            model_preferences=model_preferences,
            response_model=MultipleSamplingToolCallsRequests,
        )

        logger.info(f"Sampling demands {len(tool_calls_request.tool_calls)} tool calls.")

        tool_calls: list[SamplingToolCallRequest] = tool_calls_request.tool_calls[:max_tool_calls]

        tool_calls_results: list[SamplingToolCallResult] = []

        if parallel_tool_calls:
            tool_calls_results = await asyncio.gather(
                *[tool_call.execute(client=connected_client, logger=logger) for tool_call in tool_calls],
            )
        else:
            tool_calls_results = [await tool_call.execute(client=connected_client, logger=logger) for tool_call in tool_calls]

        return assistant_message, [result.to_sampling_message() for result in tool_calls_results], tool_calls_request.done


async def multi_turn_tool_calling_sample(
    system_prompt: str,
    client: Client[Any],
    messages: Sequence[SamplingMessage],
    *,
    max_tokens: int = 2000,
    temperature: float = 0.0,
    model_preferences: ModelPreferences | None = None,
    max_tool_calls: int = 5,
    max_turns: int = 5,
    parallel_tool_calls: bool = False,
) -> list[SamplingMessage]:
    """Sample a response from the server."""

    new_messages: list[SamplingMessage] = []

    for _ in range(max_turns):
        assistant_message, tool_messages, done = await tool_calling_sample(
            system_prompt=system_prompt,
            messages=[*messages, *new_messages],
            max_tokens=max_tokens,
            temperature=temperature,
            model_preferences=model_preferences,
            max_tool_calls=max_tool_calls,
            client=client,
            parallel_tool_calls=parallel_tool_calls,
        )

        new_messages.extend([assistant_message, *tool_messages])

        if done:
            logger.info("Sampling returns `done`.")
            break

    return new_messages


def sampling_is_supported() -> bool:
    """Check if the client supports sampling."""

    context: Context = get_context()

    if context.fastmcp.sampling_handler is not None:
        return True

    if context.session.check_client_capability(capability=ClientCapabilities(sampling=SamplingCapability())):  # noqa: SIM103
        return True

    return False
