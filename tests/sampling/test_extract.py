from textwrap import dedent

from inline_snapshot import snapshot
from pydantic import BaseModel, Field

from github_research_mcp.sampling.extract import extract_json_blocks_from_text, extract_single_object_from_text, object_in_text_instructions


class StructuredObject(BaseModel):
    """A structured object docstring."""

    name: str = Field(description="The name of the object.")
    age: int = Field(description="The age of the object.")


def test_object_in_text_instructions():
    assert object_in_text_instructions(StructuredObject) == snapshot("""\
One valid way to response to the task is to provide a structured object of type StructuredObject.

The schema for the object is:
```json
{
 "description": "A structured object docstring.",
 "properties": {
  "name": {
   "description": "The name of the object.",
   "title": "Name",
   "type": "string"
  },
  "age": {
   "description": "The age of the object.",
   "title": "Age",
   "type": "integer"
  }
 },
 "required": [
  "name",
  "age"
 ],
 "title": "StructuredObject",
 "type": "object"
}"
```

Example JSON block (a generic example, not valid for StructuredObject):
```json
{
 "property_1": "value_1",
 "property_2": ["value_2_1", "value_2_2"],
 "property_3": "value_3"
}
```

The JSON itself must be placed between the ``` tags.

The JSON does not need to be "compressed" but it should be formatted
densely, minimizing whitespace, only ever using a single space for indentation. Place short arrays and small objects on the same
line as the key for the object.

You must ensure you close any JSON tags, including arrays, objects, and strings and that
you do not leave trailing commas or other invalid JSON.


This is not required, and other forms of response are also valid.\
""")


def test_extract_json_blocks_from_text():
    text = """
    This is a test text that occurs before the json block.
    ```json
    {
        "name": "John",
        "age": 30
    }
    ```

    ```json
    {
        "name": "Jane",
        "age": 25
    }
    ```

    This is a test text that occurs after the json block.
    """
    assert extract_json_blocks_from_text(text) == snapshot([])


def test_extract_single_object_from_text():
    text = dedent("""
    ```json
    {
        "name": "John",
        "age": 30
    }
    ```
    """)
    assert extract_single_object_from_text(text, StructuredObject) == StructuredObject(name="John", age=30)


def test_extract_object_from_text_extra_text():
    text = dedent("""
    Yes, I would be happy to provide the information you requested in a json block.
    ```json
    {
        "name": "John",
        "age": 30
    }
    ```

    This is a test text that occurs after the json block.
    """)
    assert extract_single_object_from_text(text, StructuredObject) == StructuredObject(name="John", age=30)
