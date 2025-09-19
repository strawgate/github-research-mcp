import os

from fastmcp.experimental.sampling.handlers.openai import OpenAISamplingHandler

from github_research_mcp.vendored.google_genai import GoogleGenaiSamplingHandler


def get_sampling_handler():
    if os.getenv("GOOGLE_API_KEY"):
        return GoogleGenaiSamplingHandler(default_model=os.getenv("GOOGLE_MODEL") or "gemini-2.5-flash")

    if os.getenv("OPENAI_API_KEY"):
        return OpenAISamplingHandler(default_model=os.getenv("OPENAI_MODEL") or "gpt-4o")  # pyright: ignore[reportArgumentType]

    msg = "No API key found for Google or OpenAI"
    raise ValueError(msg)
