from __future__ import annotations

from dataclasses import asdict
from importlib import import_module
from typing import Any, Sequence

from rdp.scoring.ngram_hamming.reference import PhraseEntry, PhraseProfile


def _load_fast_extension():
    try:
        return import_module("rdp.scoring.ngram_hamming._ngram_hamming_fast"), None
    except ImportError as exc:  # pragma: no cover - availability probe
        return None, exc


def fast_ngram_hamming_available() -> bool:
    extension, _ = _load_fast_extension()
    return extension is not None


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
    extension, import_error = _load_fast_extension()
    if extension is None:
        detail = ""
        if import_error is not None:
            detail = f": {import_error}"
        raise RuntimeError(f"_ngram_hamming_fast extension is not built{detail}")
    return extension.scan(
        list(tokens),
        [_entry_to_payload(entry) for entry in phrase_entries],
        _profile_to_payload(profile),
        candidate_id,
        chunk_id,
        damage_level,
        debug_example_limit,
    )
