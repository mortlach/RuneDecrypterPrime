from __future__ import annotations

"""Deterministic candidate-word lists for WP6 Experiment B.

The search-visible list contains plausible selected eight-rune words and stable
branch IDs, but no field marks the benchmark word or its position.  The true
branch is identified only after a complete search and replay pass.
"""

import csv
import hashlib
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Sequence

from rune_decrypter_prime.scoring.hamming.loader import default_hamming_dir
from rune_decrypter_prime.utils.runeglish import Runeglish

from cipher_development.two_period_overlay.config import (
    ALPHABET_SIZE,
    DORMOUSE_RUNES,
    DORMOUSE_WORD,
    CribSpec,
    BenchmarkSpec,
)

_WORD_RE = re.compile(r"^[a-z][a-z'-]*$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _frequency(row: Sequence[str]) -> float | None:
    # The current raw1grams files place the useful frequency-like value near
    # the front.  Be tolerant of old/export variants while keeping the rule
    # deterministic.
    for token in (row[1:2] + row[4:]):
        if token is None:
            continue
        text = str(token).strip().replace(",", "")
        try:
            value = float(text)
        except ValueError:
            continue
        if math.isfinite(value) and value >= 0.0:
            return value
    return None


def _branch_id(runes: Sequence[int]) -> str:
    data = bytes(int(value) for value in runes)
    return "branch_" + hashlib.blake2b(
        data, digest_size=8, person=b"rdp-bword-v1"
    ).hexdigest()


def _order_key(seed: int, runes: Sequence[int]) -> str:
    payload = seed.to_bytes(8, "big", signed=False) + bytes(int(value) for value in runes)
    return hashlib.blake2b(payload, digest_size=16, person=b"rdp-blist-v1").hexdigest()


@dataclass(frozen=True, slots=True)
class CandidateWord:
    branch_id: str
    word: str
    runes: tuple[int, ...]
    frequency: float | None
    source_file: str
    source_row: int
    source_selected: bool

    def __post_init__(self) -> None:
        word = self.word.strip().lower()
        runes = tuple(int(value) for value in self.runes)
        if not _WORD_RE.fullmatch(word):
            raise ValueError("candidate word must be a simple lowercase English token")
        if len(runes) != 8:
            raise ValueError("candidate word must encode to exactly eight runes")
        if any(value < 0 or value >= ALPHABET_SIZE for value in runes):
            raise ValueError("candidate rune sequence contains an invalid symbol")
        if self.branch_id != _branch_id(runes):
            raise ValueError("branch_id does not match the rune sequence")
        if self.frequency is not None:
            value = float(self.frequency)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError("frequency must be non-negative and finite")
            object.__setattr__(self, "frequency", value)
        if self.source_row < 0:
            raise ValueError("source_row must be non-negative")
        object.__setattr__(self, "word", word)
        object.__setattr__(self, "runes", runes)

    def public_json(self) -> dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "word": self.word,
            "runes": list(self.runes),
            "rune_length": len(self.runes),
            "frequency": self.frequency,
            "source_file": self.source_file,
            "source_row": self.source_row,
            "source_selected": self.source_selected,
        }


@dataclass(frozen=True, slots=True)
class CandidateListBundle:
    source_dir: Path
    source_files: tuple[dict[str, Any], ...]
    candidates_10: tuple[CandidateWord, ...]
    candidates_100: tuple[CandidateWord, ...]
    candidates_1000: tuple[CandidateWord, ...]
    required_occurred_naturally: bool

    def public_payload(self, size: int) -> dict[str, Any]:
        if size == 10:
            candidates = self.candidates_10
        elif size == 100:
            candidates = self.candidates_100
        elif size == 1000:
            candidates = self.candidates_1000
        else:
            raise ValueError("candidate list size must be 10, 100 or 1000")
        return {
            "schema": "rdp.two_period_overlay.candidate_word_list.v1",
            "list_id": f"b{size}",
            "candidate_count": len(candidates),
            "normalisation": {
                "encoding_direction": "ltr",
                "require_selected": True,
                "required_rune_length": 8,
                "duplicate_policy": "one representative per distinct rune sequence",
                "representative_policy": "highest frequency then lexical word",
                "decoy_policy": "nearest log-frequency to controlled word then deterministic hash order",
            },
            "asset_files": list(self.source_files),
            "candidates": [item.public_json() for item in candidates],
        }


def _encode_word(word: str) -> tuple[int, ...] | None:
    try:
        values, _, _ = Runeglish.encode_english_to_runes(word, direction="ltr")
    except Exception:
        return None
    runes = tuple(int(value) for value in values)
    return runes if len(runes) == 8 else None


@lru_cache(maxsize=4)
def load_selected_eight_rune_words(wordlist_dir: str | Path | None = None) -> tuple[
    tuple[CandidateWord, ...], tuple[dict[str, Any], ...]
]:
    base = Path(default_hamming_dir() if wordlist_dir is None else wordlist_dir).resolve()
    files = tuple(sorted(base.glob("raw1grams_*.csv")))
    if not files:
        raise FileNotFoundError(f"no raw1grams_*.csv files found under {base}")

    by_runes: dict[tuple[int, ...], CandidateWord] = {}
    file_records: list[dict[str, Any]] = []
    for path in files:
        file_records.append({
            "name": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })
        with path.open("r", encoding="utf-8", newline="") as stream:
            for row_index, row in enumerate(csv.reader(stream), start=1):
                if len(row) < 5:
                    continue
                word = (row[0] or "").strip().lower()
                selected = (row[2] or "").strip() == "1"
                if not selected or not _WORD_RE.fullmatch(word):
                    continue
                runes = _encode_word(word)
                if runes is None:
                    continue
                # Cross-check the stored rune field when it is parseable.  A
                # disagreement is excluded rather than silently normalised.
                try:
                    stored = tuple(int(value) for value in Runeglish.rune_to_pos(row[3]))
                except Exception:
                    continue
                if stored != runes:
                    continue
                candidate = CandidateWord(
                    branch_id=_branch_id(runes),
                    word=word,
                    runes=runes,
                    frequency=_frequency(row),
                    source_file=path.name,
                    source_row=row_index,
                    source_selected=True,
                )
                prior = by_runes.get(runes)
                if prior is None:
                    by_runes[runes] = candidate
                    continue
                prior_frequency = -1.0 if prior.frequency is None else prior.frequency
                candidate_frequency = -1.0 if candidate.frequency is None else candidate.frequency
                if (
                    candidate_frequency > prior_frequency
                    or (
                        candidate_frequency == prior_frequency
                        and candidate.word < prior.word
                    )
                ):
                    by_runes[runes] = candidate

    if len(by_runes) < 1000:
        raise RuntimeError(
            f"selected word assets supplied only {len(by_runes)} distinct eight-rune sequences"
        )
    return tuple(by_runes[key] for key in sorted(by_runes)), tuple(file_records)


def build_nested_candidate_lists(
    wordlist_dir: str | Path | None = None,
    *,
    ordering_seed: int = 404,
) -> CandidateListBundle:
    candidates, file_records = load_selected_eight_rune_words(wordlist_dir)
    required_runes = tuple(int(value) for value in DORMOUSE_RUNES)
    by_runes = {item.runes: item for item in candidates}
    required = by_runes.get(required_runes)
    occurred_naturally = required is not None

    observed_frequencies = sorted(
        item.frequency for item in candidates if item.frequency is not None
    )
    fallback_frequency = (
        observed_frequencies[len(observed_frequencies) // 2]
        if observed_frequencies
        else 1.0
    )
    if required is None:
        required = CandidateWord(
            branch_id=_branch_id(required_runes),
            word=DORMOUSE_WORD,
            runes=required_runes,
            frequency=fallback_frequency,
            source_file="controlled_insertion",
            source_row=0,
            source_selected=True,
        )

    target_frequency = required.frequency
    if target_frequency is None:
        target_frequency = fallback_frequency
    target_log = math.log1p(target_frequency)

    decoys = [item for item in candidates if item.runes != required_runes]
    decoys.sort(key=lambda item: (
        abs(math.log1p(item.frequency if item.frequency is not None else fallback_frequency) - target_log),
        _order_key(ordering_seed, item.runes),
        item.word,
    ))
    selected_decoys = decoys[:999]
    if len(selected_decoys) != 999:
        raise RuntimeError("could not construct 999 distinct eight-rune decoys")

    master = [required, *selected_decoys]
    master.sort(key=lambda item: (_order_key(ordering_seed + 100, item.runes), item.word))
    b1000 = tuple(master)

    b100_members = {required.runes, *(item.runes for item in selected_decoys[:99])}
    b100 = tuple(item for item in b1000 if item.runes in b100_members)
    b10_members = {required.runes, *(item.runes for item in selected_decoys[:9])}
    b10 = tuple(item for item in b1000 if item.runes in b10_members)
    if len(b10) != 10 or len(b100) != 100 or len(b1000) != 1000:
        raise RuntimeError("nested candidate list construction produced the wrong size")
    if len({item.runes for item in b1000}) != 1000:
        raise RuntimeError("candidate list contains duplicate rune branches")

    base = Path(default_hamming_dir() if wordlist_dir is None else wordlist_dir).resolve()
    return CandidateListBundle(
        source_dir=base,
        source_files=file_records,
        candidates_10=b10,
        candidates_100=b100,
        candidates_1000=b1000,
        required_occurred_naturally=occurred_naturally,
    )


def benchmark_for_candidate(candidate: CandidateWord) -> BenchmarkSpec:
    crib = CribSpec(
        label=f"candidate_{candidate.branch_id.removeprefix('branch_')}",
        word=candidate.word,
        start=206,
        runes=candidate.runes,
    )
    return BenchmarkSpec(
        benchmark_id=(
            "alice_308_p13_p17_crib188x13_plus206x8_"
            f"{candidate.branch_id}_d08"
        ),
        period_a=13,
        period_b=17,
        expected_free_dimension=8,
        additional_cribs=(crib,),
        additional_cribs_are_exact=False,
    )


def candidate_for_branch(
    candidates: Iterable[CandidateWord], branch_id: str
) -> CandidateWord:
    for candidate in candidates:
        if candidate.branch_id == branch_id:
            return candidate
    raise KeyError(branch_id)


__all__ = [
    "CandidateListBundle",
    "CandidateWord",
    "benchmark_for_candidate",
    "build_nested_candidate_lists",
    "candidate_for_branch",
    "load_selected_eight_rune_words",
]
