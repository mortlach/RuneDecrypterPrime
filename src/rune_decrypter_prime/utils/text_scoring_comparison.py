from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Device, Direction, ObjectiveFamily, ObjectiveSpec, ScorerImpl, SeMode, Stat
from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime
from rune_decrypter_prime.utils.runeglish import Runeglish

ALPHABET_SIZE = 29


@dataclass(frozen=True)
class ScoringMethod:
    name: str
    family: str  # "raw_full" | "pct"
    char_weights: Dict[int, float]
    wli_weights: Dict[int, float]
    wli_within_word: bool = False


@dataclass(frozen=True)
class ScoreRow:
    method: str
    family: str
    score_a: float
    score_b: float
    delta_a_minus_b: float


def default_scoring_methods() -> List[ScoringMethod]:
    methods: List[ScoringMethod] = []
    for n in range(1, 5):
        methods.append(
            ScoringMethod(
                name=f"raw_char_n{n}",
                family="raw_full",
                char_weights={n: 1.0},
                wli_weights={},
            )
        )
    for n in range(1, 5):
        methods.append(
            ScoringMethod(
                name=f"raw_wli_n{n}_full",
                family="raw_full",
                char_weights={},
                wli_weights={n: 1.0},
                wli_within_word=False,
            )
        )
    for n in (2, 3, 4):
        methods.append(
            ScoringMethod(
                name=f"raw_wli_n{n}_within",
                family="raw_full",
                char_weights={},
                wli_weights={n: 1.0},
                wli_within_word=True,
            )
        )
    methods.append(
        ScoringMethod(
            name="raw_combo_char34_wli12_full",
            family="raw_full",
            char_weights={3: 0.5, 4: 0.5},
            wli_weights={1: 0.5, 2: 0.5},
            wli_within_word=False,
        )
    )
    methods.append(
        ScoringMethod(
            name="raw_combo_char34_wli12_within",
            family="raw_full",
            char_weights={3: 0.5, 4: 0.5},
            wli_weights={1: 0.5, 2: 0.5},
            wli_within_word=True,
        )
    )
    for n in range(1, 5):
        methods.append(
            ScoringMethod(
                name=f"pct_char_n{n}",
                family="pct",
                char_weights={n: 1.0},
                wli_weights={},
            )
        )
    for n in range(1, 5):
        methods.append(
            ScoringMethod(
                name=f"pct_wli_n{n}",
                family="pct",
                char_weights={},
                wli_weights={n: 1.0},
            )
        )
    methods.append(
        ScoringMethod(
            name="pct_combo_char34_wli12",
            family="pct",
            char_weights={3: 0.5, 4: 0.5},
            wli_weights={1: 0.5, 2: 0.5},
        )
    )
    methods.append(
        ScoringMethod(
            name="pct_combo_char34_wli1234",
            family="pct",
            char_weights={3: 0.5, 4: 0.5},
            wli_weights={1: 0.25, 2: 0.25, 3: 0.25, 4: 0.25},
        )
    )
    return methods


def encode_text(
    text: str,
    *,
    direction: Direction,
) -> tuple[np.ndarray, List[List[int]]]:
    pt_idx, wli, _runes = Runeglish.encode_english_to_runes(text, direction=direction.value)
    pt = np.asarray(pt_idx, dtype=np.uint8).reshape(-1)
    if pt.size == 0:
        raise ValueError("Encoded text is empty. Provide non-empty alphabetic text.")
    if pt.min() < 0 or pt.max() >= ALPHABET_SIZE:
        raise ValueError("Encoded text contains symbols outside 0..28")
    wli_list = [[int(a), int(b)] for a, b in wli]
    if len(wli_list) != int(pt.size):
        raise ValueError("WLI length does not match encoded plaintext length")
    return pt, wli_list


def compare_two_texts(
    text_a: str,
    text_b: str,
    *,
    direction: Direction = Direction.LTR,
    model_root: Path | str | None = None,
    methods: Sequence[ScoringMethod] | None = None,
) -> List[ScoreRow]:
    direction = Direction(direction)
    pt_a, wli_a = encode_text(text_a, direction=direction)
    pt_b, wli_b = encode_text(text_b, direction=direction)
    if len(wli_a) != int(pt_a.size) or len(wli_b) != int(pt_b.size):
        raise ValueError("Invalid WLI stream for one or both texts")

    method_list = list(methods) if methods is not None else default_scoring_methods()
    if not method_list:
        raise ValueError("No scoring methods configured")

    lm = LanguageModelPrime(
        lm_root=Path(model_root).resolve() if model_root is not None else None,
        include_char=True,
    )
    pct_cache: Dict[Tuple[Tuple[Tuple[int, float], ...], Tuple[Tuple[int, float], ...]], object] = {}
    out: List[ScoreRow] = []

    for method in method_list:
        if method.family == "raw_full":
            scorer = RawCompositeScorer(
                lm=lm,
                direction=direction,
                char_weights=method.char_weights,
                wli_weights=method.wli_weights,
                wli_within_word=method.wli_within_word,
            )
            score_a = float(scorer.score(pt_a, wli_a))
            score_b = float(scorer.score(pt_b, wli_b))
        elif method.family == "pct":
            key = (
                tuple(sorted((int(k), float(v)) for k, v in method.char_weights.items() if float(v) > 0.0)),
                tuple(sorted((int(k), float(v)) for k, v in method.wli_weights.items() if float(v) > 0.0)),
            )
            scorer = pct_cache.get(key)
            if scorer is None:
                scorer = _build_pct_scorer(
                    direction=direction,
                    model_root=model_root,
                    char_weights=method.char_weights,
                    wli_weights=method.wli_weights,
                )
                pct_cache[key] = scorer
            use_wli = bool(method.wli_weights)
            score_a = float(scorer.score(pt_a, wli_a if use_wli else None))
            score_b = float(scorer.score(pt_b, wli_b if use_wli else None))
        else:
            raise ValueError(f"Unknown scoring family: {method.family!r}")

        out.append(
            ScoreRow(
                method=method.name,
                family=method.family,
                score_a=score_a,
                score_b=score_b,
                delta_a_minus_b=float(score_a - score_b),
            )
        )

    return out


def format_score_rows(
    rows: Sequence[ScoreRow],
    *,
    label_a: str = "text_a",
    label_b: str = "text_b",
) -> str:
    if not rows:
        return "<no rows>"
    header = [
        ("method", 34),
        ("family", 10),
        (label_a, 14),
        (label_b, 14),
        ("delta_a-b", 14),
    ]
    lines = []
    lines.append(" ".join(name.ljust(width) for name, width in header))
    lines.append(" ".join(("-" * width) for _, width in header))
    for row in rows:
        lines.append(
            " ".join(
                [
                    str(row.method).ljust(34),
                    str(row.family).ljust(10),
                    f"{row.score_a:14.6f}",
                    f"{row.score_b:14.6f}",
                    f"{row.delta_a_minus_b:14.6f}",
                ]
            )
        )
    return "\n".join(lines)


class RawCompositeScorer:
    """
    Unwindowed full-text average logp scorer over one or both channels.
    """

    def __init__(
        self,
        *,
        lm: LanguageModelPrime,
        direction: Direction,
        char_weights: Dict[int, float] | None = None,
        wli_weights: Dict[int, float] | None = None,
        wli_within_word: bool = False,
    ):
        self._lm = lm
        self._direction = direction
        self._char_weights = _normalise_weights(char_weights or {})
        self._wli_weights = _normalise_weights(wli_weights or {})
        self._wli_within_word = bool(wli_within_word)
        if not self._char_weights and not self._wli_weights:
            raise ValueError("RawCompositeScorer requires at least one active channel weight")

    def score(self, pt: Sequence[int] | np.ndarray, wli: Sequence[Sequence[int]] | None) -> float:
        pt_u8 = np.asarray(pt, dtype=np.uint8).reshape(-1)
        if pt_u8.size == 0:
            return float("-inf")
        acc = 0.0
        total_weight = 0.0

        if self._char_weights:
            acc += self._score_char(pt_u8)
            total_weight += float(sum(self._char_weights.values()))
        if self._wli_weights:
            if wli is None:
                raise ValueError("WLI is required for WLI scoring")
            wli_list = [[int(a), int(b)] for a, b in wli]
            if len(wli_list) != int(pt_u8.size):
                raise ValueError("WLI length must match plaintext length")
            acc += self._score_wli(pt_u8, wli_list)
            total_weight += float(sum(self._wli_weights.values()))

        if total_weight <= 0.0:
            return float("-inf")
        return float(acc / total_weight)

    def _score_char(self, pt_u8: np.ndarray) -> float:
        total = 0.0
        L = int(pt_u8.size)
        seq = pt_u8.tolist()
        for n, w in self._char_weights.items():
            total_eval = L - int(n) + 1
            if total_eval <= 0:
                return float("-inf")
            res = self._lm.score([seq], None, direction=self._direction.value, se="nose", n=int(n), model="char")[0]
            total += float(w) * (float(res.logprob_sum) / float(total_eval))
        return total

    def _score_wli(self, pt_u8: np.ndarray, wli: List[List[int]]) -> float:
        if not self._wli_within_word:
            return self._score_wli_full(pt_u8, wli)
        return self._score_wli_within(pt_u8, wli)

    def _score_wli_full(self, pt_u8: np.ndarray, wli: List[List[int]]) -> float:
        total = 0.0
        L = int(pt_u8.size)
        seq = pt_u8.tolist()
        for n, w in self._wli_weights.items():
            total_eval = L - int(n) + 1
            if total_eval <= 0:
                return float("-inf")
            res = self._lm.score([seq], [wli], direction=self._direction.value, se="nose", n=int(n), model="wli")[0]
            total += float(w) * (float(res.logprob_sum) / float(total_eval))
        return total

    def _score_wli_within(self, pt_u8: np.ndarray, wli: List[List[int]]) -> float:
        total = 0.0
        spans = _word_spans_from_wli(wli)
        for n, w in self._wli_weights.items():
            eval_count = 0
            logp_sum = 0.0
            for s, e in spans:
                seg_len = int(e - s)
                if seg_len < int(n):
                    continue
                pt_word = pt_u8[s:e].tolist()
                wli_word = wli[s:e]
                res = self._lm.score([pt_word], [wli_word], direction=self._direction.value, se="nose", n=int(n), model="wli")[0]
                logp_sum += float(res.logprob_sum)
                eval_count += int(seg_len - int(n) + 1)
            if eval_count <= 0:
                return float("-inf")
            total += float(w) * (logp_sum / float(eval_count))
        return total


def _normalise_weights(weights: Dict[int, float]) -> Dict[int, float]:
    out = {int(n): float(w) for n, w in weights.items() if int(n) > 0 and float(w) > 0.0}
    return out


def _word_spans_from_wli(wli: Sequence[Sequence[int]]) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    start = 0
    for i, pair in enumerate(wli):
        pos, ln = int(pair[0]), int(pair[1])
        if pos == ln - 1:
            spans.append((start, int(i) + 1))
            start = int(i) + 1
    if not spans:
        spans.append((0, len(wli)))
    return spans


def _build_pct_scorer(
    *,
    direction: Direction,
    model_root: Path | str | None,
    char_weights: Dict[int, float],
    wli_weights: Dict[int, float],
):
    char_w = _normalise_weights(char_weights)
    wli_w = _normalise_weights(wli_weights)
    include_char = bool(char_w)
    use_wli = bool(wli_w)
    if not include_char and not use_wli:
        raise ValueError("PCT scorer needs at least one active channel")

    cfg = ScoringConfig(
        model_root=Path(model_root).resolve() if model_root is not None else None,
        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
        se_mode=SeMode.NOSE,
        encoding_dir=direction,
        include_char=include_char,
        use_word_breaks=use_wli,
        char_weights=char_w,
        wli_weights=wli_w,
        impl=ScorerImpl.NUMPY,
    )
    dummy = CipherConfig(
        name="periodic_columnar",
        ciphertext=[],
        wli_data=[],
        key_length=1,
        alphabet_size=ALPHABET_SIZE,
        period=1,
        columns=1,
        order="col_then_sub",
        encoding_dir=direction,
        device=Device.CPU,
    )
    return build_scorer(dummy, cfg)
