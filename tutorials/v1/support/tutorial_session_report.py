from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from tutorials.v1.support.tutorial_benchmark import TutorialRunKind, TutorialStopPolicy
from tutorials.v1.support.tutorial_reference import TutorialReference
from tutorials.v1.support.tutorial_report import build_tutorial_run_report, render_tutorial_run_report


def build_tutorial_session_report(
    *,
    title: str,
    cipher: str,
    solution: Any,
    solver_report: Any = None,
    reference: TutorialReference | None = None,
    run_kind: TutorialRunKind | None = None,
    stop_policy: TutorialStopPolicy | None = None,
    match_ok: bool | None = None,
    app_version: str | None = None,
    key_idx: Sequence[int] | None = None,
    key_len: int | None = None,
    ct_idx: Sequence[int] | None = None,
    ct_rune: str | None = None,
    pt_rune_ref: str | None = None,
    pt_idx_ref: Sequence[int] | None = None,
    preview_len: int = 160,
) -> dict[str, Any]:
    benchmark_summary = None
    if reference is not None and run_kind is not None and stop_policy is not None:
        benchmark_summary = reference.build_summary(run_kind=run_kind, stop_policy=stop_policy, solution=solution)

    if reference is not None:
        if key_idx is None and reference.key_idx is not None:
            key_idx = list(reference.key_idx)
        if pt_idx_ref is None and reference.plaintext_idx is not None:
            pt_idx_ref = list(reference.plaintext_idx)

    return build_tutorial_run_report(
        title=title,
        cipher=cipher,
        solution=solution,
        solver_report=solver_report,
        benchmark_summary=benchmark_summary,
        match_ok=match_ok,
        app_version=app_version,
        key_idx=key_idx,
        key_len=key_len,
        ct_idx=ct_idx,
        ct_rune=ct_rune,
        pt_rune_ref=pt_rune_ref,
        pt_idx_ref=pt_idx_ref,
        preview_len=preview_len,
    )


def print_tutorial_session_report(**kwargs: Any) -> dict[str, Any]:
    report = build_tutorial_session_report(**kwargs)
    for line in render_tutorial_run_report(report):
        print(line)
    return report


__all__ = ["build_tutorial_session_report", "print_tutorial_session_report"]
