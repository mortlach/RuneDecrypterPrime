from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from rdp.api.display import (
    PrintOptions,
    format_banner,
    format_key_value_block,
    format_preview_block,
    format_section,
    format_status_block,
    print_block,
)
from rdp.scoring.language_model.load_status import LmLoadStatus
from rune_decrypter_prime.utils.tutorial_output import tutorial_debug_preview_block

TRUTH_REFERENCE_USE = "stop-score calibration; not supplied to solver ranking"


def default_options() -> PrintOptions:
    return PrintOptions.detailed()


def print_rdp_identity(*, options: PrintOptions | None = None) -> None:
    print_block(format_banner(options=options or default_options()))


def print_initialising(*, options: PrintOptions | None = None) -> None:
    print_block(
        format_key_value_block(
            "Initialising RDP",
            [
                ("display schema", "api_display_summary.v1"),
                ("encoding", "utf-8"),
                ("status", "ready"),
            ],
            options=options or default_options(),
        )
    )


def print_tutorial_contract(
    *,
    name: str,
    cipher: str,
    solver: str,
    direction: str,
    expected_result: str,
    uses_reference_stop_score: bool = True,
    extra_rows: Mapping[str, Any] | Sequence[tuple[str, Any]] = (),
    options: PrintOptions | None = None,
) -> None:
    rows: list[tuple[str, Any]] = [
        ("name", name),
        ("cipher", cipher),
        ("solver", solver),
        ("direction", direction),
        ("expected result", expected_result),
    ]
    if uses_reference_stop_score:
        rows.append(("truth/reference use", TRUTH_REFERENCE_USE))
    else:
        rows.append(("truth/reference use", "not supplied to solver"))
    rows.extend(_rows(extra_rows))
    print_block(format_key_value_block("Tutorial", rows, options=options or default_options()))


def print_problem_input(
    rows: Mapping[str, Any] | Sequence[tuple[str, Any]],
    *,
    options: PrintOptions | None = None,
) -> None:
    print_block(format_key_value_block("Problem input", rows, options=options or default_options()))


def print_preview(
    title: str,
    rows: Mapping[str, Any] | Sequence[tuple[str, Any]],
    *,
    options: PrintOptions | None = None,
) -> None:
    print_block(format_preview_block(title, rows, options=options or default_options()))


def print_debug_preview(
    *,
    label: str,
    idx: Sequence[int],
    wli: Sequence[Sequence[int]] | None,
    direction: Any,
    options: PrintOptions | None = None,
) -> None:
    print_block(
        tutorial_debug_preview_block(
            label=label,
            idx=idx,
            wli=wli,
            direction=direction,
            options=options or default_options(),
        )
    )


def print_model_loading(events: Sequence[LmLoadStatus], *, options: PrintOptions | None = None) -> None:
    print_block(
        format_status_block(
            "Model loading",
            model_loading_rows(events),
            options=options or default_options(),
        )
    )


def model_loading_rows(events: Sequence[LmLoadStatus]) -> list[tuple[str, object]]:
    if not events:
        return [("status", "no model assets loaded")]
    if len(events) == 1:
        event = events[0]
        return [(event.asset_type, event.asset_id), ("status", event.status)]
    return [
        (f"{event.asset_type} {index}", f"{event.asset_id} ({event.status})")
        for index, event in enumerate(events, start=1)
    ]


def print_run_progress_heading(*, options: PrintOptions | None = None) -> None:
    _ = options or default_options()
    print_block(format_section("Run progress"))


def print_summary_spacer() -> None:
    print()


def preview_text(value: Any, *, limit: int = 160) -> str:
    text = str(value)
    suffix = "..." if len(text) > limit else ""
    return f"{text[:limit]}{suffix}"


def preview_sequence(values: Sequence[Any], *, limit: int = 32) -> str:
    clipped = list(values[:limit])
    suffix = " ..." if len(values) > limit else ""
    return f"{clipped}{suffix}"


def print_result_note(
    title: str,
    rows: Mapping[str, Any] | Sequence[tuple[str, Any]],
    *,
    options: PrintOptions | None = None,
) -> None:
    print_block(format_key_value_block(title, rows, options=options or default_options()))


def _rows(rows: Mapping[str, Any] | Sequence[tuple[str, Any]]) -> list[tuple[str, Any]]:
    if isinstance(rows, Mapping):
        return list(rows.items())
    return list(rows)


__all__ = [
    "TRUTH_REFERENCE_USE",
    "default_options",
    "model_loading_rows",
    "preview_sequence",
    "preview_text",
    "print_debug_preview",
    "print_initialising",
    "print_model_loading",
    "print_preview",
    "print_problem_input",
    "print_rdp_identity",
    "print_result_note",
    "print_run_progress_heading",
    "print_summary_spacer",
    "print_tutorial_contract",
]
