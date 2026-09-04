import json
import subprocess

from .repositories import get_repository, load_repositories


DEFAULT_MAX_MATCHES = 200
MAX_MATCHES_LIMIT = 1000


def search_code_data(
    query: str,
    repository: str | None = None,
    max_matches: int = DEFAULT_MAX_MATCHES,
) -> dict[str, object]:
    """
    Search literal text across one or all enabled repositories.

    Uses ripgrep JSON output so Windows paths do not need custom parsing.
    """
    if not query:
        raise ValueError("query must not be empty")

    if max_matches < 1 or max_matches > MAX_MATCHES_LIMIT:
        raise ValueError(
            f"max_matches must be between 1 and {MAX_MATCHES_LIMIT}"
        )

    if repository is not None:
        repositories = {repository: get_repository(repository)}
    else:
        repositories = load_repositories()

    results: dict[str, list[dict[str, str | int]]] = {}
    total_matches = 0
    truncated = False

    for name, path in repositories.items():
        remaining = max_matches - total_matches

        if remaining <= 0:
            truncated = True
            break

        process = subprocess.run(
            [
                "rg",
                "--json",
                "--fixed-strings",
                "--max-count",
                str(remaining),
                "-e",
                query,
                "--",
                str(path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        # ripgrep exit codes:
        # 0 -> one or more matches
        # 1 -> no matches
        # >1 -> actual error
        if process.returncode not in (0, 1):
            raise RuntimeError(
                f"ripgrep failed in repository '{name}': "
                f"{process.stderr.strip()}"
            )

        matches: list[dict[str, str | int]] = []

        for line in process.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("type") != "match":
                continue

            data = event["data"]

            matches.append(
                {
                    "file": data["path"]["text"],
                    "line": data["line_number"],
                    "content": data["lines"]["text"].strip(),
                }
            )

            total_matches += 1

            if total_matches >= max_matches:
                truncated = True
                break

        if matches:
            results[name] = matches

        if truncated:
            break

    return {
        "query": query,
        "repository": repository or "all enabled repositories",
        "match_count": total_matches,
        "truncated": truncated,
        "max_matches": max_matches,
        "results": results,
    }
