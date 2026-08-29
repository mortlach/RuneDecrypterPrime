from __future__ import annotations

from dataclasses import asdict
from typing import Any, Sequence

from rune_decrypter_prime.scoring.ngram_hamming.reference import (
    PhraseEntry,
    PhraseProfile,
)


try:
    from rune_decrypter_prime.scoring.ngram_hamming import _ngram_hamming_fast

    FAST_BACKEND_IMPORT_ERROR: ImportError | None = None
except ImportError as exc:  # pragma: no cover - availability probe
    _ngram_hamming_fast = None  # type: ignore[assignment]
    FAST_BACKEND_IMPORT_ERROR = exc


def fast_ngram_hamming_available() -> bool:
    return _ngram_hamming_fast is not None


def _entry_to_payload(entry: PhraseEntry) -> dict[str, Any]:
    return {
        "phrase_id": entry.phrase_id,
        "direction": entry.direction,
        "dictionary_cut": entry.dictionary_cut,
        "ngram_order": entry.ngram_order,
        "word_token_ids": [list(word) for word in entry.word_token_ids],
        "rune_token_ids": list(entry.rune_token_ids),
        "count": entry.count,
        "log_count": entry.log_count,
        "phrase_count": entry.phrase_count,
    }


def _profile_to_payload(profile: PhraseProfile) -> dict[str, Any]:
    return asdict(profile)


def scan_chunk_fast(
    tokens: Sequence[int],
    phrase_entries: Sequence[PhraseEntry],
    profile: PhraseProfile,
    *,
    candidate_id: str = "",
    chunk_id: str = "",
    damage_level: str = "",
    debug_example_limit: int = 0,
) -> dict[str, Any]:
    if _ngram_hamming_fast is None:
        detail = ""
        if FAST_BACKEND_IMPORT_ERROR is not None:
            detail = f": {FAST_BACKEND_IMPORT_ERROR}"
        raise RuntimeError(f"_ngram_hamming_fast extension is not built{detail}")
    return _ngram_hamming_fast.scan(
        list(tokens),
        [_entry_to_payload(entry) for entry in phrase_entries],
        _profile_to_payload(profile),
        candidate_id,
        chunk_id,
        damage_level,
        debug_example_limit,
    )
