from __future__ import annotations

import pytest

from rune_decrypter_prime.scoring.ngram_hamming.fast_backend import (
    fast_ngram_hamming_available,
    scan_chunk_fast,
)
from rune_decrypter_prime.scoring.ngram_hamming.reference import (
    PhraseEntry,
    PhraseProfile,
    scan_chunk_reference,
)


pytestmark = pytest.mark.skipif(
    not fast_ngram_hamming_available(),
    reason="optional _ngram_hamming_fast extension is not built",
)


def _entry(
    phrase_id: str,
    words: tuple[tuple[int, ...], ...],
    *,
    direction: str = "fwd",
    dictionary_cut: str = "normal",
    order: int | None = None,
    log_count: float = 2.0,
) -> PhraseEntry:
    return PhraseEntry(
        phrase_id=phrase_id,
        direction=direction,
        dictionary_cut=dictionary_cut,
        ngram_order=order or len(words),
        word_token_ids=words,
        rune_token_ids=tuple(token for word in words for token in word),
        count=10.0,
        log_count=log_count,
        phrase_count=3,
    )


def _profile(**overrides) -> PhraseProfile:
    data = {
        "profile_id": "P_test",
        "direction": "fwd",
        "orders": (2, 3),
        "dictionary_cuts": ("normal",),
        "min_phrase_token_length": 2,
        "max_total_phrase_hd": 2,
        "max_word_hd": 2,
        "normalised_hd_ceiling": None,
    }
    data.update(overrides)
    return PhraseProfile(**data)


def _hit_key(hit) -> dict[str, object]:
    if not isinstance(hit, dict):
        hit = hit.__dict__
    return {
        "candidate_id": hit["candidate_id"],
        "chunk_id": hit["chunk_id"],
        "damage_level": hit["damage_level"],
        "profile_id": hit["profile_id"],
        "ngram_order": hit["ngram_order"],
        "dictionary_cut": hit["dictionary_cut"],
        "phrase_id": hit["phrase_id"],
        "phrase_count": hit["phrase_count"],
        "phrase_log_count": hit["phrase_log_count"],
        "phrase_token_length": hit["phrase_token_length"],
        "word_lengths": tuple(hit["word_lengths"]),
        "word_hds": tuple(hit["word_hds"]),
        "total_phrase_hd": hit["total_phrase_hd"],
        "max_word_hd": hit["max_word_hd"],
        "mean_word_hd": hit["mean_word_hd"],
        "normalised_phrase_hd": hit["normalised_phrase_hd"],
        "hit_start": hit["hit_start"],
        "hit_end": hit["hit_end"],
    }


def _reference_payload(tokens, entries, profile, *, debug_example_limit: int = 0) -> dict[str, object]:
    result = scan_chunk_reference(
        tokens,
        entries,
        profile,
        candidate_id="candidate",
        chunk_id="chunk",
        damage_level="synthetic",
        debug_example_limit=debug_example_limit,
    )
    return {
        "phrase_hits": [_hit_key(hit.__dict__) for hit in result.phrase_hits],
        "candidate_tokens_scanned": result.candidate_tokens_scanned,
        "candidate_start_offsets_considered": result.candidate_start_offsets_considered,
        "phrase_entries_considered": result.phrase_entries_considered,
        "phrase_verification_attempts": result.phrase_verification_attempts,
        "phrase_verification_passes": result.phrase_verification_passes,
        "opportunity_count": result.opportunity_count,
        "positive_start_offset_count": result.positive_start_offset_count,
        "phrase_hits_per_opportunity": result.phrase_hits_per_opportunity,
        "positive_start_offset_fraction": result.positive_start_offset_fraction,
        "debug_examples": [_hit_key(hit.__dict__) for hit in result.debug_examples],
    }


def _fast_payload(tokens, entries, profile, *, debug_example_limit: int = 0) -> dict[str, object]:
    payload = scan_chunk_fast(
        tokens,
        entries,
        profile,
        candidate_id="candidate",
        chunk_id="chunk",
        damage_level="synthetic",
        debug_example_limit=debug_example_limit,
    )
    payload["phrase_hits"] = [_hit_key(hit) for hit in payload["phrase_hits"]]
    payload["debug_examples"] = [_hit_key(hit) for hit in payload["debug_examples"]]
    return payload


def _assert_parity(tokens, entries, profile, *, debug_example_limit: int = 0) -> None:
    assert _fast_payload(tokens, entries, profile, debug_example_limit=debug_example_limit) == _reference_payload(
        tokens,
        entries,
        profile,
        debug_example_limit=debug_example_limit,
    )


def test_fast_backend_matches_exact_hit() -> None:
    _assert_parity([9, 1, 2, 3, 8], [_entry("p1", ((1, 2), (3,)))], _profile())


def test_fast_backend_matches_one_damaged_word() -> None:
    _assert_parity([1, 9, 3, 4], [_entry("p1", ((1, 2), (3, 4)))], _profile(max_word_hd=1))


def test_fast_backend_matches_multiple_damaged_words() -> None:
    _assert_parity([1, 9, 3, 8], [_entry("p1", ((1, 2), (3, 4)))], _profile(max_word_hd=1, max_total_phrase_hd=2))


def test_fast_backend_rejects_wrong_direction() -> None:
    _assert_parity([1, 2], [_entry("rev_phrase", ((1,), (2,)), direction="rev")], _profile(max_total_phrase_hd=0, max_word_hd=0))


def test_fast_backend_rejects_wrong_cut() -> None:
    _assert_parity([1, 2], [_entry("strict_phrase", ((1,), (2,)), dictionary_cut="strict")], _profile())


def test_fast_backend_rejects_below_min_length() -> None:
    _assert_parity([1, 2], [_entry("short", ((1,), (2,)))], _profile(min_phrase_token_length=3))


def test_fast_backend_rejects_total_hd() -> None:
    _assert_parity([9, 8, 7], [_entry("p1", ((1, 2), (3,)))], _profile(max_total_phrase_hd=2, max_word_hd=2))


def test_fast_backend_rejects_max_word_hd() -> None:
    _assert_parity([9, 8, 3, 4], [_entry("p1", ((1, 2), (3, 4)))], _profile(max_total_phrase_hd=2, max_word_hd=1))


def test_fast_backend_rejects_normalised_hd_ceiling() -> None:
    _assert_parity(
        [1, 9, 3, 8],
        [_entry("p1", ((1, 2), (3, 4)))],
        _profile(max_word_hd=1, max_total_phrase_hd=2, normalised_hd_ceiling=0.25),
    )


def test_fast_backend_counts_multiple_phrases_at_same_offset() -> None:
    entries = [_entry("p1", ((1,), (2,))), _entry("p2", ((1,), (2,)), log_count=3.0)]
    _assert_parity([1, 2], entries, _profile(min_phrase_token_length=2, max_total_phrase_hd=0, max_word_hd=0))


def test_fast_backend_debug_examples_do_not_change_aggregate_scores() -> None:
    entries = [_entry("p1", ((1,), (2,))), _entry("p2", ((1,), (2,)), log_count=3.0)]
    profile = _profile(min_phrase_token_length=2, max_total_phrase_hd=0, max_word_hd=0)

    normal = _fast_payload([1, 2], entries, profile, debug_example_limit=0)
    debug = _fast_payload([1, 2], entries, profile, debug_example_limit=1)

    assert {key: value for key, value in normal.items() if key != "debug_examples"} == {
        key: value for key, value in debug.items() if key != "debug_examples"
    }
    assert len(debug["debug_examples"]) == 1


def test_fast_backend_rejects_invalid_candidate_tokens_before_scanning() -> None:
    entries = [_entry("p1", ((1,), (2,)))]
    profile = _profile(min_phrase_token_length=2)
    with pytest.raises(Exception, match="not an integer"):
        scan_chunk_fast(["1", 2], entries, profile)  # type: ignore[list-item]
    with pytest.raises(Exception, match="not an integer"):
        scan_chunk_fast([True, 2], entries, profile)  # type: ignore[list-item]
    with pytest.raises(Exception, match="outside"):
        scan_chunk_fast([29, 2], entries, profile)
    with pytest.raises(Exception, match="empty"):
        scan_chunk_fast([], entries, profile)
