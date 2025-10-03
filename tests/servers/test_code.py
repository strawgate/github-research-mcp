import tempfile
from logging import getLogger
from pathlib import Path

import pytest
from inline_snapshot import snapshot
from pydantic import AnyHttpUrl
from rpygrep.helpers import MatchedLine

from github_research_mcp.servers.code import CodeServer, FileWithMatches

logger = getLogger(__name__)


def test_init():
    repository_server: CodeServer = CodeServer(logger=logger, clone_dir=Path("temp"))
    assert repository_server is not None


@pytest.fixture
async def repository_server():
    with tempfile.TemporaryDirectory() as temp_dir:
        repository_server: CodeServer = CodeServer(logger=logger, clone_dir=Path(temp_dir))
        yield repository_server


async def test_simple_search(repository_server: CodeServer):
    search_result: list[FileWithMatches] = await repository_server.search_code(
        owner="strawgate", repo="github-issues-e2e-test", patterns=["world!"], max_results=5
    )

    sorted_search_result: list[FileWithMatches] = sorted(search_result, key=lambda x: x.url)

    assert sorted_search_result == snapshot(
        [
            FileWithMatches(
                url=AnyHttpUrl("https://github.com/strawgate/github-issues-e2e-test/blob/main/README.md"),
                matched_lines=[
                    MatchedLine(
                        before={47: "```python", 48: "from gith_ub import ExistentialCoder", 50: "coder = ExistentialCoder()"},
                        match={51: "coder.analyze_code(\"def hello_world(): print('Hello, World!')\")"},
                        after={
                            52: "# Output: \"But what is 'Hello'? What is 'World'? Are we not all just strings in the cosmic interpreter?\"",
                            53: "```",
                            55: "## Philosophy",
                        },
                    ),
                    MatchedLine(
                        before={
                            70: "MIT License - because even in the digital realm, we must respect the cosmic copyright of existence.",
                            72: "---",
                        },
                        match={
                            74: "*\"In the beginning was the Word, and the Word was `console.log('Hello, World!')`\"* - The Gospel of G.I.T.H.U.B."
                        },
                    ),
                ],
            ),
            FileWithMatches(
                url=AnyHttpUrl("https://github.com/strawgate/github-issues-e2e-test/blob/main/main.py"),
                matched_lines=[
                    MatchedLine(
                        before={
                            32: "    # Sample code to analyze",
                            33: "    sample_code = '''",
                            34: "def hello_world():",
                            35: '    """A simple function that greets the world."""',
                        },
                        match={36: '    print("Hello, World!")'},
                        after={37: '    return "greeting_complete"', 39: 'if __name__ == "__main__":', 40: "    result = hello_world()"},
                    )
                ],
            ),
            FileWithMatches(
                url=AnyHttpUrl("https://github.com/strawgate/github-issues-e2e-test/blob/main/tests/test_existential_coder.py"),
                matched_lines=[
                    MatchedLine(
                        before={
                            27: "    def test_analyze_code_function(self):",
                            28: '        """Test analysis of function definitions."""',
                            29: "        coder = ExistentialCoder()",
                        },
                        match={30: "        code = \"def hello_world():\\n    print('Hello, World!')\""},
                        after={32: "        insights = coder.analyze_code(code)", 34: "        assert len(insights) > 0"},
                    )
                ],
            ),
        ]
    )


async def test_simple_search_function_name(repository_server: CodeServer):
    search_result: list[FileWithMatches] = await repository_server.search_code(
        owner="strawgate", repo="github-issues-e2e-test", patterns=["hello_world"], max_results=5
    )

    sorted_search_result: list[FileWithMatches] = sorted(search_result, key=lambda x: x.url)

    assert sorted_search_result == snapshot(
        [
            FileWithMatches(
                url=AnyHttpUrl("https://github.com/strawgate/github-issues-e2e-test/blob/main/README.md"),
                matched_lines=[
                    MatchedLine(
                        before={47: "```python", 48: "from gith_ub import ExistentialCoder", 50: "coder = ExistentialCoder()"},
                        match={51: "coder.analyze_code(\"def hello_world(): print('Hello, World!')\")"},
                        after={
                            52: "# Output: \"But what is 'Hello'? What is 'World'? Are we not all just strings in the cosmic interpreter?\"",
                            53: "```",
                            55: "## Philosophy",
                        },
                    )
                ],
            ),
            FileWithMatches(
                url=AnyHttpUrl("https://github.com/strawgate/github-issues-e2e-test/blob/main/main.py"),
                matched_lines=[
                    MatchedLine(
                        before={30: "    coder = ExistentialCoder()", 32: "    # Sample code to analyze", 33: "    sample_code = '''"},
                        match={34: "def hello_world():"},
                        after={
                            35: '    """A simple function that greets the world."""',
                            36: '    print("Hello, World!")',
                            37: '    return "greeting_complete"',
                        },
                    ),
                    MatchedLine(
                        before={39: 'if __name__ == "__main__":'},
                        match={40: "    result = hello_world()"},
                        after={
                            41: '    print(f"The result is: {result}")',
                            42: "'''",
                            44: '    print("🔍 Analyzing sample code for existential meaning...")',
                        },
                    ),
                ],
            ),
            FileWithMatches(
                url=AnyHttpUrl("https://github.com/strawgate/github-issues-e2e-test/blob/main/tests/test_existential_coder.py"),
                matched_lines=[
                    MatchedLine(
                        before={
                            27: "    def test_analyze_code_function(self):",
                            28: '        """Test analysis of function definitions."""',
                            29: "        coder = ExistentialCoder()",
                        },
                        match={30: "        code = \"def hello_world():\\n    print('Hello, World!')\""},
                        after={32: "        insights = coder.analyze_code(code)", 34: "        assert len(insights) > 0"},
                    )
                ],
            ),
        ]
    )


async def test_simple_search_class_name(repository_server: CodeServer):
    search_result: list[FileWithMatches] = await repository_server.search_code(
        owner="strawgate", repo="github-issues-e2e-test", patterns=["ExistentialCoder"], max_results=1
    )

    assert search_result == snapshot(
        [
            FileWithMatches(
                url=AnyHttpUrl("https://github.com/strawgate/github-issues-e2e-test/blob/main/src/existential_coder.py"),
                matched_lines=[
                    MatchedLine(
                        before={26: "    contemplation_level: ContemplationLevel", 27: "    line_number: Optional[int] = None"},
                        match={30: "class ExistentialCoder:"},
                        after={
                            31: '    """',
                            32: "    The main class that provides existential guidance for developers.",
                            34: "    This class analyzes code not just for syntax errors, but for deeper",
                        },
                    )
                ],
            )
        ]
    )


async def test_simple_search_class_name_exclude_globs(repository_server: CodeServer):
    search_result: list[FileWithMatches] = await repository_server.search_code(
        owner="strawgate", repo="github-issues-e2e-test", patterns=["ExistentialCoder"], exclude_globs=["*.py"], max_results=1
    )

    assert search_result == snapshot(
        [
            FileWithMatches(
                url=AnyHttpUrl("https://github.com/strawgate/github-issues-e2e-test/blob/main/README.md"),
                matched_lines=[
                    MatchedLine(before={45: "## Usage", 47: "```python"}, match={48: "from gith_ub import ExistentialCoder"}),
                    MatchedLine(
                        match={50: "coder = ExistentialCoder()"},
                        after={
                            51: "coder.analyze_code(\"def hello_world(): print('Hello, World!')\")",
                            52: "# Output: \"But what is 'Hello'? What is 'World'? Are we not all just strings in the cosmic interpreter?\"",
                            53: "```",
                        },
                    ),
                ],
            )
        ]
    )


async def test_simple_search_class_name_exclude_types(repository_server: CodeServer):
    search_result: list[FileWithMatches] = await repository_server.search_code(
        owner="strawgate", repo="github-issues-e2e-test", patterns=["ExistentialCoder"], exclude_types=["python"], max_results=10
    )

    assert search_result == snapshot(
        [
            FileWithMatches(
                url=AnyHttpUrl("https://github.com/strawgate/github-issues-e2e-test/blob/main/README.md"),
                matched_lines=[
                    MatchedLine(before={45: "## Usage", 47: "```python"}, match={48: "from gith_ub import ExistentialCoder"}),
                    MatchedLine(
                        match={50: "coder = ExistentialCoder()"},
                        after={
                            51: "coder.analyze_code(\"def hello_world(): print('Hello, World!')\")",
                            52: "# Output: \"But what is 'Hello'? What is 'World'? Are we not all just strings in the cosmic interpreter?\"",
                            53: "```",
                        },
                    ),
                ],
            )
        ]
    )
