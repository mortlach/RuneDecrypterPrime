from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

import numpy as np

from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer


@dataclass(frozen=True)
class StopScoreResult:
    oracle_score: Optional[float]
    stop_score: Optional[float]
    reason: str


def score_plaintext(
    pt_idx: Iterable[int],
    wli: Optional[Iterable[Iterable[int]]],
    scorer_params: Dict[str, Any],
    *,
    device: str = "cpu",
    encoding_dir=None,
) -> float:
    """Score plaintext with the same scorer settings used by the tutorial."""
    pt_arr = np.asarray(list(pt_idx), dtype=np.uint8)
    c_cfg = CipherConfig(
        ciphertext=pt_arr,
        wli_data=wli,
        key_length=None,
        device=device,
        encoding_dir=encoding_dir,
    )
    s_cfg = ScoringConfig(**scorer_params)
    scorer = build_scorer(c_cfg, s_cfg)
    return float(scorer.score(pt_arr, wli))


def oracle_stop_score(
    pt_idx: Iterable[int],
    wli: Optional[Iterable[Iterable[int]]],
    scorer_params: Dict[str, Any],
    *,
    device: str = "cpu",
    encoding_dir=None,
    margin: float = 0.02,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    fallback: Optional[float] = None,
) -> StopScoreResult:
    """Compute a stop_score from oracle plaintext score (with safe fallback)."""
    try:
        oracle = score_plaintext(pt_idx, wli, scorer_params, device=device, encoding_dir=encoding_dir)
    except FileNotFoundError as exc:  # keep tutorials runnable even if LM assets are absent
        return StopScoreResult(None, fallback, f"oracle_failed: {exc}")

    stop = float(oracle - float(margin))
    # Never allow stop_score to exceed the oracle score.
    cap = float(oracle) - 1e-6
    if min_score is not None:
        stop = max(stop, float(min_score))
    stop = min(stop, cap)
    if max_score is not None:
        stop = min(stop, float(max_score))
    return StopScoreResult(oracle, stop, "oracle_ok")


def plateau_rounds_from_steps(steps: int, *, pct: float = 0.1, minimum: int = 10) -> int:
    return max(minimum, int(max(1, steps) * pct))


def print_stop_summary(label: str, result: StopScoreResult) -> None:
    if result.oracle_score is None:
        print(f"[{label}] stop_score fallback={result.stop_score} ({result.reason})")
    else:
        print(
            f"[{label}] oracle_score={result.oracle_score:.6f} stop_score={result.stop_score:.6f} ({result.reason})"
        )
