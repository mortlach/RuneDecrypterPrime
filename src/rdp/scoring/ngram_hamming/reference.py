from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence


CanonicalWordTokens = tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class PhraseProfile:
    profile_id: str
    direction: str
    orders: tuple[int, ...]
    dictionary_cuts: tuple[str, ...]
    min_phrase_token_length: int
    max_total_phrase_hd: int
    max_word_hd: int
    normalised_hd_ceiling: float | None = None
    exact_match_word_lengths: tuple[int, ...] = ()


@dataclass(frozen=True)
class PhraseEntry:
    phrase_id: str
    direction: str
    dictionary_cut: str
    ngram_order: int
    word_token_ids: CanonicalWordTokens
    rune_token_ids: tuple[int, ...]
    count: float = 0.0
    log_count: float = 0.0
    phrase_count: int = 1
    top_latin_ngram: str = ""

    @property
    def word_lengths(self) -> tuple[int, ...]:
        return tuple(len(word) for word in self.word_token_ids)

    @property
    def phrase_token_length(self) -> int:
        return len(self.rune_token_ids)


@dataclass(frozen=True)
class PhraseHit:
    candidate_id: str
    chunk_id: str
    damage_level: str
    profile_id: str
    ngram_order: int
    dictionary_cut: str
    phrase_id: str
    phrase_count: int
    phrase_log_count: float
    phrase_token_length: int
    word_lengths: tuple[int, ...]
    word_hds: tuple[int, ...]
    total_phrase_hd: int
    max_word_hd: int
    mean_word_hd: float
    normalised_phrase_hd: float
    hit_start: int
    hit_end: int


@dataclass(frozen=True)
class ReferenceScanResult:
    phrase_hits: tuple[PhraseHit, ...]
    candidate_tokens_scanned: int
    candidate_start_offsets_considered: int
    phrase_entries_considered: int
    phrase_verification_attempts: int
    phrase_verification_passes: int
    opportunity_count: int
    positive_start_offset_count: int
    phrase_hits_per_opportunity: float
    positive_start_offset_fraction: float
    debug_examples: tuple[PhraseHit, ...] = field(default_factory=tuple)


def parse_json_list(value: str | Sequence[object], field_name: str) -> list[object]:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{field_name} is not valid JSON") from exc
    else:
        parsed = list(value)
    if not isinstance(parsed, list):
        raise ValueError(f"{field_name} is not a JSON list")
    return parsed


def _parse_token(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} token is not an integer")
    token = value
    if token < 0 or token > 28:
        raise ValueError(f"{field_name} token outside 0..28")
    return token


def parse_flat_token_ids(value: str | Sequence[object], *, field_name: str = "rune_token_ids") -> tuple[int, ...]:
    raw = parse_json_list(value, field_name)
    out = tuple(_parse_token(item, field_name=field_name) for item in raw)
    if not out:
        raise ValueError(f"{field_name} is empty")
    return out


def parse_positive_int_ids(value: str | Sequence[object], *, field_name: str) -> tuple[int, ...]:
    raw = parse_json_list(value, field_name)
    out: list[int] = []
    for item in raw:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ValueError(f"{field_name} value is not an integer")
        if item <= 0:
            raise ValueError(f"{field_name} value must be positive")
        out.append(item)
    if not out:
        raise ValueError(f"{field_name} is empty")
    return tuple(out)


def validate_candidate_tokens(tokens: Sequence[int]) -> tuple[int, ...]:
    parsed = tuple(_parse_token(token, field_name="candidate_tokens") for token in tokens)
    if not parsed:
        raise ValueError("candidate_tokens is empty")
    return parsed


def parse_word_token_ids(value: str | Sequence[object], *, field_name: str = "word_token_ids") -> CanonicalWordTokens:
    raw = parse_json_list(value, field_name)
    words: list[tuple[int, ...]] = []
    for word in raw:
        if not isinstance(word, list | tuple):
            raise ValueError(f"{field_name} contains a non-list word")
        parsed = tuple(_parse_token(item, field_name=field_name) for item in word)
        if not parsed:
            raise ValueError(f"{field_name} contains an empty word")
        words.append(parsed)
    if not words:
        raise ValueError(f"{field_name} is empty")
    return tuple(words)


def flatten_word_tokens(word_token_ids: CanonicalWordTokens) -> tuple[int, ...]:
    return tuple(token for word in word_token_ids for token in word)


def phrase_entry_from_asset_row(row: Mapping[str, object], *, phrase_id: str | None = None) -> PhraseEntry:
    word_token_ids = parse_word_token_ids(row.get("word_token_ids", ""))
    rune_token_ids = parse_flat_token_ids(row.get("rune_token_ids", ""))
    rune_lengths = parse_positive_int_ids(row.get("rune_lengths", ""), field_name="rune_lengths")
    if flatten_word_tokens(word_token_ids) != rune_token_ids:
        raise ValueError("flatten(word_token_ids) != rune_token_ids")
    if tuple(len(word) for word in word_token_ids) != rune_lengths:
        raise ValueError("word_token_ids lengths != rune_lengths")
    ngram_order = int(row.get("n", len(word_token_ids)))
    if len(word_token_ids) != ngram_order:
        raise ValueError("word_token_ids group count != n")
    resolved_phrase_id = phrase_id or "|".join(
        (
            str(row.get("encoding_direction", "")),
            str(row.get("dictionary_cut", "")),
            str(ngram_order),
            json.dumps(word_token_ids, separators=(",", ":")),
        )
    )
    return PhraseEntry(
        phrase_id=resolved_phrase_id,
        direction=str(row.get("encoding_direction", "")),
        dictionary_cut=str(row.get("dictionary_cut", "")),
        ngram_order=ngram_order,
        word_token_ids=word_token_ids,
        rune_token_ids=rune_token_ids,
        count=float(row.get("count", 0.0) or 0.0),
        log_count=float(row.get("log_count", 0.0) or 0.0),
        phrase_count=int(float(row.get("phrase_count", 1) or 1)),
        top_latin_ngram=str(row.get("top_latin_ngram", "")),
    )


def hamming(left: Sequence[int], right: Sequence[int]) -> int:
    if len(left) != len(right):
        raise ValueError("cannot compute Hamming distance for unequal lengths")
    return sum(1 for lval, rval in zip(left, right) if lval != rval)


def profile_allows_entry(entry: PhraseEntry, profile: PhraseProfile) -> bool:
    return (
        entry.direction == profile.direction
        and entry.ngram_order in profile.orders
        and entry.dictionary_cut in profile.dictionary_cuts
        and entry.phrase_token_length >= profile.min_phrase_token_length
    )


def phrase_could_fit_at_start(tokens: Sequence[int], start: int, entry: PhraseEntry, profile: PhraseProfile) -> bool:
    if not profile_allows_entry(entry, profile):
        return False
    return start + entry.phrase_token_length <= len(tokens)


def verify_phrase_at_start(
    tokens: Sequence[int],
    start: int,
    entry: PhraseEntry,
    profile: PhraseProfile,
    *,
    candidate_id: str,
    chunk_id: str,
    damage_level: str,
) -> PhraseHit | None:
    offset = start
    word_hds: list[int] = []
    for word in entry.word_token_ids:
        end = offset + len(word)
        if end > len(tokens):
            return None
        distance = hamming(tokens[offset:end], word)
        if len(word) in profile.exact_match_word_lengths and distance != 0:
            return None
        if distance > profile.max_word_hd:
            return None
        word_hds.append(distance)
        offset = end
    total_hd = sum(word_hds)
    if total_hd > profile.max_total_phrase_hd:
        return None
    normalised = total_hd / entry.phrase_token_length if entry.phrase_token_length else 0.0
    if profile.normalised_hd_ceiling is not None and normalised > profile.normalised_hd_ceiling:
        return None
    return PhraseHit(
        candidate_id=candidate_id,
        chunk_id=chunk_id,
        damage_level=damage_level,
        profile_id=profile.profile_id,
        ngram_order=entry.ngram_order,
        dictionary_cut=entry.dictionary_cut,
        phrase_id=entry.phrase_id,
        phrase_count=entry.phrase_count,
        phrase_log_count=entry.log_count,
        phrase_token_length=entry.phrase_token_length,
        word_lengths=entry.word_lengths,
        word_hds=tuple(word_hds),
        total_phrase_hd=total_hd,
        max_word_hd=max(word_hds) if word_hds else 0,
        mean_word_hd=sum(word_hds) / len(word_hds) if word_hds else 0.0,
        normalised_phrase_hd=normalised,
        hit_start=start,
        hit_end=start + entry.phrase_token_length,
    )


def scan_chunk_reference(
    tokens: Sequence[int],
    phrase_entries: Iterable[PhraseEntry],
    profile: PhraseProfile,
    *,
    candidate_id: str = "",
    chunk_id: str = "",
    damage_level: str = "",
    debug_example_limit: int = 0,
) -> ReferenceScanResult:
    tokens = validate_candidate_tokens(tokens)
    entries = tuple(entry for entry in phrase_entries if profile_allows_entry(entry, profile))
    start_offsets_considered = len(tokens)
    opportunity_offsets: set[int] = set()
    hits: list[PhraseHit] = []
    attempts = 0
    passes = 0
    for start in range(len(tokens)):
        entries_that_fit = [entry for entry in entries if phrase_could_fit_at_start(tokens, start, entry, profile)]
        if entries_that_fit:
            opportunity_offsets.add(start)
        for entry in entries_that_fit:
            attempts += 1
            hit = verify_phrase_at_start(
                tokens,
                start,
                entry,
                profile,
                candidate_id=candidate_id,
                chunk_id=chunk_id,
                damage_level=damage_level,
            )
            if hit is not None:
                passes += 1
                hits.append(hit)
    positive_offsets = {hit.hit_start for hit in hits}
    opportunity_count = len(opportunity_offsets)
    return ReferenceScanResult(
        phrase_hits=tuple(hits),
        candidate_tokens_scanned=len(tokens),
        candidate_start_offsets_considered=start_offsets_considered,
        phrase_entries_considered=len(entries),
        phrase_verification_attempts=attempts,
        phrase_verification_passes=passes,
        opportunity_count=opportunity_count,
        positive_start_offset_count=len(positive_offsets),
        phrase_hits_per_opportunity=(len(hits) / opportunity_count if opportunity_count else 0.0),
        positive_start_offset_fraction=(len(positive_offsets) / opportunity_count if opportunity_count else 0.0),
        debug_examples=tuple(hits[: max(0, int(debug_example_limit))]),
    )
