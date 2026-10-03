"""Credentials and settings from the environment, with an optional ignored .env file."""
import os
from pathlib import Path


def load_env(path: Path = Path(".env")) -> dict[str, str]:
    """Environment variables, with values from .env filling in anything not already set.

    .env format: KEY=value per line, '#' comments, optional single or double quotes.
    """
    values: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            values[key.strip()] = val.strip().strip("'\"")
    return {**values, **os.environ}
