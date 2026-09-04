from .repositories import resolve_repo_file


MAX_READ_LINES = 500


def read_file_data(
    repository: str,
    path: str,
) -> str:
    """Read a UTF-8 text file from a configured repository."""
    _, file_path = resolve_repo_file(repository, path)

    return file_path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def read_file_range_data(
    repository: str,
    path: str,
    start_line: int,
    end_line: int,
) -> dict[str, object]:
    """Read a bounded 1-based inclusive line range."""
    if start_line < 1:
        raise ValueError("start_line must be at least 1")

    if end_line < start_line:
        raise ValueError(
            "end_line must be greater than or equal to start_line"
        )

    requested_line_count = end_line - start_line + 1

    if requested_line_count > MAX_READ_LINES:
        raise ValueError(
            f"Line range is too large; request at most "
            f"{MAX_READ_LINES} lines"
        )

    _, file_path = resolve_repo_file(repository, path)

    lines = file_path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    if start_line > len(lines):
        return {
            "repository": repository,
            "path": path,
            "start_line": start_line,
            "end_line": start_line - 1,
            "total_lines": len(lines),
            "lines": [],
        }

    actual_end = min(end_line, len(lines))

    selected = [
        {
            "line": line_number,
            "content": lines[line_number - 1],
        }
        for line_number in range(start_line, actual_end + 1)
    ]

    return {
        "repository": repository,
        "path": path,
        "start_line": start_line,
        "end_line": actual_end,
        "total_lines": len(lines),
        "lines": selected,
    }
