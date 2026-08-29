from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from rune_decrypter_prime.core.types import Direction, ensure_direction
from rune_decrypter_prime.scoring.span_hamming.types import SpanInterval
from rune_decrypter_prime.scoring.word_ngrams.scorer import (
    RuneTokenWordNgramScorer,
    summarize_prefix_total_confidence,
    summarize_word_ngram_report_trust,
    word_ngram_report_is_active,
)
from rune_decrypter_prime.scoring.word_ngrams.sqlite_model import RuneTokenWordNgramSqlite


@dataclass(frozen=True)
class ExactMatchToken:
    start: int
    end: int
    length: int
    token: bytes


@dataclass(frozen=True)
class RuneTokenWordNgramJudgeReport:
    available: bool
    active: bool
    inactive_reason: str | None
    exact_word_count: int
    segment_count: int
    xent_3: float | None
    xent_backoff_5_4_3: float | None
    n_positions: int
    miss_rate: float | None
    used5_rate: float | None
    used4_rate: float | None
    used3_rate: float | None
    prefix_total_mean: float
    prefix_total_min: float
    prefix_total_ge_1_rate: float
    prefix_total_ge_10_rate: float
    prefix_total_ge_100_rate: float
    trust_score: float
    trust_tier: str


def token_bytes_from_indices(seq: Sequence[int]) -> bytes:
    return bytes(int(v) for v in seq)


def extract_exact_match_tokens(
    text_idx: Sequence[int],
    intervals: Sequence[SpanInterval],
) -> tuple[ExactMatchToken, ...]:
    values = tuple(int(v) for v in text_idx)
    chosen = [
        item
        for item in intervals
        if int(item.distance) == 0 and 0 <= int(item.start) < int(item.end) <= len(values)
    ]
    chosen.sort(key=lambda item: (int(item.start), int(item.end), int(item.length)))
    out: list[ExactMatchToken] = []
    for item in chosen:
        start = int(item.start)
        end = int(item.end)
        out.append(
            ExactMatchToken(
                start=start,
                end=end,
                length=int(item.length),
                token=token_bytes_from_indices(values[start:end]),
            )
        )
    return tuple(out)


def segment_exact_match_tokens(
    tokens: Sequence[ExactMatchToken],
) -> tuple[tuple[ExactMatchToken, ...], ...]:
    if not tokens:
        return tuple()
    ordered = sorted(tokens, key=lambda item: (int(item.start), int(item.end), int(item.length)))
    segments: list[list[ExactMatchToken]] = [[ordered[0]]]
    for item in ordered[1:]:
        prev = segments[-1][-1]
        if int(item.start) == int(prev.end):
            segments[-1].append(item)
        else:
            segments.append([item])
    return tuple(tuple(seg) for seg in segments)


def _segment_token_bytes(
    segments: Sequence[Sequence[ExactMatchToken]],
    *,
    direction: Direction,
) -> tuple[tuple[bytes, ...], ...]:
    out: list[tuple[bytes, ...]] = []
    if direction is Direction.RTL:
        ordered_segments = list(reversed(segments))
        for seg in ordered_segments:
            out.append(tuple(tok.token for tok in reversed(seg)))
    else:
        for seg in segments:
            out.append(tuple(tok.token for tok in seg))
    return tuple(out)


class RuneTokenWordNgramJudgeRuntime:
    def __init__(
        self,
        *,
        sqlite_model: RuneTokenWordNgramSqlite,
        scorer: RuneTokenWordNgramScorer,
        min_positions: int,
        prefix_total_thresholds: Sequence[int],
    ) -> None:
        self.sqlite_model = sqlite_model
        self.scorer = scorer
        self.min_positions = int(min_positions)
        self.prefix_total_thresholds = tuple(int(v) for v in prefix_total_thresholds)

    @classmethod
    def open_sqlite(
        cls,
        path: str | Path,
        *,
        alpha: float,
        miss_logp: float,
        min_positions: int,
        prefix_total_thresholds: Sequence[int],
    ) -> "RuneTokenWordNgramJudgeRuntime":
        sqlite_model = RuneTokenWordNgramSqlite.open(path)
        scorer = RuneTokenWordNgramScorer(
            sqlite_model,
            alpha=float(alpha),
            miss_logp=float(miss_logp),
        )
        return cls(
            sqlite_model=sqlite_model,
            scorer=scorer,
            min_positions=int(min_positions),
            prefix_total_thresholds=tuple(int(v) for v in prefix_total_thresholds),
        )

    def close(self) -> None:
        self.sqlite_model.close()

    def score_candidate(
        self,
        *,
        text_idx: Sequence[int],
        selected_intervals: Sequence[SpanInterval],
        direction: Direction | str,
    ) -> RuneTokenWordNgramJudgeReport:
        dir_enum = ensure_direction(direction)
        tokens = extract_exact_match_tokens(text_idx, selected_intervals)
        segments = segment_exact_match_tokens(tokens)
        token_segments = _segment_token_bytes(segments, direction=dir_enum)
        diag = self.scorer.score_segments_with_diagnostics(token_segments)
        score = diag.score
        support = summarize_prefix_total_confidence(
            diag.prefix_totals_3,
            thresholds=self.prefix_total_thresholds,
        )
        active = word_ngram_report_is_active(
            n_positions=int(score.n_positions),
            min_positions=int(self.min_positions),
        )
        trust = summarize_word_ngram_report_trust(
            n_positions=int(score.n_positions),
            min_positions=int(self.min_positions),
            prefix_total_ge_10_rate=float(support.get("prefix_total_ge_10_rate", 0.0)),
            prefix_total_ge_100_rate=float(support.get("prefix_total_ge_100_rate", 0.0)),
        )
        inactive_reason = None
        if int(score.n_positions) <= 0:
            inactive_reason = "no_positions"
        elif not active:
            inactive_reason = "min_positions_not_met"
        return RuneTokenWordNgramJudgeReport(
            available=True,
            active=bool(active),
            inactive_reason=inactive_reason,
            exact_word_count=int(len(tokens)),
            segment_count=int(len(segments)),
            xent_3=(None if int(score.n_positions) <= 0 else float(score.xent_3)),
            xent_backoff_5_4_3=(
                None if int(score.n_positions) <= 0 else float(score.xent_backoff_5_4_3)
            ),
            n_positions=int(score.n_positions),
            miss_rate=(None if int(score.n_positions) <= 0 else float(score.miss_rate)),
            used5_rate=(None if int(score.n_positions) <= 0 else float(score.used5_rate)),
            used4_rate=(None if int(score.n_positions) <= 0 else float(score.used4_rate)),
            used3_rate=(None if int(score.n_positions) <= 0 else float(score.used3_rate)),
            prefix_total_mean=float(support.get("prefix_total_mean", 0.0)),
            prefix_total_min=float(support.get("prefix_total_min", 0.0)),
            prefix_total_ge_1_rate=float(support.get("prefix_total_ge_1_rate", 0.0)),
            prefix_total_ge_10_rate=float(support.get("prefix_total_ge_10_rate", 0.0)),
            prefix_total_ge_100_rate=float(support.get("prefix_total_ge_100_rate", 0.0)),
            trust_score=float(trust.trust_score),
            trust_tier=str(trust.trust_tier),
        )


__all__ = [
    "ExactMatchToken",
    "RuneTokenWordNgramJudgeReport",
    "RuneTokenWordNgramJudgeRuntime",
    "extract_exact_match_tokens",
    "segment_exact_match_tokens",
    "token_bytes_from_indices",
]
