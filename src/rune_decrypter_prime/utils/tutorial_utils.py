from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np

from rdp.api.display import PrintOptions, format_key_value_block, print_block
from rdp.core.config.cipher import CipherConfig
from rdp.core.config.scoring import ScoringConfig
from rdp.core.types import Direction, TextDirection
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.scoring.language_model.load_status import LmLoadReporter, LmLoadStatus
from rune_decrypter_prime.utils.tutorial_pretty import print_model_loading


@dataclass(frozen=True)
class StopScoreResult:
    oracle_score: Optional[float]
    stop_score: Optional[float]
    reason: str
    load_events: tuple[LmLoadStatus, ...] = ()


def score_plaintext(
    pt_idx: Iterable[int],
    wli: Optional[Iterable[Iterable[int]]],
    scorer_params: ScoringConfig,
    *,
    device: str = "cpu",
    encoding_dir=None,
    load_reporter: LmLoadReporter | None = None,
) -> float:
    """Score plaintext with the same scorer settings used by the tutorial."""
    pt_arr = np.asarray(list(pt_idx), dtype=np.uint8)
    runtime_direction = (
        Direction.LTR
        if encoding_dir is TextDirection.LEFT_TO_RIGHT
        else Direction.RTL
        if encoding_dir is TextDirection.RIGHT_TO_LEFT
        else encoding_dir
    )
    c_cfg = CipherConfig(
        ciphertext=pt_arr,
        wli_data=wli,
        key_length=None,
        device=device,
        encoding_dir=runtime_direction,
    )
    if not isinstance(scorer_params, ScoringConfig):
        raise TypeError("scorer_params must be ScoringConfig")
    scorer = build_scorer(c_cfg, scorer_params)
    return float(scorer.score(pt_arr, wli))


def oracle_stop_score(
    pt_idx: Iterable[int],
    wli: Optional[Iterable[Iterable[int]]],
    scorer_params: ScoringConfig,
    *,
    device: str = "cpu",
    encoding_dir=None,
    margin: float = 0.02,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    fallback: Optional[float] = None,
    load_reporter: LmLoadReporter | None = None,
) -> StopScoreResult:
    """Compute a stop_score from oracle plaintext score (with safe fallback)."""
    load_events: list[LmLoadStatus] = []

    def _report_load(event: LmLoadStatus) -> None:
        load_events.append(event)
        if load_reporter is not None:
            load_reporter(event)

    try:
        oracle = score_plaintext(
            pt_idx,
            wli,
            scorer_params,
            device=device,
            encoding_dir=encoding_dir,
            load_reporter=_report_load,
        )
    except FileNotFoundError as exc:  # keep tutorials runnable even if LM assets are absent
        return StopScoreResult(None, fallback, f"oracle_failed: {exc}", tuple(load_events))

    stop = float(oracle - float(margin))
    # Never allow stop_score to exceed the oracle score.
    cap = float(oracle) - 1e-6
    if min_score is not None:
        stop = max(stop, float(min_score))
    stop = min(stop, cap)
    if max_score is not None:
        stop = min(stop, float(max_score))
    return StopScoreResult(oracle, stop, "oracle_ok", tuple(load_events))


def plateau_rounds_from_steps(steps: int, *, pct: float = 0.1, minimum: int = 10) -> int:
    return max(minimum, int(max(1, steps) * pct))


def stop_summary_rows(label: str, result: StopScoreResult) -> list[tuple[str, object]]:
    return [
        ("label", label),
        ("oracle_score", result.oracle_score),
        ("stop_score", result.stop_score),
        ("status", result.reason),
    ]


def format_stop_summary(
    label: str,
    result: StopScoreResult,
    *,
    options: PrintOptions | None = None,
) -> str:
    return format_key_value_block("Scoring / stop target", stop_summary_rows(label, result), options=options)


def print_stop_summary(label: str, result: StopScoreResult) -> None:
    print_model_loading(result.load_events)
    print_block(format_stop_summary(label, result))
