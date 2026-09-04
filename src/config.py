from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_DIR / "repositories.yaml"
ENV_PATH = PROJECT_DIR / ".env"

load_dotenv(ENV_PATH)


def load_config() -> dict[str, Any]:
    """Load the MCP project configuration."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Could not find repositories.yaml at {CONFIG_PATH}"
        )

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    if "repositories" not in config:
        raise ValueError(
            "repositories.yaml must contain a top-level 'repositories' mapping"
        )

    if not isinstance(config["repositories"], dict):
        raise ValueError("'repositories' must be a mapping")

    return config
