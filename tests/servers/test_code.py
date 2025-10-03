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
        owner="strawgate", repo="github-issues-e2e-test", patterns=["ExistentialCoder"], max_results=5
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
            ),
            FileWithMatches(
                url=AnyHttpUrl("https://github.com/strawgate/github-issues-e2e-test/blob/main/main.py"),
                matched_lines=[
                    MatchedLine(
                        before={6: "This is the main entry point for the G.I.T.H.U.B. application.", 7: '"""'},
                        match={9: "from src.existential_coder import ExistentialCoder"},
                        after={
                            10: "from src.philosopher_agent import PhilosopherAgent",
                            11: "from src.zen_master import ZenMaster",
                            12: "from src.oracle import Oracle",
                            13: "from src.utils import contemplate_code, find_meaning_in_bugs",
                        },
                    ),
                    MatchedLine(
                        before={26: '    print("=" * 60)', 27: "    print()", 29: "    # Initialize the existential coder"},
                        match={30: "    coder = ExistentialCoder()"},
                        after={32: "    # Sample code to analyze", 33: "    sample_code = '''", 34: "def hello_world():"},
                    ),
                ],
            ),
            FileWithMatches(
                url=AnyHttpUrl("https://github.com/strawgate/github-issues-e2e-test/blob/main/src/cli.py"),
                matched_lines=[
                    MatchedLine(
                        before={
                            8: "from rich.console import Console",
                            9: "from rich.panel import Panel",
                            10: "from rich.text import Text",
                            11: "from rich.prompt import Prompt",
                        },
                        match={12: "from .existential_coder import ExistentialCoder, ContemplationLevel"},
                        after={
                            13: "from .philosopher_agent import PhilosopherAgent",
                            14: "from .zen_master import ZenMaster",
                            15: "from .oracle import Oracle",
                        },
                    ),
                    MatchedLine(
                        before={
                            51: "        with open(file_path, 'r') as f:",
                            52: "            code = f.read()",
                            54: "        contemplation_level = ContemplationLevel(level)",
                        },
                        match={55: "        coder = ExistentialCoder(contemplation_level)"},
                        after={
                            56: "        insights = coder.analyze_code(code, file_path)",
                            58: '        console.print(f"\\n[bold green]Analyzing {file_path}...[/bold green]")',
                            59: '        console.print(f"[dim]Contemplation Level: {level}[/dim]\\n")',
                        },
                    ),
                    MatchedLine(
                        before={
                            79: '    """Generate a philosophical commit message based on your changes."""',
                            80: "    if not changes:",
                            81: '        changes = ["Made some changes"]',
                        },
                        match={83: "    coder = ExistentialCoder()"},
                        after={
                            84: "    message = coder.generate_commit_message(list(changes))",
                            86: "    console.print(Panel(",
                            87: "        message,",
                        },
                    ),
                ],
            ),
            FileWithMatches(
                url=AnyHttpUrl("https://github.com/strawgate/github-issues-e2e-test/blob/main/tests/test_existential_coder.py"),
                matched_lines=[
                    MatchedLine(
                        before={1: '"""'},
                        match={2: "Tests for the ExistentialCoder class."},
                        after={
                            4: "These tests verify that the existential coder provides meaningful",
                            5: "philosophical insights about code.",
                            6: '"""',
                        },
                    ),
                    MatchedLine(
                        before={8: "import pytest"},
                        match={9: "from src.existential_coder import ExistentialCoder, ContemplationLevel, CodeInsight"},
                    ),
                    MatchedLine(match={12: "class TestExistentialCoder:"}),
                    MatchedLine(match={13: '    """Test cases for the ExistentialCoder class."""'}, after={15: "    def test_init(self):"}),
                    MatchedLine(match={16: '        """Test that ExistentialCoder initializes correctly."""'}),
                    MatchedLine(
                        match={17: "        coder = ExistentialCoder()"},
                        after={
                            18: "        assert coder.contemplation_level == ContemplationLevel.DEEP",
                            19: "        assert len(coder.philosophical_questions) > 0",
                            20: "        assert len(coder.wisdom_quotes) > 0",
                        },
                    ),
                ],
            ),
            FileWithMatches(
                url=AnyHttpUrl("https://github.com/strawgate/github-issues-e2e-test/blob/main/src/__init__.py"),
                matched_lines=[
                    MatchedLine(
                        before={
                            10: '__version__ = "0.1.0"',
                            11: '__author__ = "The Digital Sages"',
                            12: '__email__ = "wisdom@gith-ub.dev"',
                        },
                        match={14: "from .existential_coder import ExistentialCoder"},
                        after={
                            15: "from .philosopher_agent import PhilosopherAgent",
                            16: "from .zen_master import ZenMaster",
                            17: "from .oracle import Oracle",
                            18: "from .utils import contemplate_code, find_meaning_in_bugs",
                        },
                    ),
                    MatchedLine(
                        before={20: "__all__ = ["},
                        match={21: '    "ExistentialCoder",'},
                        after={22: '    "PhilosopherAgent",', 23: '    "ZenMaster",', 24: '    "Oracle",', 25: '    "contemplate_code",'},
                    ),
                ],
            ),
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
