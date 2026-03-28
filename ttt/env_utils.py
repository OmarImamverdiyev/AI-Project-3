from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


def load_dotenv(path: str | Path = ".env", *, override: bool = False) -> dict[str, str]:
    """Load simple KEY=VALUE pairs from a .env file into os.environ."""

    dotenv_path = Path(path)
    if not dotenv_path.exists():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_inline_comment(value.strip())
        value = _strip_quotes(value)
        if not key:
            continue

        loaded[key] = value
        if override or key not in os.environ:
            os.environ[key] = value
    return loaded


def env_str(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def env_int(name: str) -> int | None:
    value = env_str(name)
    if value is None:
        return None
    return int(value)


def env_float(name: str) -> float | None:
    value = env_str(name)
    if value is None:
        return None
    return float(value)


def upsert_dotenv(path: str | Path = ".env", values: Mapping[str, object] | None = None) -> None:
    """Update or append KEY=VALUE pairs in a .env-style file."""

    if not values:
        return

    dotenv_path = Path(path)
    existing_lines = []
    if dotenv_path.exists():
        existing_lines = dotenv_path.read_text(encoding="utf-8").splitlines()

    remaining = {
        key: str(value)
        for key, value in values.items()
        if value is not None and str(key).strip()
    }
    output_lines: list[str] = []

    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            output_lines.append(line)
            continue

        key, _, _ = line.partition("=")
        normalized_key = key.strip()
        if normalized_key in remaining:
            output_lines.append(f"{normalized_key}={remaining.pop(normalized_key)}")
        else:
            output_lines.append(line)

    for key, value in remaining.items():
        output_lines.append(f"{key}={value}")

    dotenv_path.write_text("\n".join(output_lines).rstrip() + "\n", encoding="utf-8")


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _strip_inline_comment(value: str) -> str:
    if "#" not in value:
        return value

    in_single = False
    in_double = False
    for idx, char in enumerate(value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            return value[:idx].rstrip()
    return value
