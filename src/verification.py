import subprocess
from typing import Any

from .config import load_config
from .repositories import get_repository


MAX_TIMEOUT_SECONDS = 600
DEFAULT_TIMEOUT_SECONDS = 120
MAX_OUTPUT_CHARS = 20_000


def _truncate_output(
    value: str,
    limit: int = MAX_OUTPUT_CHARS,
) -> dict[str, Any]:
    """Return bounded output and explicit truncation metadata."""
    value = value or ""

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


def get_verification_config_data(
    repository: str,
) -> dict[str, object]:
    """
    Return configured verification commands without executing them.
    """
    # Enforces enabled/known repository semantics consistently.
    get_repository(repository)

    config = load_config()

    verification = (
        config["repositories"][repository]
        .get("verification", {})
    )

    if not isinstance(verification, dict):
        raise ValueError(
            f"'verification' for repository '{repository}' "
            f"must be a mapping"
        )

    return {
        "repository": repository,
        "available_checks": list(verification),
        "commands": verification,
    }


def run_verification_data(
    repository: str,
    check: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, object]:
    """
    Run one allow-listed verification command from repositories.yaml.
    """
    if timeout_seconds < 1 or timeout_seconds > MAX_TIMEOUT_SECONDS:
        raise ValueError(
            f"timeout_seconds must be between 1 and "
            f"{MAX_TIMEOUT_SECONDS}"
        )

    repo_path = get_repository(repository)
    config = load_config()

    repository_config = config["repositories"][repository]
    verification = repository_config.get("verification", {})

    if not isinstance(verification, dict):
        raise ValueError(
            f"'verification' for repository '{repository}' "
            f"must be a mapping"
        )

    if check not in verification:
        available = ", ".join(verification) or "none"
        raise ValueError(
            f"Unknown verification check '{check}'. "
            f"Available checks: {available}"
        )

    command = verification[check]

    if not isinstance(command, list):
        raise ValueError(
            f"Verification command '{check}' must be a YAML list"
        )

    if not command:
        raise ValueError(
            f"Verification command '{check}' is empty"
        )

    if not all(isinstance(part, str) for part in command):
        raise ValueError(
            f"Every argument for verification check '{check}' "
            f"must be a string"
        )

    try:
        process = subprocess.run(
            command,
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )

        return {
            "repository": repository,
            "check": check,
            "command": command,
            "exit_code": process.returncode,
            "success": process.returncode == 0,
            "timed_out": False,
            "stdout": _truncate_output(process.stdout),
            "stderr": _truncate_output(process.stderr),
        }

    except subprocess.TimeoutExpired as error:
        stdout = (
            error.stdout
            if isinstance(error.stdout, str)
            else ""
        )
        stderr = (
            error.stderr
            if isinstance(error.stderr, str)
            else ""
        )

        return {
            "repository": repository,
            "check": check,
            "command": command,
            "exit_code": None,
            "success": False,
            "timed_out": True,
            "timeout_seconds": timeout_seconds,
            "stdout": _truncate_output(stdout),
            "stderr": _truncate_output(stderr),
        }
