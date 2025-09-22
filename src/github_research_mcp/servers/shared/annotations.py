from enum import Enum
from typing import Annotated, Literal

from fastmcp.tools.tool_transform import ArgTransform
from pydantic import Field

OWNER_DESCRIPTION = "The owner of the repository."
OWNER = Annotated[str, OWNER_DESCRIPTION]
OWNER_ARG_TRANSFORM = ArgTransform(description=OWNER_DESCRIPTION)

REPO_DESCRIPTION = "The name of the repository."
REPO = Annotated[str, REPO_DESCRIPTION]
REPO_ARG_TRANSFORM = ArgTransform(description=REPO_DESCRIPTION)

KEYWORDS = Annotated[set[str], "The keywords to search for in the issue. You may only provide up to 6 keywords."]
REQUIRE_ALL_KEYWORDS = Annotated[bool, "Whether all keywords must be present for a result to appear in the search results."]
STATE = Annotated[Literal["open", "closed", "all"], "The state of the issue."]

PAGE = Annotated[int, "The page of the search results."]
PER_PAGE = Annotated[int, "The number of results per page."]

LIMIT_COMMENTS_DESCRIPTION = "The maximum number of comments to include."
LIMIT_COMMENTS = Annotated[int, Field(description=LIMIT_COMMENTS_DESCRIPTION)]
LIMIT_COMMENTS_ARG_TRANSFORM = ArgTransform(description=LIMIT_COMMENTS_DESCRIPTION)

LIMIT_RELATED_ITEMS_DESCRIPTION = "The maximum number of related items to include."
LIMIT_RELATED_ITEMS = Annotated[int, Field(description=LIMIT_RELATED_ITEMS_DESCRIPTION)]
LIMIT_RELATED_ITEMS_ARG_TRANSFORM = ArgTransform(description=LIMIT_RELATED_ITEMS_DESCRIPTION)

TRUNCATE_LINES_DESCRIPTION = "The number of lines to truncate the content of the files to."
TRUNCATE_LINES = Annotated[int, Field(description=TRUNCATE_LINES_DESCRIPTION)]
TRUNCATE_LINES_ARG_TRANSFORM = ArgTransform(description=TRUNCATE_LINES_DESCRIPTION)

TRUNCATE_CHARACTERS_DESCRIPTION = "The number of characters to truncate the content of the files to."
TRUNCATE_CHARACTERS = Annotated[int, Field(description=TRUNCATE_CHARACTERS_DESCRIPTION)]
TRUNCATE_CHARACTERS_ARG_TRANSFORM = ArgTransform(description=TRUNCATE_CHARACTERS_DESCRIPTION)

FIND_FILES_DEPTH_DESCRIPTION = (
    "The depth of the tree to search for files. If not provided, the entire tree will be searched. Depth 0 is the root directory."
)
FIND_FILES_DEPTH = Annotated[int, Field(description=FIND_FILES_DEPTH_DESCRIPTION)]
FIND_FILES_DEPTH_ARG_TRANSFORM = ArgTransform(description=FIND_FILES_DEPTH_DESCRIPTION)

# Summary Fields


class Length(int, Enum):
    SHORT = 500
    MEDIUM = 2000
    LONG = 4000


SUMMARY_LENGTH = Annotated["Length", Field(description="The length of the summary in words.")]
SUMMARY_FOCUS = Annotated[str, Field(description="The desired focus of the summary to be produced.")]
