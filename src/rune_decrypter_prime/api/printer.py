from __future__ import annotations

"""Standard printer facade for RDP display summaries and console output.

The printer layer is intentionally thin: it does not solve, score, mutate
solutions, or infer missing configuration. It renders or writes the standard
``RdpDisplaySummary`` produced by ``api.display`` and provides shared human
console formatting for tutorials and review runners.

OPSEC rule: public return values and rendered artifact paths are display-safe;
real filesystem paths may be used internally only to write files.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, TextIO

from rune_decrypter_prime.api.display import (
    DISPLAY_SUMMARY_RELPATH,
    RdpDisplayOptions,
    RdpDisplaySummary,
    build_rdp_summary,
    format_rdp_summary,
    write_rdp_summary_json,
)


class RdpPrintFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


class RdpPrintDetail(StrEnum):
    COMPACT = "compact"
    STANDARD = "standard"
    DETAILED = "detailed"
    DEBUG = "debug"


class RdpBannerStyle(StrEnum):
    PLAIN = "plain"
    BOX = "box"


@dataclass(frozen=True, slots=True)
class RdpPrintOptions:
    """Controls shared human console presentation."""

    detail: RdpPrintDetail | str = RdpPrintDetail.DETAILED
    width: int = 72
    output_root: str = "output/"
    banner_style: RdpBannerStyle | str = RdpBannerStyle.PLAIN

    def __post_init__(self) -> None:
        object.__setattr__(self, "detail", _ensure_print_detail(self.detail))
        object.__setattr__(self, "banner_style", _ensure_banner_style(self.banner_style))
        _require_positive_int(self.width, "width")
        object.__setattr__(self, "output_root", _safe_display_path(self.output_root, field_name="output_root"))

    @classmethod
    def compact(cls) -> "RdpPrintOptions":
        return cls(detail=RdpPrintDetail.COMPACT)

    @classmethod
    def standard(cls) -> "RdpPrintOptions":
        return cls(detail=RdpPrintDetail.STANDARD)

    @classmethod
    def detailed(cls) -> "RdpPrintOptions":
        return cls(detail=RdpPrintDetail.DETAILED)

    @classmethod
    def debug(cls) -> "RdpPrintOptions":
        return cls(detail=RdpPrintDetail.DEBUG, width=88)


def render_rdp_summary(
    summary: RdpDisplaySummary | object,
    *,
    output_format: RdpPrintFormat | str = RdpPrintFormat.TEXT,
    **build_kwargs: Any,
) -> str:
    """Render a standard RDP summary as text or JSON.

    ``summary`` may already be an ``RdpDisplaySummary`` or may be any value
    accepted by ``build_rdp_summary``. Build keyword arguments are forwarded only
    when a summary must be built.
    """

    fmt = _ensure_print_format(output_format)
    if not isinstance(summary, RdpDisplaySummary):
        summary = build_rdp_summary(summary, **build_kwargs)

    if fmt is RdpPrintFormat.TEXT:
        return format_rdp_summary(summary)
    if fmt is RdpPrintFormat.JSON:
        return json.dumps(summary.to_json_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    raise AssertionError(f"unhandled print format: {fmt}")


def print_rdp_result(
    value: object,
    *,
    file: TextIO | None = None,
    output_format: RdpPrintFormat | str = RdpPrintFormat.TEXT,
    options: RdpDisplayOptions | None = None,
    **build_kwargs: Any,
) -> RdpDisplaySummary:
    """Build, print, and return the standard RDP display summary."""

    summary = build_rdp_summary(value, options=options, **build_kwargs)
    rendered = render_rdp_summary(summary, output_format=output_format)
    if file is None:
        import sys

        file = sys.stdout
    file.write(rendered)
    return summary


def write_rdp_summary_artifact(
    summary: RdpDisplaySummary | object,
    *,
    run_dir: Path,
    options: RdpDisplayOptions | None = None,
    **build_kwargs: Any,
) -> str:
    """Write ``artifacts/rdp_display_summary.json`` under ``run_dir``.

    The returned value is always the standard run-relative sidecar path, never an
    absolute local path.
    """

    if not isinstance(run_dir, Path):
        raise TypeError("run_dir must be a Path")
    if isinstance(summary, RdpDisplaySummary):
        built = summary
    else:
        built = build_rdp_summary(summary, options=options, **build_kwargs)
    relpath = write_rdp_summary_json(built, run_dir / DISPLAY_SUMMARY_RELPATH)
    if relpath != DISPLAY_SUMMARY_RELPATH:
        # Keep the public contract fixed even if the internal path was absolute.
        return DISPLAY_SUMMARY_RELPATH
    return relpath


def format_rdp_banner(
    *,
    title: str = "Rune Decrypter Prime",
    version_label: str = "RDP V1 pre-release",
    output_root: str | Path | None = None,
    options: RdpPrintOptions | None = None,
) -> str:
    """Return the standard restrained RDP console banner."""
    opts = _ensure_print_options(options)
    root = opts.output_root if output_root is None else _safe_display_path(output_root, field_name="output_root")
    lines = [
        _require_text(title, "title"),
        "=" * len(title),
        _require_text(version_label, "version_label"),
        f"output root : {root}",
    ]
    if opts.banner_style is RdpBannerStyle.PLAIN:
        return "\n".join(lines) + "\n"

    inner_width = max(max(len(line) for line in lines), 42)
    out = ["+" + "-" * (inner_width + 2) + "+"]
    out.extend(f"| {line.ljust(inner_width)} |" for line in lines)
    out.append("+" + "-" * (inner_width + 2) + "+")
    return "\n".join(out) + "\n"


def format_rdp_section(title: str, *, underline: str = "-") -> str:
    """Return a simple deterministic section heading."""
    title_text = _require_text(title, "title")
    underline_text = _require_text(underline, "underline")
    marker = underline_text[0]
    return f"{title_text}\n{marker * len(title_text)}\n"


def format_rdp_kv_block(
    title: str,
    rows: Mapping[str, Any] | Sequence[tuple[str, Any]],
    *,
    options: RdpPrintOptions | None = None,
) -> str:
    """Return a deterministic key/value section for human console output."""
    _ensure_print_options(options)
    items = _normalise_rows(rows)
    key_width = max((len(key) for key, _ in items), default=0)
    lines = [format_rdp_section(title).rstrip()]
    for key, value in items:
        rendered = _display_value(value)
        value_lines = rendered.splitlines() or [""]
        lines.append(f"{key.ljust(key_width)} : {value_lines[0]}")
        indent = " " * (key_width + 3)
        lines.extend(f"{indent}{line}" for line in value_lines[1:])
    return "\n".join(lines) + "\n"


def format_rdp_preview_block(
    title: str,
    rows: Mapping[str, Any] | Sequence[tuple[str, Any]],
    *,
    options: RdpPrintOptions | None = None,
) -> str:
    """Return a preview section using the standard key/value style."""
    return format_rdp_kv_block(title, rows, options=options)


def format_rdp_status_block(
    title: str,
    rows: Mapping[str, Any] | Sequence[tuple[str, Any]],
    *,
    options: RdpPrintOptions | None = None,
) -> str:
    """Return a status section using the standard key/value style."""
    return format_rdp_kv_block(title, rows, options=options)


def print_rdp_text(text: str, *, file: TextIO | None = None) -> None:
    """Write human console text to ``file`` or stdout."""
    if file is None:
        import sys

        file = sys.stdout
    file.write(str(text))
    if text and not str(text).endswith("\n"):
        file.write("\n")


def print_rdp_block(text: str, *, file: TextIO | None = None) -> None:
    """Write a complete console block followed by one blank line."""
    if file is None:
        import sys

        file = sys.stdout
    file.write(str(text).rstrip() + "\n\n")


def _normalise_rows(rows: Mapping[str, Any] | Sequence[tuple[str, Any]]) -> list[tuple[str, Any]]:
    if isinstance(rows, Mapping):
        iterable = list(rows.items())
    elif isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)):
        iterable = list(rows)
    else:
        raise TypeError("rows must be a mapping or sequence of key/value pairs")

    out: list[tuple[str, Any]] = []
    for index, item in enumerate(iterable):
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError(f"rows[{index}] must be a two-item tuple")
        key, value = item
        out.append((_require_text(str(key), f"rows[{index}].key"), value))
    return out


def _display_value(value: Any) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, Path):
        return _safe_display_path(value, field_name="value")
    if isinstance(value, float):
        return f"{value:.6f}" if value == value and abs(value) < 1e9 else str(value)
    return str(value)


def _safe_display_path(value: str | Path, *, field_name: str) -> str:
    if isinstance(value, Path):
        if value.is_absolute():
            raise ValueError(f"{field_name} must be display-safe and repo-relative")
        text = value.as_posix()
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError(f"{field_name} must not be empty")
        path = Path(text)
        if path.is_absolute() or _looks_windows_absolute(text):
            raise ValueError(f"{field_name} must be display-safe and repo-relative")
        text = text.replace("\\", "/")
    else:
        raise TypeError(f"{field_name} must be a string or Path")
    return text


def _looks_windows_absolute(value: str) -> bool:
    return len(value) >= 3 and value[1] == ":" and value[2] in {"/", "\\"} and value[0].isalpha()


def _ensure_print_format(value: RdpPrintFormat | str) -> RdpPrintFormat:
    if isinstance(value, RdpPrintFormat):
        return value
    try:
        return RdpPrintFormat(str(value))
    except ValueError as exc:
        allowed = sorted(item.value for item in RdpPrintFormat)
        raise ValueError(f"output_format must be one of {allowed}") from exc


def _ensure_print_detail(value: RdpPrintDetail | str) -> RdpPrintDetail:
    if isinstance(value, RdpPrintDetail):
        return value
    try:
        return RdpPrintDetail(str(value))
    except ValueError as exc:
        allowed = sorted(item.value for item in RdpPrintDetail)
        raise ValueError(f"detail must be one of {allowed}") from exc


def _ensure_banner_style(value: RdpBannerStyle | str) -> RdpBannerStyle:
    if isinstance(value, RdpBannerStyle):
        return value
    try:
        return RdpBannerStyle(str(value))
    except ValueError as exc:
        allowed = sorted(item.value for item in RdpBannerStyle)
        raise ValueError(f"banner_style must be one of {allowed}") from exc


def _ensure_print_options(value: RdpPrintOptions | None) -> RdpPrintOptions:
    if value is None:
        return RdpPrintOptions.detailed()
    if not isinstance(value, RdpPrintOptions):
        raise TypeError("options must be RdpPrintOptions or None")
    return value


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _require_positive_int(value: Any, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value <= 0:
        raise ValueError(f"{field_name} must be > 0")


__all__ = [
    "RdpBannerStyle",
    "RdpPrintDetail",
    "RdpPrintFormat",
    "RdpPrintOptions",
    "format_rdp_banner",
    "format_rdp_kv_block",
    "format_rdp_preview_block",
    "format_rdp_section",
    "format_rdp_status_block",
    "print_rdp_block",
    "print_rdp_result",
    "print_rdp_text",
    "render_rdp_summary",
    "write_rdp_summary_artifact",
]
