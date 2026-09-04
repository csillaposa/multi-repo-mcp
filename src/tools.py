from mcp.server import MCPServer

from .files import read_file_data, read_file_range_data
from .jira import (
    get_jira_issue_comments_data,
    get_jira_issue_data,
    search_jira_data,
)
from .git import (
    compare_branches_data,
    get_commit_history_data,
    get_file_diff_data,
    get_git_status_data,
    get_project_status_data,
    get_working_tree_diff_summary_data,
    list_branches_data,
    list_changed_files_data,
    show_commit_data,
)
from .repositories import list_repositories_data
from .search import search_code_data
from .verification import (
    get_verification_config_data,
    run_verification_data,
)


def register_tools(mcp: MCPServer) -> None:
    """Register all project MCP tools on the supplied server."""

    @mcp.tool()
    def list_repositories() -> dict[str, dict[str, str | bool]]:
        """
        List all enabled repositories configured for this MCP project.

        Returns each repository's resolved path and whether it exists
        and appears to be a Git repository.
        """
        return list_repositories_data()

    @mcp.tool()
    def search_code(
        query: str,
        repository: str | None = None,
        max_matches: int = 200,
    ) -> dict[str, object]:
        """
        Search for literal text across one or all enabled repositories.

        Args:
            query: Literal text to search for.
            repository: Optional configured repository name. If omitted,
                search all enabled repositories.
            max_matches: Maximum total matches to return across repositories.
        """
        return search_code_data(
            query=query,
            repository=repository,
            max_matches=max_matches,
        )

    @mcp.tool()
    def read_file(
        repository: str,
        path: str,
    ) -> str:
        """
        Read a UTF-8 text file from a configured repository.

        Args:
            repository: Configured repository name.
            path: File path relative to the repository root.
        """
        return read_file_data(
            repository=repository,
            path=path,
        )

    @mcp.tool()
    def read_file_range(
        repository: str,
        path: str,
        start_line: int,
        end_line: int,
    ) -> dict[str, object]:
        """
        Read a specific 1-based inclusive line range from a text file.

        Use this instead of read_file when only part of a large file is needed.

        Args:
            repository: Configured repository name.
            path: File path relative to the repository root.
            start_line: First line to return, starting at 1.
            end_line: Last line to return, inclusive.
        """
        return read_file_range_data(
            repository=repository,
            path=path,
            start_line=start_line,
            end_line=end_line,
        )

    @mcp.tool()
    def get_git_status(
        repository: str,
    ) -> dict[str, str]:
        """
        Return the current branch and working-tree status for a repository.

        This is read-only and does not fetch, checkout, or modify Git state.
        """
        return get_git_status_data(repository)

    @mcp.tool()
    def list_changed_files(
        repository: str,
    ) -> dict[str, object]:
        """
        List staged, unstaged, and untracked files in a repository.

        Prefer this before requesting detailed diffs.
        """
        return list_changed_files_data(repository)

    @mcp.tool()
    def list_branches(
        repository: str,
    ) -> dict[str, object]:
        """
        List local and locally known remote-tracking branches.

        This does not run git fetch, so remote branch information may be stale.
        """
        return list_branches_data(repository)

    @mcp.tool()
    def compare_branches(
        repository: str,
        base: str,
        head: str,
    ) -> dict[str, object]:
        """
        Compare two Git refs or branches.

        Returns commits present in head but not base, changed files,
        and a diff-stat summary.

        Args:
            repository: Configured repository name.
            base: Base branch or Git ref.
            head: Head branch or Git ref.
        """
        return compare_branches_data(
            repository=repository,
            base=base,
            head=head,
        )

    @mcp.tool()
    def get_commit_history(
        repository: str,
        branch: str | None = None,
        limit: int = 20,
    ) -> dict[str, object]:
        """
        Return recent commit metadata for a repository or branch.

        Args:
            repository: Configured repository name.
            branch: Optional branch or Git ref. Uses current HEAD if omitted.
            limit: Number of commits to return, from 1 to 100.
        """
        return get_commit_history_data(
            repository=repository,
            branch=branch,
            limit=limit,
        )

    @mcp.tool()
    def show_commit(
        repository: str,
        commit: str,
    ) -> dict[str, object]:
        """
        Show metadata, changed files, and diff statistics for one Git commit.

        This intentionally does not return the full patch.

        Args:
            repository: Configured repository name.
            commit: Commit hash or other Git revision.
        """
        return show_commit_data(
            repository=repository,
            commit=commit,
        )

    @mcp.tool()
    def get_working_tree_diff_summary(
        repository: str,
    ) -> dict[str, object]:
        """
        Return staged and unstaged diff-stat summaries for a repository.

        Use list_changed_files and get_file_diff for detailed inspection.
        """
        return get_working_tree_diff_summary_data(repository)

    @mcp.tool()
    def get_file_diff(
        repository: str,
        path: str,
        max_lines: int = 300,
    ) -> dict[str, object]:
        """
        Return bounded staged and unstaged diffs for one file.

        Args:
            repository: Configured repository name.
            path: File path relative to the repository root.
            max_lines: Maximum number of diff lines returned per section.
        """
        return get_file_diff_data(
            repository=repository,
            path=path,
            max_lines=max_lines,
        )

    @mcp.tool()
    def get_project_status() -> dict[str, object]:
        """
        Return a Git status summary across all enabled repositories.

        Includes current branch, dirty state, locally known upstream,
        ahead/behind counts, changed files, and latest commit.

        Ahead/behind values use local remote-tracking refs and do not
        prove the current state of the remote server.
        """
        return get_project_status_data()

    @mcp.tool()
    def get_verification_config(
        repository: str,
    ) -> dict[str, object]:
        """
        Show the allow-listed verification checks configured for a repository.

        This does not execute any command.
        """
        return get_verification_config_data(repository)

    @mcp.tool()
    def run_verification(
        repository: str,
        check: str,
        timeout_seconds: int = 120,
    ) -> dict[str, object]:
        """
        Run one preconfigured verification check for a repository.

        Only commands explicitly allow-listed in repositories.yaml can run.
        Arbitrary shell commands are not accepted.

        Args:
            repository: Configured repository name.
            check: Configured check name such as tests, lint, or typecheck.
            timeout_seconds: Maximum runtime, from 1 to 600 seconds.
        """
        return run_verification_data(
            repository=repository,
            check=check,
            timeout_seconds=timeout_seconds,
        )

    @mcp.tool()
    def get_jira_issue(
        issue_key: str,
    ) -> dict[str, object]:
        """
        Fetch one Jira issue by key or ID.

        Args:
            issue_key: Jira issue key such as MA-2161.
        """
        return get_jira_issue_data(issue_key)

    @mcp.tool()
    def search_jira(
        jql: str,
        max_results: int = 25,
    ) -> dict[str, object]:
        """
        Search Jira using JQL.

        This is read-only and returns at most 100 issues.
        """
        return search_jira_data(
            jql=jql,
            max_results=max_results,
        )

    @mcp.tool()
    def get_jira_issue_comments(
        issue_key: str,
        max_results: int = 50,
    ) -> dict[str, object]:
        """
        Fetch comments for one Jira issue.
        """
        return get_jira_issue_comments_data(
            issue_key=issue_key,
            max_results=max_results,
        )
