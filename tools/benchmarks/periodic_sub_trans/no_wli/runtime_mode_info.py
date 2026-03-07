from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class RunModeInfo:
    mode_raw: str
    mode_canonical: str
    intent: str
    stage3_can_skip: bool
    adaptive_focus: bool


def canonical_run_mode(mode: str | None) -> str:
    m = str(mode or "").strip().lower()
    if m == "scan_p5_p7_c1357":
        return "adaptive_scan_v1"
    return m


def mode_intent(mode: str | None, *, scan_modes: FrozenSet[str]) -> str:
    return "scan" if canonical_run_mode(mode) in scan_modes else "focus"


def mode_stage3_can_skip(mode: str | None, *, scan_modes: FrozenSet[str]) -> bool:
    return bool(canonical_run_mode(mode) in scan_modes)


def is_adaptive_focus_mode(
    mode: str | None,
    *,
    adaptive_focus_modes: FrozenSet[str],
) -> bool:
    return bool(canonical_run_mode(mode) in adaptive_focus_modes)


def build_run_mode_info(
    mode: str | None,
    *,
    scan_modes: FrozenSet[str],
    adaptive_focus_modes: FrozenSet[str],
) -> RunModeInfo:
    raw = str(mode or "")
    canonical = canonical_run_mode(raw)
    return RunModeInfo(
        mode_raw=raw,
        mode_canonical=canonical,
        intent=mode_intent(canonical, scan_modes=scan_modes),
        stage3_can_skip=mode_stage3_can_skip(canonical, scan_modes=scan_modes),
        adaptive_focus=is_adaptive_focus_mode(
            canonical, adaptive_focus_modes=adaptive_focus_modes
        ),
    )
