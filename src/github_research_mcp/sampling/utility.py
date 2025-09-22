from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal, overload

from fastmcp.server.dependencies import get_context
from fastmcp.utilities.logging import get_logger
from mcp.types import AudioContent, ContentBlock, ImageContent, ModelPreferences, SamplingMessage, TextContent
from pydantic import BaseModel
from pydantic_core import ValidationError

from github_research_mcp.sampling.extract import extract_single_object_from_text, object_in_text_instructions
from github_research_mcp.servers.shared.utility import estimate_model_tokens

if TYPE_CHECKING:
    from fastmcp.server import Context

logger = get_logger(__name__)


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


@overload
async def structured_sample[T: BaseModel](
    system_prompt: str,
    messages: Sequence[SamplingMessage],
    *,
    max_tokens: int = 2000,
    temperature: float = 0.0,
    model_preferences: ModelPreferences | None = None,
    response_model: None,
) -> tuple[ContentBlock, SamplingMessage]: ...


@overload
async def structured_sample[T: BaseModel](
    system_prompt: str,
    messages: Sequence[SamplingMessage],
    *,
    max_tokens: int = 2000,
    temperature: float = 0.0,
    model_preferences: ModelPreferences | None = None,
    response_model: type[str],
) -> tuple[str, SamplingMessage]: ...


@overload
async def structured_sample[T: BaseModel](
    system_prompt: str,
    messages: Sequence[SamplingMessage],
    *,
    max_tokens: int = 2000,
    temperature: float = 0.0,
    model_preferences: ModelPreferences | None = None,
    response_model: type[T],
) -> tuple[T, SamplingMessage]: ...


async def structured_sample[T: BaseModel](
    system_prompt: str,
    messages: Sequence[SamplingMessage],
    *,
    max_tokens: int = 2000,
    temperature: float = 0.0,
    model_preferences: ModelPreferences | None = None,
    response_model: type[str | T] | None = None,
) -> tuple[ContentBlock | str | T, SamplingMessage]:
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
        A ContentBlock if response_model is None,
            a tuple of a string and a SamplingMessage if response_model is str, or
            a tuple of a BaseModel and a SamplingMessage if response_model is a BaseModel.
    """

    context: Context = get_context()

    logger.info(f"Sampling with prompt that is {get_sampling_tokens(system_prompt, messages)} tokens.")

    extra_messages: list[SamplingMessage] = []

    if response_model and issubclass(response_model, BaseModel):
        extra_messages.append(new_user_sampling_message(content=object_in_text_instructions(object_type=response_model, require=True)))

    sampling_response: TextContent | ImageContent | AudioContent = await context.sample(  # pyright: ignore[reportAssignmentType]
        system_prompt=system_prompt,
        messages=[*messages, *extra_messages],
        temperature=temperature,
        max_tokens=max_tokens,
        model_preferences=model_preferences,
    )

    assistant_message: SamplingMessage = SamplingMessage(role="assistant", content=sampling_response)

    # Response Model is None, return a single ContentBlock
    if response_model is None:
        return sampling_response, assistant_message

    if not isinstance(sampling_response, TextContent):
        msg = "The sampling call failed to generate a valid text summary of the issue."
        raise TypeError(msg)

    # Response Model is str, return the text from the TextContent and the ContentBlock
    if issubclass(response_model, str):
        return sampling_response.text, assistant_message

    # Response Model is a BaseModel, coerce the response to the model
    try:
        return extract_single_object_from_text(sampling_response.text, object_type=response_model), assistant_message
    except ValidationError as e:
        logger.exception(f"Invalid structured response for {response_model.__name__}: {sampling_response.text}")
        msg = "The sampling call failed to generate a valid structured response."
        raise TypeError(msg) from e
