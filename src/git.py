import subprocess
from pathlib import Path
from typing import Any

from .repositories import get_repository, resolve_repo_file


MAX_DIFF_LINES = 300
MAX_GIT_OUTPUT_CHARS = 20_000


def run_git(
    repo_path: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a Git command against a repository."""
    return subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True,
        check=check,
        encoding="utf-8",
        errors="replace",
    )


def _truncate_text(
    value: str,
    limit: int = MAX_GIT_OUTPUT_CHARS,
) -> dict[str, Any]:
    """Return bounded text together with truncation metadata."""
    if len(value) <= limit:
        return {
            "content": value,
            "truncated": False,
            "original_char_count": len(value),
        }

    return {
        "content": (
            f"... output truncated "
            f"({len(value) - limit} chars omitted) ...\n"
            f"{value[-limit:]}"
        ),
        "truncated": True,
        "original_char_count": len(value),
    }


def get_git_status_data(repository: str) -> dict[str, str]:
    repo_path = get_repository(repository)

    branch = run_git(
        repo_path,
        "branch",
        "--show-current",
    ).stdout.strip()

    status = run_git(
        repo_path,
        "status",
        "--short",
    ).stdout.strip()

    return {
        "branch": branch,
        "status": status or "clean",
    }


def list_changed_files_data(repository: str) -> dict[str, object]:
    repo_path = get_repository(repository)

    process = run_git(
        repo_path,
        "status",
        "--porcelain=v1",
    )

    files: list[dict[str, object]] = []

    for line in process.stdout.splitlines():
        if len(line) < 3:
            continue

        status = line[:2]
        path = line[3:]

        files.append(
            {
                "status": status,
                "path": path,
                "staged": status[0] not in (" ", "?"),
                "unstaged": status[1] not in (" ", "?"),
                "untracked": status == "??",
            }
        )

    return {
        "repository": repository,
        "clean": not files,
        "files": files,
    }


def list_branches_data(repository: str) -> dict[str, object]:
    repo_path = get_repository(repository)

    current_branch = run_git(
        repo_path,
        "branch",
        "--show-current",
    ).stdout.strip()

    local_output = run_git(
        repo_path,
        "branch",
        "--format=%(refname:short)",
    ).stdout

    remote_output = run_git(
        repo_path,
        "branch",
        "--remotes",
        "--format=%(refname:short)",
    ).stdout

    local_branches = [
        branch.strip()
        for branch in local_output.splitlines()
        if branch.strip()
    ]

    remote_branches = [
        branch.strip()
        for branch in remote_output.splitlines()
        if branch.strip() and not branch.endswith("/HEAD")
    ]

    return {
        "current_branch": current_branch,
        "local_branches": local_branches,
        "remote_branches": remote_branches,
    }


def compare_branches_data(
    repository: str,
    base: str,
    head: str,
) -> dict[str, object]:
    repo_path = get_repository(repository)

    commits_output = run_git(
        repo_path,
        "log",
        "--oneline",
        f"{base}..{head}",
    ).stdout.strip()

    files_output = run_git(
        repo_path,
        "diff",
        "--name-status",
        base,
        head,
    ).stdout.strip()

    stat_output = run_git(
        repo_path,
        "diff",
        "--stat",
        base,
        head,
    ).stdout.strip()

    commits = [
        line
        for line in commits_output.splitlines()
        if line
    ]

    changed_files = [
        line
        for line in files_output.splitlines()
        if line
    ]

    return {
        "base": base,
        "head": head,
        "commits_ahead": len(commits),
        "commits": commits,
        "changed_files": changed_files,
        "diff_stat": stat_output or "No differences",
    }


def get_commit_history_data(
    repository: str,
    branch: str | None = None,
    limit: int = 20,
) -> dict[str, object]:
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")

    repo_path = get_repository(repository)

    command = [
        "log",
        f"-{limit}",
        "--date=iso-strict",
        "--pretty=format:%H%x09%h%x09%ad%x09%an%x09%s",
    ]

    if branch:
        command.append(branch)

    process = run_git(repo_path, *command)

    commits: list[dict[str, str]] = []

    for line in process.stdout.splitlines():
        parts = line.split("\t", 4)

        if len(parts) != 5:
            continue

        full_hash, short_hash, date, author, subject = parts

        commits.append(
            {
                "hash": full_hash,
                "short_hash": short_hash,
                "date": date,
                "author": author,
                "subject": subject,
            }
        )

    return {
        "repository": repository,
        "branch": branch or "current",
        "commits": commits,
    }


def show_commit_data(
    repository: str,
    commit: str,
) -> dict[str, object]:
    repo_path = get_repository(repository)

    metadata = run_git(
        repo_path,
        "show",
        "--no-patch",
        "--date=iso-strict",
        "--format=%H%n%h%n%an%n%ad%n%s%n%b",
        commit,
    ).stdout.strip()

    files = run_git(
        repo_path,
        "show",
        "--name-status",
        "--format=",
        commit,
    ).stdout.strip()

    stat = run_git(
        repo_path,
        "show",
        "--stat",
        "--format=",
        commit,
    ).stdout.strip()

    metadata_lines = metadata.splitlines()

    return {
        "repository": repository,
        "commit": commit,
        "full_hash": metadata_lines[0] if len(metadata_lines) > 0 else "",
        "short_hash": metadata_lines[1] if len(metadata_lines) > 1 else "",
        "author": metadata_lines[2] if len(metadata_lines) > 2 else "",
        "date": metadata_lines[3] if len(metadata_lines) > 3 else "",
        "subject": metadata_lines[4] if len(metadata_lines) > 4 else "",
        "body": "\n".join(metadata_lines[5:]).strip(),
        "changed_files": [
            line
            for line in files.splitlines()
            if line.strip()
        ],
        "diff_stat": stat or "No file changes",
    }


def get_working_tree_diff_summary_data(
    repository: str,
) -> dict[str, object]:
    """
    Return bounded diff summaries rather than full repository diffs.
    """
    repo_path = get_repository(repository)

    unstaged = run_git(
        repo_path,
        "diff",
        "--stat",
    ).stdout.strip()

    staged = run_git(
        repo_path,
        "diff",
        "--cached",
        "--stat",
    ).stdout.strip()

    return {
        "repository": repository,
        "unstaged": unstaged or "No unstaged changes",
        "staged": staged or "No staged changes",
    }


def get_file_diff_data(
    repository: str,
    path: str,
    max_lines: int = MAX_DIFF_LINES,
) -> dict[str, object]:
    if max_lines < 1 or max_lines > 1000:
        raise ValueError("max_lines must be between 1 and 1000")

    repo_root, file_path = resolve_repo_file(
        repository,
        path,
        require_exists=False,
    )

    relative_path = file_path.relative_to(repo_root)

    def run_diff(staged: bool) -> dict[str, object]:
        command = ["diff"]

        if staged:
            command.append("--cached")

        command.extend(["--", str(relative_path)])

        process = run_git(repo_root, *command)
        lines = process.stdout.splitlines()

        return {
            "line_count": len(lines),
            "truncated": len(lines) > max_lines,
            "diff": (
                "\n".join(lines[:max_lines])
                if lines
                else "No changes"
            ),
        }

    return {
        "repository": repository,
        "path": str(relative_path),
        "unstaged": run_diff(staged=False),
        "staged": run_diff(staged=True),
    }


def get_project_status_data() -> dict[str, object]:
    from .repositories import load_repositories

    repositories = load_repositories()
    project_status: dict[str, object] = {}

    for name, repo_path in repositories.items():
        branch = run_git(
            repo_path,
            "branch",
            "--show-current",
        ).stdout.strip()

        status_output = run_git(
            repo_path,
            "status",
            "--short",
        ).stdout.strip()

        latest_commit_output = run_git(
            repo_path,
            "log",
            "-1",
            "--date=iso-strict",
            "--pretty=format:%H%x09%h%x09%ad%x09%an%x09%s",
        ).stdout.strip()

        latest_commit = None

        if latest_commit_output:
            parts = latest_commit_output.split("\t", 4)

            if len(parts) == 5:
                full_hash, short_hash, date, author, subject = parts
                latest_commit = {
                    "hash": full_hash,
                    "short_hash": short_hash,
                    "date": date,
                    "author": author,
                    "subject": subject,
                }

        upstream = run_git(
            repo_path,
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            "@{upstream}",
            check=False,
        )

        ahead = None
        behind = None
        upstream_name = None

        if upstream.returncode == 0:
            upstream_name = upstream.stdout.strip()

            counts = run_git(
                repo_path,
                "rev-list",
                "--left-right",
                "--count",
                f"{upstream_name}...HEAD",
            ).stdout.strip()

            if counts:
                behind_text, ahead_text = counts.split()
                behind = int(behind_text)
                ahead = int(ahead_text)

        changed_files = [
            line
            for line in status_output.splitlines()
            if line.strip()
        ]

        project_status[name] = {
            "branch": branch,
            "clean": not bool(status_output),
            "changed_files": changed_files,
            "upstream": upstream_name,
            "ahead": ahead,
            "behind": behind,
            "latest_commit": latest_commit,
        }

    return project_status


def read_file_at_ref_data(
    repository: str,
    ref: str,
    path: str,
    max_chars: int = 50_000,
) -> dict[str, object]:
    """
    Read a text file from a Git ref without changing the working tree.

    Args:
        repository: Configured repository name.
        ref: Branch, tag, commit hash, or other Git revision.
        path: File path relative to the repository root.
        max_chars: Maximum number of characters to return.
    """
    if max_chars < 1 or max_chars > 200_000:
        raise ValueError("max_chars must be between 1 and 200000")

    repo_path = get_repository(repository)

    process = run_git(
        repo_path,
        "show",
        f"{ref}:{path}",
        check=False,
    )

    if process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip()

        raise ValueError(
            f"Could not read '{path}' at ref '{ref}' "
            f"in repository '{repository}': {detail}"
        )

    content = process.stdout
    truncated = len(content) > max_chars

    return {
        "repository": repository,
        "ref": ref,
        "path": path,
        "char_count": len(content),
        "truncated": truncated,
        "content": content[:max_chars],
    }


def list_files_at_ref_data(
    repository: str,
    ref: str,
    path: str = "",
    max_results: int = 1000,
) -> dict[str, object]:
    """
    List files/directories at a Git ref without changing branches.

    Args:
        repository: Configured repository name.
        ref: Branch, tag, commit hash, or other Git revision.
        path: Optional repository-relative directory.
        max_results: Maximum entries to return.
    """
    if max_results < 1 or max_results > 5000:
        raise ValueError("max_results must be between 1 and 5000")

    repo_path = get_repository(repository)

    command = [
        "ls-tree",
        "--name-only",
    ]

    if path:
        command.extend(
            [
                f"{ref}:{path}",
            ]
        )
    else:
        command.append(ref)

    process = run_git(
        repo_path,
        *command,
        check=False,
    )

    if process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip()

        raise ValueError(
            f"Could not list files at ref '{ref}' "
            f"and path '{path}' in repository '{repository}': {detail}"
        )

    entries = [
        line.strip()
        for line in process.stdout.splitlines()
        if line.strip()
    ]

    return {
        "repository": repository,
        "ref": ref,
        "path": path,
        "returned": min(len(entries), max_results),
        "total_found": len(entries),
        "truncated": len(entries) > max_results,
        "entries": entries[:max_results],
    }
