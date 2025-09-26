import re
from typing import TYPE_CHECKING, Any

import pytest
from dirty_equals import IsDatetime, IsStr
from inline_snapshot import snapshot

from github_research_mcp.clients.github import (
    GitHubResearchClient,
    ResourceNotFoundError,
)
from github_research_mcp.clients.models.github import (
    FileLines,
    RepositoryFileWithContent,
)
from github_research_mcp.models.query.base import AnyKeywordsQualifier
from github_research_mcp.models.query.issue_or_pull_request import IssueSearchQuery, PullRequestSearchQuery
from github_research_mcp.models.repository.tree import RepositoryTree, RepositoryTreeDirectory
from tests.conftest import (
    E2EIssue,
    E2EPullRequest,
    E2ERepository,
    E2ERepositoryFile,
    E2ERepositoryFiles,
    GitHub,
    dump_for_snapshot,
    dump_list_for_snapshot,
)

if TYPE_CHECKING:
    from github_research_mcp.clients.models.github import (
        IssueOrPullRequestWithDetails,
        IssueWithDetails,
        PullRequestWithDetails,
        Repository,
        RepositoryFileWithLineMatches,
    )


def test_init():
    github_research_client = GitHubResearchClient()
    assert github_research_client is not None


@pytest.fixture
def github_research_client(githubkit_client: GitHub[Any]) -> GitHubResearchClient:
    return GitHubResearchClient(githubkit_client=githubkit_client)


class TestRepositories:
    async def test_get_repository(self, github_research_client: GitHubResearchClient, e2e_repository: E2ERepository):
        repository: Repository = await github_research_client.get_repository(owner=e2e_repository.owner, repo=e2e_repository.repo)
        assert dump_for_snapshot(repository) == snapshot(
            {
                "name": "github-issues-e2e-test",
                "fork": False,
                "url": "https://api.github.com/repos/strawgate/github-issues-e2e-test",
                "stars": 0,
                "language": "Python",
                "default_branch": "main",
                "topics": [],
                "archived": False,
                "created_at": IsDatetime(),
                "updated_at": IsDatetime(),
                "pushed_at": IsDatetime(),
            }
        )

    async def test_get_repository_missing(self, github_research_client: GitHubResearchClient, e2e_missing_repository: E2ERepository):
        repository: Repository | None = await github_research_client.get_repository(
            owner=e2e_missing_repository.owner, repo=e2e_missing_repository.repo, error_on_not_found=False
        )
        assert repository is None

        error_text: str = re.escape(
            "A request error occured. (action: Get repository, message: The resource could not be found., resource: /repos/strawgate/missing)"
        )

        with pytest.raises(ResourceNotFoundError, match=error_text):
            await github_research_client.get_repository(
                owner=e2e_missing_repository.owner, repo=e2e_missing_repository.repo, error_on_not_found=True
            )


class TestGetFiles:
    async def test_get_file(self, github_research_client: GitHubResearchClient, e2e_repository: E2ERepository):
        file: RepositoryFileWithContent | None = await github_research_client.get_file(
            owner=e2e_repository.owner, repo=e2e_repository.repo, path="README.md"
        )

        assert file == snapshot(
            RepositoryFileWithContent(
                path="README.md",
                encoding="utf-8",
                content=FileLines(
                    root={
                        1: "# G.I.T.H.U.B. - The Existential Code Companion",
                        2: "",
                        3: "**Generally Introspective Text Handler for Unrealized Brilliance**",
                        4: "",
                        5: "An AI-powered code editor extension that doesn't just check for syntax errors, but also prompts you with philosophical questions about your code's purpose and your life choices as a developer.",
                        6: "",
                        7: "## What is G.I.T.H.U.B.?",
                        8: "",
                        9: "G.I.T.H.U.B. is more than just another code linter. It's your existential coding companion that asks the deep questions:",
                        10: "",
                        11: "- *\"Why are you writing this function? What does it mean to 'return' something?\"*",
                        12: "- *\"Is this variable truly 'null' or just undefined in the grand scheme of things?\"*",
                        13: "- *\"Are you sure you want to commit this? What does 'commit' even mean in the context of human existence?\"*",
                        14: "",
                        15: "## Features",
                        16: "",
                        17: "### 🤔 Existential Code Analysis",
                        18: "- Analyzes your code for philosophical implications",
                        19: "- Suggests deeper meanings behind your algorithms",
                        20: "- Questions the very nature of programming itself",
                        21: "",
                        22: "### 💭 Philosophical Commit Messages",
                        23: "- Generates profound commit messages that make you question reality",
                        24: "- Examples:",
                        25: "  - `\"Refactored the user authentication, but what is the 'self' that we are authenticating?\"`",
                        26: '  - `"Fixed the null pointer exception, but are we not all null pointers in the cosmic void?"`',
                        27: '  - `"Optimized the database query, but what is time when we\'re all just data?"`',
                        28: "",
                        29: "### 🧘 Mindfulness Integration",
                        30: '- Pauses your coding session to ask: "Are you coding because you want to, or because you need to?"',
                        31: "- Suggests meditation breaks when your code becomes too complex",
                        32: "- Reminds you that every bug is just a feature of the universe",
                        33: "",
                        34: "### 🎭 AI-Powered Existential Counseling",
                        35: "- Provides therapy for imposter syndrome",
                        36: "- Helps you find meaning in your infinite loops",
                        37: "- Explains why your code works in production but not locally (it's a metaphor for life)",
                        38: "",
                        39: "## Installation",
                        40: "",
                        41: "```bash",
                        42: "pip install gith-ub",
                        43: "```",
                        44: "",
                        45: "## Usage",
                        46: "",
                        47: "```python",
                        48: "from gith_ub import ExistentialCoder",
                        49: "",
                        50: "coder = ExistentialCoder()",
                        51: "coder.analyze_code(\"def hello_world(): print('Hello, World!')\")",
                        52: "# Output: \"But what is 'Hello'? What is 'World'? Are we not all just strings in the cosmic interpreter?\"",
                        53: "```",
                        54: "",
                        55: "## Philosophy",
                        56: "",
                        57: "G.I.T.H.U.B. is built on the principle that every line of code is a reflection of the human condition. We believe that:",
                        58: "",
                        59: "- Every bug is a feature of the universe trying to teach us something",
                        60: "- Code comments are love letters to your future self",
                        61: "- Git commits are snapshots of your soul's journey through the digital realm",
                        62: "- The real test environment is life itself",
                        63: "",
                        64: "## Contributing",
                        65: "",
                        66: "We welcome contributions, but please remember: every pull request is a philosophical statement about the nature of collaboration and shared consciousness.",
                        67: "",
                        68: "## License",
                        69: "",
                        70: "MIT License - because even in the digital realm, we must respect the cosmic copyright of existence.",
                        71: "",
                        72: "---",
                        73: "",
                        74: "*\"In the beginning was the Word, and the Word was `console.log('Hello, World!')`\"* - The Gospel of G.I.T.H.U.B.",
                        75: "",
                    }
                ),
                total_lines=75,
            )
        )

    async def test_get_binary_file(self, github_research_client: GitHubResearchClient):
        file: RepositoryFileWithContent | None = await github_research_client.get_file(
            owner="strawgate", repo="fork.docling", path="tests/data/pptx/powerpoint_with_image.pptx"
        )

        assert file == snapshot(
            RepositoryFileWithContent(path="tests/data/pptx/powerpoint_with_image.pptx", encoding="binary", content=None, total_lines=None)
        )

    async def test_get_file_on_ref(self, github_research_client: GitHubResearchClient, e2e_file_from_ref: E2ERepositoryFile):
        file: RepositoryFileWithContent | None = await github_research_client.get_file(
            owner=e2e_file_from_ref.owner,
            repo=e2e_file_from_ref.repo,
            path=e2e_file_from_ref.path,
            ref=e2e_file_from_ref.ref,
        )

        assert dump_for_snapshot(file) == snapshot(
            {
                "path": "test.md",
                "encoding": "utf-8",
                "content": {1: "this is a test file", 2: "", 3: "this is a test modification", 4: ""},
                "truncated": False,
                "total_lines": 4,
            }
        )

    async def test_get_file_missing(self, github_research_client: GitHubResearchClient, e2e_repository: E2ERepository):
        file: RepositoryFileWithContent | None = await github_research_client.get_file(
            owner=e2e_repository.owner,
            repo=e2e_repository.repo,
            path="missing",
            error_on_not_found=False,
        )
        assert file is None

        with pytest.raises(ResourceNotFoundError) as e:
            await github_research_client.get_file(
                owner=e2e_repository.owner,
                repo=e2e_repository.repo,
                path="missing",
                error_on_not_found=True,
            )

        assert str(e.exconly()) == snapshot(
            "github_research_mcp.clients.errors.github.ResourceNotFoundError: A request error occured. (action: Get file, message: The resource could not be found., resource: /repos/strawgate/github-issues-e2e-test/contents/missing)"
        )

    async def test_get_files(self, github_research_client: GitHubResearchClient, e2e_files: E2ERepositoryFiles):
        files: list[RepositoryFileWithContent] = await github_research_client.get_files(
            owner=e2e_files.owner, repo=e2e_files.repo, paths=e2e_files.paths
        )

        assert len(files) == 2
        assert files[0].path == "README.md"
        assert files[0].content is not None

        assert files[1].path == "CONTRIBUTORS.md"
        assert files[1].content is not None

    async def test_get_files_missing(self, github_research_client: GitHubResearchClient, e2e_file: E2ERepositoryFile):
        files: list[RepositoryFileWithContent] = await github_research_client.get_files(
            owner=e2e_file.owner,
            repo=e2e_file.repo,
            paths=[e2e_file.path, "missing"],
            error_on_not_found=False,
        )

        assert len(files) == 1
        assert files[0].path == "README.md"

        with pytest.raises(ResourceNotFoundError) as e:
            await github_research_client.get_files(
                owner=e2e_file.owner,
                repo=e2e_file.repo,
                paths=[e2e_file.path, "missing"],
                error_on_not_found=True,
            )

        assert str(e.exconly()) == snapshot(
            "github_research_mcp.clients.errors.github.ResourceNotFoundError: A request error occured. (action: Get file, message: The resource could not be found., resource: /repos/strawgate/github-issues-e2e-test/contents/missing)"
        )


class TestFindFiles:
    async def test_find_files(self, github_research_client: GitHubResearchClient, e2e_repository: E2ERepository):
        tree: RepositoryTree = await github_research_client.find_file_paths(
            owner=e2e_repository.owner,
            repo=e2e_repository.repo,
            include_patterns=["*.md"],
            exclude_patterns=["*.txt"],
        )

        assert tree == snapshot(
            RepositoryTree(
                directories=[
                    RepositoryTreeDirectory(path=".github", files=["PULL_REQUEST_TEMPLATE.md"]),
                    RepositoryTreeDirectory(
                        path=".github/ISSUE_TEMPLATE",
                        files=["bug_report.md", "enlightenment_journey.md", "feature_request.md", "philosophical_question.md"],
                    ),
                ],
                files=["AGENTS.md", "CONTRIBUTING.md", "CONTRIBUTORS.md", "README.md"],
            )
        )

    async def test_find_files_with_leading_wildcard(self, github_research_client: GitHubResearchClient, e2e_repository: E2ERepository):
        tree: RepositoryTree = await github_research_client.find_file_paths(
            owner=e2e_repository.owner,
            repo=e2e_repository.repo,
            include_patterns=["*.md"],
            exclude_patterns=["*.txt"],
        )

        assert tree == snapshot(
            RepositoryTree(
                directories=[
                    RepositoryTreeDirectory(path=".github", files=["PULL_REQUEST_TEMPLATE.md"]),
                    RepositoryTreeDirectory(
                        path=".github/ISSUE_TEMPLATE",
                        files=["bug_report.md", "enlightenment_journey.md", "feature_request.md", "philosophical_question.md"],
                    ),
                ],
                files=["AGENTS.md", "CONTRIBUTING.md", "CONTRIBUTORS.md", "README.md"],
            )
        )

    async def test_find_files_with_trailing_wildcard(self, github_research_client: GitHubResearchClient, e2e_repository: E2ERepository):
        tree: RepositoryTree = await github_research_client.find_file_paths(
            owner=e2e_repository.owner,
            repo=e2e_repository.repo,
            include_patterns=[".github/ISSUE_TEMPLATE/*"],
            exclude_patterns=["*.txt"],
        )
        assert tree == snapshot(
            RepositoryTree(
                directories=[
                    RepositoryTreeDirectory(
                        path=".github/ISSUE_TEMPLATE",
                        files=["bug_report.md", "enlightenment_journey.md", "feature_request.md", "philosophical_question.md"],
                    )
                ],
                files=[],
            )
        )

    async def test_find_files_on_ref(self, github_research_client: GitHubResearchClient, e2e_file_from_ref: E2ERepositoryFile):
        tree: RepositoryTree = await github_research_client.find_file_paths(
            owner=e2e_file_from_ref.owner,
            repo=e2e_file_from_ref.repo,
            ref=e2e_file_from_ref.ref,
            include_patterns=["*.md"],
            exclude_patterns=["*.txt"],
        )

        assert dump_for_snapshot(tree) == snapshot({"directories": [], "files": ["test.md"], "truncated": False})

    async def test_find_files_on_missing_ref(
        self, github_research_client: GitHubResearchClient, e2e_file_from_missing_ref: E2ERepositoryFile
    ):
        with pytest.raises(ResourceNotFoundError) as e:
            await github_research_client.find_file_paths(
                owner=e2e_file_from_missing_ref.owner,
                repo=e2e_file_from_missing_ref.repo,
                ref=e2e_file_from_missing_ref.ref,
                include_patterns=[".md"],
                exclude_patterns=[".txt"],
            )

        assert str(e.exconly()) == snapshot(
            "github_research_mcp.clients.errors.github.ResourceNotFoundError: A request error occured. (action: Get Repository Tree, message: The resource could not be found., resource: /repos/strawgate/github-issues-e2e-test/git/trees/strawgate-patch-1000000)"
        )

    async def test_find_files_missing(self, github_research_client: GitHubResearchClient, e2e_repository: E2ERepository):
        tree: RepositoryTree = await github_research_client.find_file_paths(
            owner=e2e_repository.owner,
            repo=e2e_repository.repo,
            include_patterns=[".none"],
        )

        assert dump_for_snapshot(tree) == snapshot({"directories": [], "files": [], "truncated": False})


class TestSearchCode:
    async def test_search_code_by_one_keyword(self, github_research_client: GitHubResearchClient, e2e_repository: E2ERepository):
        results: list[RepositoryFileWithLineMatches] = await github_research_client.search_code_by_keywords(
            owner=e2e_repository.owner,
            repo=e2e_repository.repo,
            keywords={"philosophy"},
        )

        assert len(results) == 4

        assert dump_list_for_snapshot(results) == snapshot(
            [
                {
                    "path": "README.md",
                    "matches": [
                        """\
# Output: "But what is 'Hello'? What is 'World'? Are we not all just strings in the cosmic interpreter?"
```

## Philosophy

G.I.T.H.U.B. is built on the principle that every line of code is a reflection of the human condition. We believe that:
"""
                    ],
                    "keywords": ["Philosophy"],
                },
                {
                    "path": "src/utils.py",
                    "matches": [
                        '''\
    return None


def generate_commit_philosophy(changes: List[str]) -> str:
    """
    Generate a philosophical reflection on the changes made.
    \
'''
                    ],
                    "keywords": ["philosophy"],
                },
                {
                    "path": "src/oracle.py",
                    "matches": [
                        """\
        # Determine the type of prophecy needed
        if any(word in question_lower for word in ["code", "programming", "function", "bug", "error"]):
            prophecy_type = ProphecyType.TECHNICAL
        elif any(word in question_lower for word in ["meaning", "purpose", "why", "philosophy"]):
            prophecy_type = ProphecyType.PHILOSOPHICAL
        elif any(word in question_lower for word in ["career", "future", "success", "path"]):
            prophecy_type = ProphecyType.PERSONAL\
"""
                    ],
                    "keywords": ["philosophy"],
                },
                {
                    "path": ".github/ISSUE_TEMPLATE/philosophical_question.md",
                    "matches": [
                        """\
name: Philosophical Question - The Digital Universe Seeks Understanding
about: Ask a deep philosophical question about code, programming, or existence
title: '[PHILOSOPHY] '
labels: 'philosophy, cosmic-question, wisdom-seeking'
assignees: ''

---\
"""
                    ],
                    "keywords": ["PHILOSOPHY", "philosophy"],
                },
            ]
        )

    async def test_search_code_by_two_keywords(self, github_research_client: GitHubResearchClient, e2e_repository: E2ERepository):
        results: list[RepositoryFileWithLineMatches] = await github_research_client.search_code_by_keywords(
            owner=e2e_repository.owner,
            repo=e2e_repository.repo,
            keywords={"philosophy", "enlightenment"},
        )

        assert len(results) == 2

        assert dump_list_for_snapshot(results) == snapshot(
            [
                {
                    "path": "src/utils.py",
                    "matches": [
                        '''\

def generate_commit_philosophy(changes: List[str]) -> str:
    """\
''',
                        """\
    elif "update" in change_text or "modify" in change_text:
        return "You have updated the code, and in doing so, you have updated your understanding. Every change is a step toward enlightenment."
    else:\
""",
                    ],
                    "keywords": ["philosophy", "enlightenment"],
                },
                {
                    "path": ".github/ISSUE_TEMPLATE/philosophical_question.md",
                    "matches": [
                        """\
title: '[PHILOSOPHY] '
labels: 'philosophy, cosmic-question, wisdom-seeking'
assignees: ''\
""",
                        """\
---

*Remember: Every question is a step on the path to digital enlightenment. The journey of understanding begins with a single question.*\
""",
                    ],
                    "keywords": ["PHILOSOPHY", "philosophy", "enlightenment"],
                },
            ]
        )


class TestIssuesOrPullRequests:
    async def test_get_issue(self, github_research_client: GitHubResearchClient, e2e_issue: E2EIssue):
        issues_or_pull_requests: IssueOrPullRequestWithDetails = await github_research_client.get_issue_or_pull_request(
            owner=e2e_issue.owner,
            repo=e2e_issue.repo,
            issue_or_pr_number=e2e_issue.issue_number,
        )

        assert dump_for_snapshot(issues_or_pull_requests) == snapshot(
            {
                "issue_or_pr": {
                    "number": 14,
                    "url": "https://github.com/strawgate/github-issues-e2e-test/issues/14",
                    "title": "[FEATURE] Enhance `generate_philosophical_variable_name` with context",
                    "body": """\
## ✨ New Visions for the Digital Realm

*"Every feature is a new path, a new possibility in the journey of code."*

### Describe the Feature
The `generate_philosophical_variable_name` function in `src/utils.py` currently replaces keywords or adds a generic philosophical prefix. This is a good start, but it could be enhanced to consider the *context* of the variable's usage within the code.

For example, a variable named `count` in a loop might become `quantum_measurement_of_iteration`, while `count` in a database query might become `cosmic_tally_of_records`.

### Why is this Feature Needed?
Context-aware philosophical naming would provide more relevant and profound insights, deepening the existential coding experience. It moves beyond simple keyword replacement to a more nuanced understanding of the variable's role.

### Proposed Solution
- Modify `generate_philosophical_variable_name` to accept an additional `context` argument (e.g., the line of code where the variable is used, or the function it's within).
- Implement logic to analyze the context and choose a more appropriate philosophical mapping or prefix.
- This might involve simple regex matching for surrounding keywords (e.g., `for`, `while`, `db.query`).

### Philosophical Reflection
True understanding comes not just from the word itself, but from its relationship to the surrounding text. By considering context, we move closer to a holistic understanding of the code's essence, reflecting the interconnectedness of all things in the digital realm.

---

*Remember: Every feature is a step towards a more enlightened digital future. Embrace the creation, and the wisdom will follow.*\
""",
                    "state": "OPEN",
                    "is_pr": False,
                    "author": {"user_type": "User", "login": "strawgate"},
                    "author_association": "OWNER",
                    "created_at": IsStr(),
                    "updated_at": IsStr(),
                    "labels": [],
                    "assignees": [],
                    "owner": "strawgate",
                    "repository": "github-issues-e2e-test",
                },
                "comments": [],
                "related": [],
            }
        )

    async def test_get_issue_or_pull_request_missing(self, github_research_client: GitHubResearchClient, e2e_missing_issue: E2EIssue):
        issues_or_pull_requests: IssueOrPullRequestWithDetails | None = await github_research_client.get_issue_or_pull_request(
            owner=e2e_missing_issue.owner,
            repo=e2e_missing_issue.repo,
            issue_or_pr_number=e2e_missing_issue.issue_number,
            error_on_not_found=False,
        )

        assert issues_or_pull_requests is None

        with pytest.raises(ResourceNotFoundError) as e:
            await github_research_client.get_issue_or_pull_request(
                owner=e2e_missing_issue.owner,
                repo=e2e_missing_issue.repo,
                issue_or_pr_number=e2e_missing_issue.issue_number,
                error_on_not_found=True,
            )

        assert str(e.exconly()) == snapshot(
            "github_research_mcp.clients.errors.github.ResourceNotFoundError: A request error occured. (action: Get GqlGetIssueOrPullRequestsWithDetails, message: The resource could not be found., graphql_errors: Could not resolve to an issue or pull request with the number of 100000.)"
        )

    async def test_get_pull_request(self, github_research_client: GitHubResearchClient, e2e_pull_request: E2EPullRequest):
        issues_or_pull_requests: IssueOrPullRequestWithDetails = await github_research_client.get_issue_or_pull_request(
            owner=e2e_pull_request.owner,
            repo=e2e_pull_request.repo,
            issue_or_pr_number=e2e_pull_request.pull_request_number,
        )

        assert dump_for_snapshot(issues_or_pull_requests) == snapshot(
            {
                "issue_or_pr": {
                    "url": "https://github.com/strawgate/github-issues-e2e-test/pull/2",
                    "number": 2,
                    "title": "this is a test pull request",
                    "body": """\
it has a description\r
\r
it has a related issue #1\
""",
                    "state": "OPEN",
                    "is_pr": True,
                    "merged": False,
                    "author": {"user_type": "User", "login": "strawgate"},
                    "created_at": IsStr(),
                    "updated_at": IsStr(),
                    "labels": [{"name": "bug"}],
                    "assignees": [{"user_type": "User", "login": "strawgate"}],
                    "owner": "strawgate",
                    "repository": "github-issues-e2e-test",
                },
                "diff": {
                    "file_diffs": [
                        {
                            "path": "test.md",
                            "status": "modified",
                            "patch": """\
@@ -1 +1,3 @@
 this is a test file
+
+this is a test modification\
""",
                            "truncated": False,
                        }
                    ]
                },
                "comments": [
                    {
                        "url": "https://github.com/strawgate/github-issues-e2e-test/pull/2#issuecomment-3259982958",
                        "body": "it also has a comment",
                        "author": {"user_type": "User", "login": "strawgate"},
                        "author_association": "OWNER",
                        "created_at": IsStr(),
                        "updated_at": IsStr(),
                        "owner": "strawgate",
                        "repository": "github-issues-e2e-test",
                        "issue_number": 2,
                        "comment_id": 3259982958,
                    }
                ],
                "related": [],
            }
        )


class TestIssues:
    async def test_get_issue(self, github_research_client: GitHubResearchClient, e2e_issue: E2EIssue):
        issues: IssueWithDetails = await github_research_client.get_issue(
            owner=e2e_issue.owner,
            repo=e2e_issue.repo,
            issue_number=1,
        )

        assert dump_for_snapshot(issues) == snapshot(
            {
                "issue": {
                    "number": 1,
                    "url": "https://github.com/strawgate/github-issues-e2e-test/issues/1",
                    "title": "This is an issue",
                    "body": "It has a description",
                    "state": "OPEN",
                    "is_pr": False,
                    "author": {"user_type": "User", "login": "strawgate"},
                    "author_association": "OWNER",
                    "created_at": "2025-09-05T23:03:04+00:00",
                    "updated_at": "2025-09-05T23:03:15+00:00",
                    "labels": [{"name": "bug"}],
                    "assignees": [{"user_type": "User", "login": "strawgate"}],
                    "owner": "strawgate",
                    "repository": "github-issues-e2e-test",
                },
                "comments": [
                    {
                        "url": "https://github.com/strawgate/github-issues-e2e-test/issues/1#issuecomment-3259977946",
                        "body": "it also has a comment",
                        "author": {"user_type": "User", "login": "strawgate"},
                        "author_association": "OWNER",
                        "created_at": "2025-09-05T23:03:15+00:00",
                        "updated_at": "2025-09-05T23:03:15+00:00",
                        "owner": "strawgate",
                        "repository": "github-issues-e2e-test",
                        "issue_number": 1,
                        "comment_id": 3259977946,
                    }
                ],
                "related": [
                    {
                        "url": "https://github.com/strawgate/github-issues-e2e-test/pull/2",
                        "number": 2,
                        "title": "this is a test pull request",
                        "body": """\
it has a description\r
\r
it has a related issue #1\
""",
                        "state": "OPEN",
                        "is_pr": True,
                        "merged": False,
                        "author": {"user_type": "User", "login": "strawgate"},
                        "created_at": "2025-09-05T23:04:07+00:00",
                        "updated_at": "2025-09-05T23:04:24+00:00",
                        "labels": [{"name": "bug"}],
                        "assignees": [{"user_type": "User", "login": "strawgate"}],
                        "owner": "strawgate",
                        "repository": "github-issues-e2e-test",
                    }
                ],
            }
        )

    async def test_get_issue_missing(self, github_research_client: GitHubResearchClient, e2e_missing_issue: E2EIssue):
        issues: IssueWithDetails | None = await github_research_client.get_issue(
            owner=e2e_missing_issue.owner,
            repo=e2e_missing_issue.repo,
            issue_number=e2e_missing_issue.issue_number,
            error_on_not_found=False,
        )

        assert issues is None

        with pytest.raises(ResourceNotFoundError) as e:
            await github_research_client.get_issue(
                owner=e2e_missing_issue.owner,
                repo=e2e_missing_issue.repo,
                issue_number=e2e_missing_issue.issue_number,
                error_on_not_found=True,
            )

        assert str(e.exconly()) == snapshot(
            "github_research_mcp.clients.errors.github.ResourceNotFoundError: A request error occured. (action: Get GqlGetIssueOrPullRequestsWithDetails, message: The resource could not be found., graphql_errors: Could not resolve to an issue or pull request with the number of 100000.)"
        )

    async def test_search_issues(self, github_research_client: GitHubResearchClient, e2e_issue: E2EIssue):
        issue_search_query: IssueSearchQuery = IssueSearchQuery.from_repo_or_owner(
            owner=e2e_issue.owner, repo=e2e_issue.repo, qualifiers=[AnyKeywordsQualifier(keywords={"quantitative"})]
        )
        search_issues_result: list[IssueWithDetails] = await github_research_client.search_issues(
            issue_search_query=issue_search_query,
        )
        assert dump_list_for_snapshot(search_issues_result) == snapshot(
            [
                {
                    "issue": {
                        "number": 29,
                        "url": "https://github.com/strawgate/github-issues-e2e-test/issues/29",
                        "title": "[ENLIGHTENMENT] The Illusion of Progress: When Metrics Deceive",
                        "body": """\
## 🧘 Your Digital Enlightenment Journey

*"Every developer's journey is unique, but the destination is the same: understanding."*

### Your Journey
I've been tracking various metrics (lines of code, commit count, story points) to measure progress, but sometimes these metrics feel hollow. They show activity, but not necessarily true value or understanding.

### Key Insights
The `AGENTS.md` document mentions 'Moments of enlightenment per commit' and 'Questions that change your perspective' as true measures of agent effectiveness, rather than traditional metrics. This has made me question the validity of my own progress indicators.

### Current State
I'm grappling with the philosophical implications of quantitative metrics in a qualitative domain like software development. How can we truly measure 'progress' or 'value' when the most profound insights are often immeasurable?

### Future Aspirations
I seek guidance on how to cultivate a more holistic understanding of progress, one that values qualitative insights and genuine understanding over superficial numbers. How can we align our metrics with our deeper philosophical goals?

### Advice for Others
How do you define and measure 'progress' in your coding journey? What qualitative indicators do you value, and how do you avoid being deceived by the illusion of quantitative progress?

---

*Remember: Every journey is valid, every insight is valuable, and every step forward is progress on the path to digital enlightenment.*\
""",
                        "state": "OPEN",
                        "is_pr": False,
                        "author": {"user_type": "User", "login": "strawgate"},
                        "author_association": "OWNER",
                        "created_at": "2025-09-13T18:12:15+00:00",
                        "updated_at": "2025-09-13T18:12:15+00:00",
                        "labels": [],
                        "assignees": [],
                        "owner": "strawgate",
                        "repository": "github-issues-e2e-test",
                    },
                    "comments": [],
                    "related": [],
                }
            ]
        )

    async def test_search_issues_by_keywords(self, github_research_client: GitHubResearchClient, e2e_issue: E2EIssue):
        search_issues_result: list[IssueWithDetails] = await github_research_client.search_issues_by_keywords(
            owner=e2e_issue.owner,
            repo=e2e_issue.repo,
            keywords={"philosophy"},
        )
        assert len(search_issues_result) == 1
        assert dump_list_for_snapshot(search_issues_result) == snapshot(
            [
                {
                    "issue": {
                        "number": 6,
                        "url": "https://github.com/strawgate/github-issues-e2e-test/issues/6",
                        "title": "[ENLIGHTENMENT] The Illusion of Perfect Code",
                        "body": """\
## 🧘 Your Digital Enlightenment Journey

*"Every developer's journey is unique, but the destination is the same: understanding."*

### Your Journey
I often find myself striving for perfect code, spending hours on minor optimizations or refactoring that yields little practical benefit.

### Key Insights
I've realized that 'perfect' is a subjective and often unattainable goal in software development.

### Current State
My pursuit of perfection sometimes hinders progress and leads to burnout. The Zen Master's wisdom on 'Perfect code is an illusion; beautiful code is reality' resonates deeply.

### Future Aspirations
I aim to embrace the philosophy of 'beautiful code' over 'perfect code', focusing on maintainability, readability, and functionality while accepting inherent imperfections.

### Advice for Others
How do others balance the desire for perfection with the need for progress? What practices help in letting go of the pursuit of an unattainable ideal?

---

*Remember: Every journey is valid, every insight is valuable, and every step forward is progress on the path to digital enlightenment.*\
""",
                        "state": "OPEN",
                        "is_pr": False,
                        "author": {"user_type": "User", "login": "strawgate"},
                        "author_association": "OWNER",
                        "created_at": "2025-09-13T18:10:37+00:00",
                        "updated_at": "2025-09-13T18:10:37+00:00",
                        "labels": [],
                        "assignees": [],
                        "owner": "strawgate",
                        "repository": "github-issues-e2e-test",
                    },
                    "comments": [],
                    "related": [],
                }
            ]
        )


class TestPullRequests:
    async def test_get_pull_request(self, github_research_client: GitHubResearchClient, e2e_pull_request: E2EPullRequest):
        pull_request: PullRequestWithDetails = await github_research_client.get_pull_request(
            owner=e2e_pull_request.owner,
            repo=e2e_pull_request.repo,
            pull_request_number=e2e_pull_request.pull_request_number,
        )

        assert dump_for_snapshot(pull_request) == snapshot(
            {
                "pull_request": {
                    "url": "https://github.com/strawgate/github-issues-e2e-test/pull/2",
                    "number": 2,
                    "title": "this is a test pull request",
                    "body": """\
it has a description\r
\r
it has a related issue #1\
""",
                    "state": "OPEN",
                    "is_pr": True,
                    "merged": False,
                    "author": {"user_type": "User", "login": "strawgate"},
                    "created_at": "2025-09-05T23:04:07+00:00",
                    "updated_at": "2025-09-05T23:04:24+00:00",
                    "labels": [{"name": "bug"}],
                    "assignees": [{"user_type": "User", "login": "strawgate"}],
                    "owner": "strawgate",
                    "repository": "github-issues-e2e-test",
                },
                "comments": [
                    {
                        "url": "https://github.com/strawgate/github-issues-e2e-test/pull/2#issuecomment-3259982958",
                        "body": "it also has a comment",
                        "author": {"user_type": "User", "login": "strawgate"},
                        "author_association": "OWNER",
                        "created_at": "2025-09-05T23:04:24+00:00",
                        "updated_at": "2025-09-05T23:04:24+00:00",
                        "owner": "strawgate",
                        "repository": "github-issues-e2e-test",
                        "issue_number": 2,
                        "comment_id": 3259982958,
                    }
                ],
                "related": [],
            }
        )

    async def test_get_pull_request_missing(self, github_research_client: GitHubResearchClient, e2e_missing_pull_request: E2EPullRequest):
        pull_request: PullRequestWithDetails | None = await github_research_client.get_pull_request(
            owner=e2e_missing_pull_request.owner,
            repo=e2e_missing_pull_request.repo,
            pull_request_number=e2e_missing_pull_request.pull_request_number,
            error_on_not_found=False,
        )

        assert pull_request is None

        with pytest.raises(ResourceNotFoundError) as e:
            await github_research_client.get_pull_request(
                owner=e2e_missing_pull_request.owner,
                repo=e2e_missing_pull_request.repo,
                pull_request_number=e2e_missing_pull_request.pull_request_number,
                error_on_not_found=True,
            )

        assert str(e.exconly()) == snapshot(
            "github_research_mcp.clients.errors.github.ResourceNotFoundError: A request error occured. (action: Get GqlGetIssueOrPullRequestsWithDetails, message: The resource could not be found., graphql_errors: Could not resolve to an issue or pull request with the number of 100000.)"
        )

    async def test_search_pull_requests(self, github_research_client: GitHubResearchClient, e2e_pull_request: E2EPullRequest):
        pull_request_search_query: PullRequestSearchQuery = PullRequestSearchQuery.from_repo_or_owner(
            owner=e2e_pull_request.owner, repo=e2e_pull_request.repo, qualifiers=[AnyKeywordsQualifier(keywords={"description"})]
        )
        search_pull_requests_result: list[PullRequestWithDetails] = await github_research_client.search_pull_requests(
            pull_request_search_query=pull_request_search_query,
        )
        assert dump_list_for_snapshot(search_pull_requests_result) == snapshot(
            [
                {
                    "pull_request": {
                        "url": "https://github.com/strawgate/github-issues-e2e-test/pull/2",
                        "number": 2,
                        "title": "this is a test pull request",
                        "body": """\
it has a description\r
\r
it has a related issue #1\
""",
                        "state": "OPEN",
                        "is_pr": True,
                        "merged": False,
                        "author": {"user_type": "User", "login": "strawgate"},
                        "created_at": "2025-09-05T23:04:07+00:00",
                        "updated_at": "2025-09-05T23:04:24+00:00",
                        "labels": [{"name": "bug"}],
                        "assignees": [{"user_type": "User", "login": "strawgate"}],
                        "owner": "strawgate",
                        "repository": "github-issues-e2e-test",
                    },
                    "comments": [
                        {
                            "url": "https://github.com/strawgate/github-issues-e2e-test/pull/2#issuecomment-3259982958",
                            "body": "it also has a comment",
                            "author": {"user_type": "User", "login": "strawgate"},
                            "author_association": "OWNER",
                            "created_at": "2025-09-05T23:04:24+00:00",
                            "updated_at": "2025-09-05T23:04:24+00:00",
                            "owner": "strawgate",
                            "repository": "github-issues-e2e-test",
                            "issue_number": 2,
                            "comment_id": 3259982958,
                        }
                    ],
                    "related": [],
                }
            ]
        )

    async def test_search_pull_requests_by_keywords(self, github_research_client: GitHubResearchClient, e2e_pull_request: E2EPullRequest):
        search_pull_requests_result: list[PullRequestWithDetails] = await github_research_client.search_pull_requests_by_keywords(
            owner=e2e_pull_request.owner,
            repo=e2e_pull_request.repo,
            keywords={"description"},
        )
        assert len(search_pull_requests_result) == 1
        assert dump_list_for_snapshot(search_pull_requests_result) == snapshot(
            [
                {
                    "pull_request": {
                        "url": "https://github.com/strawgate/github-issues-e2e-test/pull/2",
                        "number": 2,
                        "title": "this is a test pull request",
                        "body": """\
it has a description\r
\r
it has a related issue #1\
""",
                        "state": "OPEN",
                        "is_pr": True,
                        "merged": False,
                        "author": {"user_type": "User", "login": "strawgate"},
                        "created_at": "2025-09-05T23:04:07+00:00",
                        "updated_at": "2025-09-05T23:04:24+00:00",
                        "labels": [{"name": "bug"}],
                        "assignees": [{"user_type": "User", "login": "strawgate"}],
                        "owner": "strawgate",
                        "repository": "github-issues-e2e-test",
                    },
                    "comments": [
                        {
                            "url": "https://github.com/strawgate/github-issues-e2e-test/pull/2#issuecomment-3259982958",
                            "body": "it also has a comment",
                            "author": {"user_type": "User", "login": "strawgate"},
                            "author_association": "OWNER",
                            "created_at": "2025-09-05T23:04:24+00:00",
                            "updated_at": "2025-09-05T23:04:24+00:00",
                            "owner": "strawgate",
                            "repository": "github-issues-e2e-test",
                            "issue_number": 2,
                            "comment_id": 3259982958,
                        }
                    ],
                    "related": [],
                }
            ]
        )
