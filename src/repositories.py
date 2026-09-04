from pathlib import Path

from .config import PROJECT_DIR, load_config


def load_repositories() -> dict[str, Path]:
    """Return configured and enabled repositories."""
    config = load_config()

    repositories: dict[str, Path] = {}

    for name, repository in config["repositories"].items():
        if not isinstance(repository, dict):
            raise ValueError(
                f"Repository configuration for '{name}' must be a mapping"
            )

        if not repository.get("enabled", True):
            continue

        raw_path = repository.get("path")
        if not raw_path:
            raise ValueError(
                f"Repository '{name}' is missing a 'path' value"
            )

        repositories[name] = (PROJECT_DIR / raw_path).resolve()

    return repositories


def get_repository(repository: str) -> Path:
    repositories = load_repositories()

    if repository in repositories:
        return repositories[repository]

    for repo_path in repositories.values():
        if repo_path.name == repository:
            return repo_path

    available = ", ".join(
        f"{alias} ({path.name})"
        for alias, path in sorted(repositories.items())
    )

    raise ValueError(
        f"Unknown or disabled repository '{repository}'. "
        f"Available repositories: {available}"
    )


def resolve_repo_file(
    repository: str,
    path: str,
    *,
    require_exists: bool = True,
) -> tuple[Path, Path]:
    """
    Resolve a file path while preventing access outside the repository.

    Returns:
        Tuple of (repository root, resolved file path).
    """
    repo_root = get_repository(repository).resolve()
    file_path = (repo_root / path).resolve()

    try:
        file_path.relative_to(repo_root)
    except ValueError as error:
        raise ValueError("Path must stay inside the repository") from error

    if require_exists:
        if not file_path.exists():
            raise FileNotFoundError(path)

        if not file_path.is_file():
            raise ValueError(f"Not a file: {path}")

    return repo_root, file_path


def list_repositories_data() -> dict[str, dict[str, str | bool]]:
    """Return repository discovery information."""
    repositories = load_repositories()

    return {
        name: {
            "path": str(path),
            "exists": path.exists(),
            "is_git_repository": (path / ".git").exists(),
        }
        for name, path in repositories.items()
    }
