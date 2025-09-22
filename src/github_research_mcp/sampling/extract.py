import json
from textwrap import dedent
from typing import Any

from pydantic import BaseModel, TypeAdapter

ALLOWED_TYPES = BaseModel | list[BaseModel]


def object_in_text_instructions[T: ALLOWED_TYPES](object_type: type[T], require: bool = False) -> str:
    """Return instructions for extracting an object from a text string."""

    type_adapter: TypeAdapter[T] = TypeAdapter[T](object_type)
    json_schema: dict[str, Any] = type_adapter.json_schema()

    schema_and_example: str = dedent(
        f"""The schema for the object is:
```json
{json.dumps(obj=json_schema, indent=1)}"
```

Example JSON block (a generic example, not valid for {object_type.__name__}):
```json
{{
 "property_1": "value_1",
 "property_2": ["value_2_1", "value_2_2"],
 "property_3": "value_3"
}}
```

The JSON itself must be placed between the ``` tags.

The JSON does not need to be "compressed" but it should be formatted
densely, minimizing whitespace, only ever using a single space for indentation. Place short arrays and small objects on the same
line as the key for the object.

You must ensure you close any JSON tags, including arrays, objects, and strings and that
you do not leave trailing commas or other invalid JSON.
"""
    )

    if require:
        return dedent(
            f"""
The only valid response to this request is a structured object of type {object_type.__name__}.

{schema_and_example}

Any response other than providing the exact json block for {object_type.__name__} will be considered invalid."""
        ).strip()

    return dedent(
        f"""
One valid way to response to the task is to provide a structured object of type {object_type.__name__}.

{schema_and_example}

This is not required, and other forms of response are also valid.
"""
    ).strip()


def extract_json_blocks_from_text(text: str) -> list[str]:
    """Extract all JSON blocks from a text string."""

    lines = text.strip().split("\n")

    start_index: int | None = None
    end_index: int | None = None

    matches: list[str] = []

    for i, line in enumerate(lines):
        if line.startswith("```") and start_index is None:
            start_index = i + 1
            continue
        if line.startswith("```") and start_index is not None and end_index is None:
            end_index = i

        if start_index is not None and end_index is not None:
            matches.append("\n".join(lines[start_index:end_index]))
            start_index = None
            end_index = None

    return matches


def extract_single_object_from_json_block[T: ALLOWED_TYPES](json_block_text: str, object_type: type[T]) -> T:
    """Extract an object from a JSON block."""
    type_adapter: TypeAdapter[T] = TypeAdapter[T](object_type)

    json_text: str = "\n".join([line.strip() for line in json_block_text.splitlines()])

    return type_adapter.validate_json(json_text)


def extract_single_object_from_text[T: ALLOWED_TYPES](text: str, object_type: type[T]) -> T:
    """Extract an object from a Markdown JSON block provided in the text string.

    For example:
    We should investigate the following users:
    ```json
    {
        "name": "John",
        "age": 30
    }

    And determine if they are valid reports of type errors.
    ```"""

    matches: list[str] = extract_json_blocks_from_text(text)

    if len(matches) != 1:
        msg = f"Text must contain exactly one Markdown JSON block. Received {text}."
        raise ValueError(msg)

    object_text: str = matches[0]

    return extract_single_object_from_json_block(json_block_text=object_text, object_type=object_type)
