from __future__ import annotations

"""Standard printer facade for RDP display summaries.

The printer layer is intentionally thin: it does not solve, score, mutate
solutions, or infer missing configuration. It renders or writes the standard
``RdpDisplaySummary`` produced by ``api.display``.

OPSEC rule: public return values and rendered artifact paths are display-safe;
real filesystem paths may be used internally only to write files.
"""

import json
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


def _ensure_print_format(value: RdpPrintFormat | str) -> RdpPrintFormat:
    if isinstance(value, RdpPrintFormat):
        return value
    try:
        return RdpPrintFormat(str(value))
    except ValueError as exc:
        allowed = sorted(item.value for item in RdpPrintFormat)
        raise ValueError(f"output_format must be one of {allowed}") from exc


__all__ = [
    "RdpPrintFormat",
    "print_rdp_result",
    "render_rdp_summary",
    "write_rdp_summary_artifact",
]
