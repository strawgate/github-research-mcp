import os

from fastmcp.experimental.sampling.handlers.openai import OpenAISamplingHandler
from fastmcp.utilities.logging import get_logger

from github_research_mcp.vendored.google_genai import GoogleGenaiSamplingHandler

logger = get_logger(__name__)


def get_sampling_handler() -> GoogleGenaiSamplingHandler | OpenAISamplingHandler | None:
    if os.getenv("GOOGLE_API_KEY"):
        return GoogleGenaiSamplingHandler(default_model=os.getenv("GOOGLE_MODEL") or "gemini-2.5-flash")

    if os.getenv("OPENAI_API_KEY"):
        return OpenAISamplingHandler(default_model=os.getenv("OPENAI_MODEL") or "gpt-4o")  # pyright: ignore[reportArgumentType]

    logger.warning(
        msg=(
            "No sampling handler found, sampling requests to clients that do not support sampling will fail. "
            "Set OPENAI_API_KEY or GOOGLE_API_KEY to use a sampling handler. "
        )
    )

    return None
