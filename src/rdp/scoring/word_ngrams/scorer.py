from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol, Sequence

from rdp.scoring.word_ngrams.sqlite_model import make_prefix_key, make_token_ngram_key


class RuneTokenWordNgramCounts(Protocol):
    def get_ngram_count(self, n: int, key: bytes) -> int: ...

    def get_prefix_total(self, n_minus_1: int, prefix: bytes) -> int: ...


@dataclass(frozen=True)
class RuneTokenWordNgramScore:
    xent_3: float
    xent_backoff_5_4_3: float
    used5_rate: float
    used4_rate: float
    used3_rate: float
    miss_rate: float
    n_positions: int


@dataclass(frozen=True)
class RuneTokenWordNgramDiagnostics:
    score: RuneTokenWordNgramScore
    prefix_totals_3: tuple[int, ...]


@dataclass(frozen=True)
class RuneTokenWordNgramReportTrust:
    active: bool
    trust_score: float
    trust_tier: str


class RuneTokenWordNgramScorer:
    """
    Rune-token word sequence judge.

    This scorer is designed for top-K / judge usage, not inner-loop search.
    The token space is `bytes` where each token is the rune-index encoding of a
    word. Runtime extraction of those tokens is intentionally kept outside this
    module.
    """

    def __init__(
        self,
        model: RuneTokenWordNgramCounts,
        *,
        alpha: float = 0.4,
        miss_logp: float = -20.0,
    ) -> None:
        self.model = model
        self.alpha = float(alpha)
        self.miss_logp = float(miss_logp)
        if not (0.0 < self.alpha <= 1.0):
            raise ValueError("alpha must be in (0, 1]")

    def _cond_logp(self, *, n: int, tokens: Sequence[bytes]) -> float | None:
        if len(tokens) != int(n):
            raise ValueError("tokens length must match n")
        key = make_token_ngram_key(tuple(tokens))
        prefix = make_prefix_key(tuple(tokens[:-1]))
        count = self.model.get_ngram_count(int(n), key)
        total = self.model.get_prefix_total(int(n) - 1, prefix)
        if count <= 0 or total <= 0:
            return None
        return float(math.log(count / total))

    def _prefix_total(self, *, n_minus_1: int, tokens: Sequence[bytes]) -> int:
        if len(tokens) != int(n_minus_1):
            raise ValueError("tokens length must match n_minus_1")
        prefix = make_prefix_key(tuple(tokens))
        return int(self.model.get_prefix_total(int(n_minus_1), prefix))

    def _score_backoff_position(self, tokens: Sequence[bytes], idx: int) -> tuple[float, int] | None:
        if idx >= 4:
            lp5 = self._cond_logp(n=5, tokens=tokens[idx - 4 : idx + 1])
            if lp5 is not None:
                return float(lp5), 5
        if idx >= 3:
            lp4 = self._cond_logp(n=4, tokens=tokens[idx - 3 : idx + 1])
            if lp4 is not None:
                if idx >= 4:
                    return float(math.log(self.alpha) + lp4), 4
                return float(lp4), 4
        if idx >= 2:
            lp3 = self._cond_logp(n=3, tokens=tokens[idx - 2 : idx + 1])
            if lp3 is not None:
                if idx >= 4:
                    return float((2.0 * math.log(self.alpha)) + lp3), 3
                if idx >= 3:
                    return float(math.log(self.alpha) + lp3), 3
                return float(lp3), 3
        return None

    def score_segments_with_diagnostics(
        self,
        segments: Sequence[Sequence[bytes]],
    ) -> RuneTokenWordNgramDiagnostics:
        logps_3: list[float] = []
        logps_backoff: list[float] = []
        prefix_totals_3: list[int] = []
        used5 = 0
        used4 = 0
        used3 = 0
        miss = 0
        n_positions = 0

        for seg in segments:
            tokens = [bytes(tok) for tok in seg]
            for idx in range(2, len(tokens)):
                lp3 = self._cond_logp(n=3, tokens=tokens[idx - 2 : idx + 1])
                prefix_totals_3.append(
                    self._prefix_total(n_minus_1=2, tokens=tokens[idx - 2 : idx])
                )
                n_positions += 1
                if lp3 is None:
                    logps_3.append(float(self.miss_logp))
                else:
                    logps_3.append(float(lp3))

                hit = self._score_backoff_position(tokens, idx)
                if hit is None:
                    miss += 1
                    logps_backoff.append(float(self.miss_logp))
                else:
                    lp, order = hit
                    logps_backoff.append(float(lp))
                    if order == 5:
                        used5 += 1
                    elif order == 4:
                        used4 += 1
                    else:
                        used3 += 1

        if n_positions <= 0:
            return RuneTokenWordNgramDiagnostics(
                score=RuneTokenWordNgramScore(
                    xent_3=0.0,
                    xent_backoff_5_4_3=0.0,
                    used5_rate=0.0,
                    used4_rate=0.0,
                    used3_rate=0.0,
                    miss_rate=0.0,
                    n_positions=0,
                ),
                prefix_totals_3=(),
            )

        denom = float(n_positions)
        return RuneTokenWordNgramDiagnostics(
            score=RuneTokenWordNgramScore(
                xent_3=float(-sum(logps_3) / denom),
                xent_backoff_5_4_3=float(-sum(logps_backoff) / denom),
                used5_rate=float(used5 / denom),
                used4_rate=float(used4 / denom),
                used3_rate=float(used3 / denom),
                miss_rate=float(miss / denom),
                n_positions=int(n_positions),
            ),
            prefix_totals_3=tuple(int(v) for v in prefix_totals_3),
        )

    def score_segments(self, segments: Sequence[Sequence[bytes]]) -> RuneTokenWordNgramScore:
        return self.score_segments_with_diagnostics(segments).score


def summarize_prefix_total_confidence(
    prefix_totals: Sequence[int],
    *,
    thresholds: Sequence[int],
) -> dict[str, float]:
    vals = [int(v) for v in prefix_totals]
    if not vals:
        out = {
            "prefix_total_mean": 0.0,
            "prefix_total_min": 0.0,
        }
        for thr in thresholds:
            out[f"prefix_total_ge_{int(thr)}_rate"] = 0.0
        return out

    denom = float(len(vals))
    out = {
        "prefix_total_mean": float(sum(vals) / denom),
        "prefix_total_min": float(min(vals)),
    }
    for thr in thresholds:
        thr_i = int(thr)
        out[f"prefix_total_ge_{thr_i}_rate"] = float(
            sum(1 for v in vals if int(v) >= thr_i) / denom
        )
    return out


def word_ngram_report_is_active(
    *,
    n_positions: int,
    min_positions: int,
) -> bool:
    return int(n_positions) >= int(min_positions)


def summarize_word_ngram_report_trust(
    *,
    n_positions: int,
    min_positions: int,
    prefix_total_ge_10_rate: float,
    prefix_total_ge_100_rate: float,
) -> RuneTokenWordNgramReportTrust:
    active = word_ngram_report_is_active(
        n_positions=int(n_positions),
        min_positions=int(min_positions),
    )
    if not active:
        return RuneTokenWordNgramReportTrust(
            active=False,
            trust_score=0.0,
            trust_tier="inactive",
        )

    ge10 = float(max(0.0, min(1.0, prefix_total_ge_10_rate)))
    ge100 = float(max(0.0, min(1.0, prefix_total_ge_100_rate)))
    trust_score = float((0.5 * ge10) + (0.5 * ge100))
    if trust_score >= 0.5:
        tier = "strong"
    elif trust_score >= 0.25:
        tier = "medium"
    else:
        tier = "weak"
    return RuneTokenWordNgramReportTrust(
        active=True,
        trust_score=trust_score,
        trust_tier=tier,
    )


__all__ = [
    "RuneTokenWordNgramCounts",
    "RuneTokenWordNgramDiagnostics",
    "RuneTokenWordNgramReportTrust",
    "RuneTokenWordNgramScore",
    "RuneTokenWordNgramScorer",
    "summarize_prefix_total_confidence",
    "summarize_word_ngram_report_trust",
    "word_ngram_report_is_active",
]
