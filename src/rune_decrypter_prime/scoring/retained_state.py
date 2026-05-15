from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping

import numpy as np

from rune_decrypter_prime.core.types import Direction, ensure_direction
from rune_decrypter_prime.scoring.scorer_report import ScorerReport
from rune_decrypter_prime.scoring.scorer_report_builder import build_scorer_report


def _int_token(value: Any, *, field_name: str) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{field_name} must be an integer token, not bool")
    if not isinstance(value, (int, np.integer)):
        raise TypeError(f"{field_name} must be an integer token")
    token = int(value)
    if token < 0 or token > 28:
        raise ValueError(f"{field_name} must be in [0..28]")
    return token


def _int_wli_value(value: Any, *, field_name: str) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{field_name} must be an integer, not bool")
    if not isinstance(value, (int, np.integer)):
        raise TypeError(f"{field_name} must be an integer")
    return int(value)


def _normalize_plaintext_idx(value: Iterable[Any]) -> tuple[int, ...]:
    try:
        raw = value.tolist() if hasattr(value, "tolist") else value
        return tuple(_int_token(item, field_name=f"plaintext_idx[{idx}]") for idx, item in enumerate(raw))
    except (TypeError, ValueError):
        raise
    except Exception as exc:
        raise TypeError("plaintext_idx must be an iterable of integer tokens") from exc


def _normalize_wli(
    value: Iterable[Iterable[Any]] | None,
    *,
    expected_len: int,
) -> tuple[tuple[int, int], ...] | None:
    if value is None:
        return None
    raw = value.tolist() if hasattr(value, "tolist") else value
    out: list[tuple[int, int]] = []
    try:
        for idx, pair in enumerate(raw):
            pair_raw = pair.tolist() if hasattr(pair, "tolist") else pair
            if not isinstance(pair_raw, (list, tuple)) or len(pair_raw) != 2:
                raise TypeError(f"wli[{idx}] must be a (pos_in_word, word_len) pair")
            pos = _int_wli_value(pair_raw[0], field_name=f"wli[{idx}][0]")
            word_len = _int_wli_value(pair_raw[1], field_name=f"wli[{idx}][1]")
            if pos < 0:
                raise ValueError("wli pos_in_word must be >= 0")
            if word_len <= 0:
                raise ValueError("wli word_len must be > 0")
            if pos >= word_len:
                raise ValueError("wli pos_in_word must be < word_len")
            out.append((pos, word_len))
    except (TypeError, ValueError):
        raise
    except Exception as exc:
        raise TypeError("wli must be an iterable of (pos_in_word, word_len) pairs") from exc
    if len(out) != int(expected_len):
        raise ValueError("wli length must match plaintext_idx length")
    return tuple(out)


@dataclass(frozen=True, slots=True, init=False)
class PlaintextRetainedCandidate:
    candidate_representation: Literal["plaintext_idx"]
    plaintext_idx: tuple[int, ...]
    wli: tuple[tuple[int, int], ...] | None
    alphabet: str
    direction: Direction
    tokenization: str
    candidate_id: str | None

    def __init__(
        self,
        plaintext_idx: Iterable[Any],
        wli: Iterable[Iterable[Any]] | None = None,
        *,
        candidate_representation: Literal["plaintext_idx"] = "plaintext_idx",
        alphabet: str = "runic-29",
        direction: Direction | str = Direction.RTL,
        tokenization: str = "runeglish-pos29",
        candidate_id: str | None = None,
    ) -> None:
        if candidate_representation != "plaintext_idx":
            raise ValueError('candidate_representation must be "plaintext_idx"')
        pt = _normalize_plaintext_idx(plaintext_idx)
        norm_wli = _normalize_wli(wli, expected_len=len(pt))
        object.__setattr__(self, "candidate_representation", "plaintext_idx")
        object.__setattr__(self, "plaintext_idx", pt)
        object.__setattr__(self, "wli", norm_wli)
        object.__setattr__(self, "alphabet", str(alphabet))
        object.__setattr__(self, "direction", ensure_direction(direction))
        object.__setattr__(self, "tokenization", str(tokenization))
        object.__setattr__(self, "candidate_id", None if candidate_id is None else str(candidate_id))


def score_plaintext_candidate(
    candidate: PlaintextRetainedCandidate,
    scorer: Any,
    *,
    objective_str: str = "",
    raw_score: float | None = None,
    cost_ms: float | None = None,
    extra_metrics: Mapping[str, float] | None = None,
    extra_details: Mapping[str, Any] | None = None,
) -> ScorerReport:
    if not isinstance(candidate, PlaintextRetainedCandidate):
        raise TypeError("candidate must be a PlaintextRetainedCandidate")
    if not hasattr(scorer, "score") or not callable(scorer.score):
        raise TypeError("scorer must provide score(plaintext, wli)")

    score = float(scorer.score(candidate.plaintext_idx, candidate.wli))
    return build_scorer_report(
        scorer=scorer,
        objective_str=objective_str,
        score=score,
        raw_score=raw_score,
        cost_ms=cost_ms,
        extra_metrics=extra_metrics,
        extra_details=extra_details,
    )
