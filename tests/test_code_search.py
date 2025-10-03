import os
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

import pytest
from dirty_equals import IsList
from fastmcp import FastMCP
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from inline_snapshot import snapshot

from github_research_mcp.code_search import new_mcp_server
from tests.conftest import dump_list_for_snapshot

if TYPE_CHECKING:
    from fastmcp.client.client import CallToolResult


@pytest.fixture
def code_search_mcp() -> FastMCP[Any]:
    os.environ["OWNER_ALLOWLIST"] = "strawgate"
    return new_mcp_server()


@pytest.fixture
async def code_search_mcp_client(code_search_mcp: FastMCP[Any]) -> AsyncGenerator[Client[FastMCPTransport], Any]:
    async with Client[FastMCPTransport](transport=code_search_mcp) as code_search_mcp_client:
        yield code_search_mcp_client


async def test_code_search_mcp_client(code_search_mcp_client: Client[FastMCPTransport]) -> None:
    list_tools = await code_search_mcp_client.list_tools()
    assert dump_list_for_snapshot(list_tools, exclude_keys=["outputSchema", "meta"]) == snapshot(
        [
            {
                "name": "search_code",
                "description": """\
Search the code in the default branch of the repository.

Up to 5 matches per file will be returned, Search is not case-sensitive, and up to 4 lines of context will
be returned before and after the match. Globs are similar to the globs used with `grep` on the command line.

`Patterns` are searched in the contents of the code. Do not use patterns to search for file paths or file names.

For example, `python` will search for Python files, and `java` will search for Java files.
If not provided, common types are excluded by default (binary files, lock files, etc).\
""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "The owner of the repository."},
                        "repo": {"type": "string", "description": "The repository name."},
                        "patterns": {
                            "description": "The regular expressions to search for in the contents of the code. For example: `def hello_world`. Invalid regex will be rejected.",
                            "items": {"type": "string"},
                            "type": "array",
                        },
                        "include_globs": {
                            "anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}],
                            "default": None,
                            "description": "The globs to include in the search. For example: '*.py'",
                        },
                        "exclude_globs": {
                            "anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}],
                            "default": None,
                            "description": "The globs to exclude in the search. For example: '*.pyc'",
                        },
                        "include_types": {
                            "anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}],
                            "default": None,
                            "description": "The types to include in the search. For example: 'python'. Available types include: ('ada', 'agda', 'aidl', 'alire', 'amake', 'asciidoc', 'asm', 'asp', 'ats', 'avro', 'awk', 'bat', 'batch', 'bazel', 'bitbake', 'brotli', 'buildstream', 'bzip2', 'c', 'cabal', 'candid', 'carp', 'cbor', 'ceylon', 'clojure', 'cmake', 'cmd', 'cml', 'coffeescript', 'config', 'coq', 'cpp', 'creole', 'crystal', 'cs', 'csharp', 'cshtml', 'csproj', 'css', 'csv', 'cuda', 'cython', 'd', 'dart', 'devicetree', 'dhall', 'diff', 'dita', 'docker', 'dockercompose', 'dts', 'dvc', 'ebuild', 'edn', 'elisp', 'elixir', 'elm', 'erb', 'erlang', 'fennel', 'fidl', 'fish', 'flatbuffers', 'fortran', 'fsharp', 'fut', 'gap', 'gn', 'go', 'gprbuild', 'gradle', 'graphql', 'groovy', 'gzip', 'h', 'haml', 'hare', 'haskell', 'hbs', 'hs', 'html', 'hy', 'idris', 'janet', 'java', 'jinja', 'jl', 'js', 'json', 'jsonl', 'julia', 'jupyter', 'k', 'kotlin', 'lean', 'less', 'license', 'lilypond', 'lisp', 'lock', 'log', 'lua', 'lz4', 'lzma', 'm4', 'make', 'mako', 'man', 'markdown', 'matlab', 'md', 'meson', 'minified', 'mint', 'mk', 'ml', 'motoko', 'msbuild', 'nim', 'nix', 'objc', 'objcpp', 'ocaml', 'org', 'pants', 'pascal', 'pdf', 'perl', 'php', 'po', 'pod', 'postscript', 'prolog', 'protobuf', 'ps', 'puppet', 'purs', 'py', 'python', 'qmake', 'qml', 'r', 'racket', 'raku', 'rdoc', 'readme', 'reasonml', 'red', 'rescript', 'robot', 'rst', 'ruby', 'rust', 'sass', 'scala', 'sh', 'slim', 'smarty', 'sml', 'solidity', 'soy', 'spark', 'spec', 'sql', 'stylus', 'sv', 'svelte', 'svg', 'swift', 'swig', 'systemd', 'taskpaper', 'tcl', 'tex', 'texinfo', 'textile', 'tf', 'thrift', 'toml', 'ts', 'twig', 'txt', 'typescript', 'typoscript', 'usd', 'v', 'vala', 'vb', 'vcl', 'verilog', 'vhdl', 'vim', 'vimscript', 'vue', 'webidl', 'wgsl', 'wiki', 'xml', 'xz', 'yacc', 'yaml', 'yang', 'z', 'zig', 'zsh', 'zstd')",
                        },
                        "exclude_types": {
                            "anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}],
                            "default": None,
                            "description": "The types to exclude in the search. For example: 'python'. If not provided, common types are excluded by default (['avro', 'brotli', 'bzip2', 'cbor', 'flatbuffers', 'gzip', 'jupyter', 'lock', 'log', 'lz4', 'lzma', 'minified', 'pdf', 'postscript', 'protobuf', 'svg', 'thrift', 'usd', 'xz', 'zstd']).",
                        },
                        "max_results": {"default": 30, "description": "The maximum number of results to return.", "type": "integer"},
                    },
                    "required": IsList("owner", "patterns", "repo", check_order=False),
                },
            }
        ]
    )


async def test_code_search_mcp_client_code_search(code_search_mcp_client: Client[FastMCPTransport]) -> None:
    result: CallToolResult = await code_search_mcp_client.call_tool(
        "search_code",
        arguments={"owner": "strawgate", "repo": "github-issues-e2e-test", "patterns": ["world!"]},
    )

    assert result.structured_content == snapshot(
        {
            "result": [
                {
                    "url": "https://github.com/strawgate/github-issues-e2e-test/blob/main/README.md",
                    "matched_lines": [
                        {
                            "before": {"47": "```python", "48": "from gith_ub import ExistentialCoder", "50": "coder = ExistentialCoder()"},
                            "match": {"51": "coder.analyze_code(\"def hello_world(): print('Hello, World!')\")"},
                            "after": {
                                "52": "# Output: \"But what is 'Hello'? What is 'World'? Are we not all just strings in the cosmic interpreter?\"",
                                "53": "```",
                                "55": "## Philosophy",
                            },
                        },
                        {
                            "before": {
                                "70": "MIT License - because even in the digital realm, we must respect the cosmic copyright of existence.",
                                "72": "---",
                            },
                            "match": {
                                "74": "*\"In the beginning was the Word, and the Word was `console.log('Hello, World!')`\"* - The Gospel of G.I.T.H.U.B."
                            },
                            "after": {},
                        },
                    ],
                },
                {
                    "url": "https://github.com/strawgate/github-issues-e2e-test/blob/main/main.py",
                    "matched_lines": [
                        {
                            "before": {
                                "32": "    # Sample code to analyze",
                                "33": "    sample_code = '''",
                                "34": "def hello_world():",
                                "35": '    """A simple function that greets the world."""',
                            },
                            "match": {"36": '    print("Hello, World!")'},
                            "after": {
                                "37": '    return "greeting_complete"',
                                "39": 'if __name__ == "__main__":',
                                "40": "    result = hello_world()",
                            },
                        }
                    ],
                },
                {
                    "url": "https://github.com/strawgate/github-issues-e2e-test/blob/main/tests/test_existential_coder.py",
                    "matched_lines": [
                        {
                            "before": {
                                "27": "    def test_analyze_code_function(self):",
                                "28": '        """Test analysis of function definitions."""',
                                "29": "        coder = ExistentialCoder()",
                            },
                            "match": {"30": "        code = \"def hello_world():\\n    print('Hello, World!')\""},
                            "after": {"32": "        insights = coder.analyze_code(code)", "34": "        assert len(insights) > 0"},
                        }
                    ],
                },
            ]
        }
    )
