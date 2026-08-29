"""Internal artifact path and portable-message policy helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import re

EXTERNAL_PATH = "<external>"
REDACTED_PATH_TEXT = "<path>"

_QUOTED_WINDOWS_ABS_PATH_RE = re.compile(
    r"(?i)(?<=[\"'])[a-z]:[\\/][^\"'<>|]+(?=[\"'])"
)
_QUOTED_UNC_ABS_PATH_RE = re.compile(r"(?<=[\"'])\\\\[^\"'<>|]+(?=[\"'])")
_QUOTED_UNIX_ABS_PATH_RE = re.compile(r"(?<=[\"'])/(?:[^\"'<>|]+/)*[^\"'<>|]+(?=[\"'])")
_WINDOWS_ABS_PATH_RE = re.compile(r"(?i)\b[a-z]:[\\/][^\s\"'<>|]+")
_UNC_ABS_PATH_RE = re.compile(r"\\\\[^\s\"'<>|]+")
_UNIX_ABS_PATH_RE = re.compile(r"(?<!\w)/(?:[^\s\"'<>|]+/)*[^\s\"'<>|]+")


def artifact_path(value: Path, *, root: Path) -> str:
    """Render a path for a portable artifact field relative to ``root``."""
    if not value.is_absolute():
        return value.as_posix()
    try:
        return value.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return EXTERNAL_PATH


def artifact_json_value(value: Any, *, root: Path) -> Any:
    """Convert explicit Path values inside structured JSON payloads."""
    if isinstance(value, Path):
        return artifact_path(value, root=root)
    if isinstance(value, dict):
        return {
            key: artifact_json_value(item, root=root) for key, item in value.items()
        }
    if isinstance(value, list):
        return [artifact_json_value(item, root=root) for item in value]
    if isinstance(value, tuple):
        return [artifact_json_value(item, root=root) for item in value]
    return value


def portable_exception_message(
    exc: Exception, *, max_len: int = 240
) -> tuple[str, bool]:
    """Return a short message safe for explicitly portable event fields."""
    message = str(exc)
    redacted = False
    for pattern in (
        _QUOTED_UNC_ABS_PATH_RE,
        _QUOTED_WINDOWS_ABS_PATH_RE,
        _QUOTED_UNIX_ABS_PATH_RE,
        _UNC_ABS_PATH_RE,
        _WINDOWS_ABS_PATH_RE,
        _UNIX_ABS_PATH_RE,
    ):
        updated = pattern.sub(REDACTED_PATH_TEXT, message)
        if updated != message:
            redacted = True
            message = updated
    if len(message) > max_len:
        redacted = True
        if max_len <= 3:
            message = message[:max_len]
        else:
            message = message[: max_len - 3] + "..."
    return message, redacted
