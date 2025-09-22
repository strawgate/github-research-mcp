import re
from typing import TYPE_CHECKING, Any

import pytest
from dirty_equals import IsDatetime, IsStr
from inline_snapshot import snapshot

from github_research_mcp.clients.github import (
    FindFilePathsResult,
    GitHubResearchClient,
    ResourceNotFoundError,
    SearchCodeResult,
    SearchIssuesResult,
    SearchPullRequestsResult,
)
from github_research_mcp.clients.models.github import (
    IssueOrPullRequestWithDetails,
    IssueWithDetails,
    PullRequestWithDetails,
    RepositoryFileWithLineMatches,
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
    from github_research_mcp.clients.models.github import Repository, RepositoryFileWithContent


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

        assert file is not None
        assert file.path == "README.md"
        assert file.content is not None

    async def test_get_file_on_ref(self, github_research_client: GitHubResearchClient, e2e_file_from_ref: E2ERepositoryFile):
        file: RepositoryFileWithContent | None = await github_research_client.get_file(
            owner=e2e_file_from_ref.owner,
            repo=e2e_file_from_ref.repo,
            path=e2e_file_from_ref.path,
            ref=e2e_file_from_ref.ref,
        )

        assert dump_for_snapshot(file) == snapshot(
            {"path": "test.md", "content": {1: "this is a test file", 2: "", 3: "this is a test modification", 4: ""}, "truncated": False}
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
        tree: FindFilePathsResult = await github_research_client.find_file_paths(
            owner=e2e_repository.owner,
            repo=e2e_repository.repo,
            include_patterns=[".md"],
            exclude_patterns=[".txt"],
            include_exclude_is_regex=False,
        )

        assert tree == snapshot(
            FindFilePathsResult(
                include_patterns=[".md"],
                exclude_patterns=[".txt"],
                include_exclude_is_regex=False,
                matching_file_paths=RepositoryTree(
                    directories=[
                        RepositoryTreeDirectory(path=".github", files=["PULL_REQUEST_TEMPLATE.md"]),
                        RepositoryTreeDirectory(
                            path=".github/ISSUE_TEMPLATE",
                            files=[
                                "bug_report.md",
                                "enlightenment_journey.md",
                                "feature_request.md",
                                "philosophical_question.md",
                            ],
                        ),
                    ],
                    files=["AGENTS.md", "CONTRIBUTING.md", "CONTRIBUTORS.md", "README.md"],
                    truncated=True,
                ),
            )
        )

    async def test_find_files_on_ref(self, github_research_client: GitHubResearchClient, e2e_file_from_ref: E2ERepositoryFile):
        tree: FindFilePathsResult = await github_research_client.find_file_paths(
            owner=e2e_file_from_ref.owner,
            repo=e2e_file_from_ref.repo,
            include_patterns=[".md"],
            exclude_patterns=[".txt"],
        )

        assert dump_for_snapshot(tree) == snapshot(
            {
                "include_patterns": [".md"],
                "exclude_patterns": [".txt"],
                "include_exclude_is_regex": False,
                "matching_file_paths": {
                    "directories": [
                        {"path": ".github", "files": ["PULL_REQUEST_TEMPLATE.md"]},
                        {
                            "path": ".github/ISSUE_TEMPLATE",
                            "files": [
                                "bug_report.md",
                                "enlightenment_journey.md",
                                "feature_request.md",
                                "philosophical_question.md",
                            ],
                        },
                    ],
                    "files": ["AGENTS.md", "CONTRIBUTING.md", "CONTRIBUTORS.md", "README.md"],
                    "truncated": True,
                },
            }
        )

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
        tree: FindFilePathsResult = await github_research_client.find_file_paths(
            owner=e2e_repository.owner,
            repo=e2e_repository.repo,
            include_patterns=[".none"],
        )

        assert dump_for_snapshot(tree) == snapshot(
            {
                "include_patterns": [".none"],
                "include_exclude_is_regex": False,
                "matching_file_paths": {"directories": [], "files": [], "truncated": True},
            }
        )


class TestSearchCode:
    async def test_search_code_by_one_keyword(self, github_research_client: GitHubResearchClient, e2e_repository: E2ERepository):
        results: SearchCodeResult = await github_research_client.search_code_by_keywords(
            owner=e2e_repository.owner,
            repo=e2e_repository.repo,
            keywords={"philosophy"},
        )

        assert len(results.matches) == 4

        assert results.code_search_query == snapshot('repo:strawgate/github-issues-e2e-test "philosophy"')

        assert results.matches == snapshot(
            [
                RepositoryFileWithLineMatches(
                    path="README.md",
                    matches=[
                        """\
# Output: "But what is 'Hello'? What is 'World'? Are we not all just strings in the cosmic interpreter?"
```

## Philosophy

G.I.T.H.U.B. is built on the principle that every line of code is a reflection of the human condition. We believe that:
"""
                    ],
                    keywords=["Philosophy"],
                ),
                RepositoryFileWithLineMatches(
                    path="src/utils.py",
                    matches=[
                        '''\
    return None


def generate_commit_philosophy(changes: List[str]) -> str:
    """
    Generate a philosophical reflection on the changes made.
    \
'''
                    ],
                    keywords=["philosophy"],
                ),
                RepositoryFileWithLineMatches(
                    path="src/oracle.py",
                    matches=[
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
                    keywords=["philosophy"],
                ),
                RepositoryFileWithLineMatches(
                    path=".github/ISSUE_TEMPLATE/philosophical_question.md",
                    matches=[
                        """\
name: Philosophical Question - The Digital Universe Seeks Understanding
about: Ask a deep philosophical question about code, programming, or existence
title: '[PHILOSOPHY] '
labels: 'philosophy, cosmic-question, wisdom-seeking'
assignees: ''

---\
"""
                    ],
                    keywords=["PHILOSOPHY", "philosophy"],
                ),
            ]
        )

    async def test_search_code_by_two_keywords(self, github_research_client: GitHubResearchClient, e2e_repository: E2ERepository):
        results: SearchCodeResult = await github_research_client.search_code_by_keywords(
            owner=e2e_repository.owner,
            repo=e2e_repository.repo,
            keywords={"philosophy", "enlightenment"},
        )

        assert len(results.matches) == 2

        assert results.code_search_query == snapshot('repo:strawgate/github-issues-e2e-test "enlightenment" "philosophy"')

        assert dump_list_for_snapshot(results.matches) == snapshot(
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
        search_issues_result: SearchIssuesResult = await github_research_client.search_issues(
            issue_search_query=issue_search_query,
        )
        assert dump_list_for_snapshot(search_issues_result.issues) == snapshot(
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
        search_issues_result: SearchIssuesResult = await github_research_client.search_issues_by_keywords(
            owner=e2e_issue.owner,
            repo=e2e_issue.repo,
            keywords={"philosophy"},
        )
        assert len(search_issues_result.issues) == 1
        assert dump_list_for_snapshot(search_issues_result.issues) == snapshot(
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
        search_pull_requests_result: SearchPullRequestsResult = await github_research_client.search_pull_requests(
            pull_request_search_query=pull_request_search_query,
        )
        assert dump_list_for_snapshot(search_pull_requests_result.pull_requests) == snapshot(
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
        search_pull_requests_result: SearchPullRequestsResult = await github_research_client.search_pull_requests_by_keywords(
            owner=e2e_pull_request.owner,
            repo=e2e_pull_request.repo,
            keywords={"description"},
        )
        assert len(search_pull_requests_result.pull_requests) == 1
        assert dump_list_for_snapshot(search_pull_requests_result.pull_requests) == snapshot(
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
