from __future__ import annotations

import pytest

from rune_decrypter_prime.scoring.ngram_hamming.reference import (
    PhraseEntry,
    PhraseProfile,
    parse_word_token_ids,
    scan_chunk_reference,
)


def _entry(
    phrase_id: str,
    words: tuple[tuple[int, ...], ...],
    *,
    dictionary_cut: str = "normal",
    order: int | None = None,
) -> PhraseEntry:
    return PhraseEntry(
        phrase_id=phrase_id,
        direction="fwd",
        dictionary_cut=dictionary_cut,
        ngram_order=order or len(words),
        word_token_ids=words,
        rune_token_ids=tuple(token for word in words for token in word),
        count=10.0,
        log_count=2.0,
    )


def _profile(**overrides) -> PhraseProfile:
    data = {
        "profile_id": "P_test",
        "direction": "fwd",
        "orders": (2, 3),
        "dictionary_cuts": ("normal",),
        "min_phrase_token_length": 3,
        "max_total_phrase_hd": 2,
        "max_word_hd": 2,
        "normalised_hd_ceiling": None,
    }
    data.update(overrides)
    return PhraseProfile(**data)


def test_word_structured_phrase_hit_exact() -> None:
    entry = _entry("p1", ((1, 2), (3,)))

    result = scan_chunk_reference([9, 1, 2, 3, 8], [entry], _profile(), candidate_id="c", chunk_id="k")

    assert len(result.phrase_hits) == 1
    hit = result.phrase_hits[0]
    assert hit.hit_start == 1
    assert hit.word_hds == (0, 0)
    assert hit.total_phrase_hd == 0


def test_word_structured_phrase_hit_with_damage() -> None:
    entry = _entry("p1", ((1, 2), (3, 4)))

    result = scan_chunk_reference([1, 9, 3, 8], [entry], _profile(max_total_phrase_hd=2, max_word_hd=1))

    assert len(result.phrase_hits) == 1
    assert result.phrase_hits[0].word_hds == (1, 1)


def test_phrase_min_length_rule() -> None:
    entry = _entry("p1", ((1,), (2,)))

    result = scan_chunk_reference([1, 2], [entry], _profile(min_phrase_token_length=3))

    assert result.phrase_entries_considered == 0
    assert len(result.phrase_hits) == 0


def test_len8_profiles_scan_the_full_phrase_not_first_eight_tokens() -> None:
    entry = _entry("long_phrase", ((1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11)))
    tokens = [1, 2, 3, 4, 5, 6, 7, 8, 20, 21, 22]
    p2 = _profile(
        profile_id="P2_conservative_len8_hd2",
        orders=(3,),
        min_phrase_token_length=8,
        max_total_phrase_hd=2,
        max_word_hd=1,
    )
    p3 = _profile(
        profile_id="P3_word_shape_guarded_len8_hd2",
        orders=(3,),
        min_phrase_token_length=8,
        max_total_phrase_hd=2,
        max_word_hd=1,
        exact_match_word_lengths=(1, 2),
    )

    assert scan_chunk_reference(tokens, [entry], p2).phrase_hits == ()
    assert scan_chunk_reference(tokens, [entry], p3).phrase_hits == ()


def test_scan_considers_every_candidate_token_offset() -> None:
    entry = _entry("offset_phrase", ((9, 9, 9), (8, 8, 8), (7, 7)))
    tokens = [1, 2, 3, 9, 9, 9, 8, 8, 8, 7, 7, 4]
    profile = _profile(orders=(3,), min_phrase_token_length=8, max_total_phrase_hd=0, max_word_hd=0)

    result = scan_chunk_reference(tokens, [entry], profile)

    assert result.candidate_start_offsets_considered == len(tokens)
    assert len(result.phrase_hits) == 1
    assert result.phrase_hits[0].hit_start == 3
    assert result.phrase_hits[0].hit_end == 11


def test_p3_rejects_mismatch_in_short_words() -> None:
    entry = _entry("short_word_guard", ((1, 2), (3, 4, 5), (6, 7, 8)))
    tokens = [1, 9, 3, 4, 5, 6, 7, 8]
    p2 = _profile(
        profile_id="P2_conservative_len8_hd2",
        orders=(3,),
        min_phrase_token_length=8,
        max_total_phrase_hd=2,
        max_word_hd=1,
    )
    p3 = _profile(
        profile_id="P3_word_shape_guarded_len8_hd2",
        orders=(3,),
        min_phrase_token_length=8,
        max_total_phrase_hd=2,
        max_word_hd=1,
        exact_match_word_lengths=(1, 2),
    )

    p2_result = scan_chunk_reference(tokens, [entry], p2)
    p3_result = scan_chunk_reference(tokens, [entry], p3)

    assert len(p2_result.phrase_hits) == 1
    assert p2_result.phrase_hits[0].word_lengths == (2, 3, 3)
    assert p2_result.phrase_hits[0].word_hds == (1, 0, 0)
    assert p3_result.phrase_hits == ()


def test_total_phrase_hd_rule() -> None:
    entry = _entry("p1", ((1, 2), (3,)))

    result = scan_chunk_reference([9, 8, 7], [entry], _profile(max_total_phrase_hd=2, max_word_hd=2))

    assert len(result.phrase_hits) == 0


def test_max_word_hd_rule() -> None:
    entry = _entry("p1", ((1, 2), (3, 4)))

    result = scan_chunk_reference([9, 8, 3, 4], [entry], _profile(max_total_phrase_hd=2, max_word_hd=1))

    assert len(result.phrase_hits) == 0


def test_joined_phrase_and_word_structured_phrase_can_differ() -> None:
    left = parse_word_token_ids("[[12, 3], [4]]")
    right = parse_word_token_ids("[[12], [3, 4]]")

    assert tuple(token for word in left for token in word) == tuple(token for word in right for token in word)
    assert left != right


def test_word_token_ids_accepts_canonical_nested_tuple() -> None:
    assert parse_word_token_ids(((12, 3), (4,))) == ((12, 3), (4,))


def test_word_token_ids_rejects_strings_and_floats() -> None:
    with pytest.raises(ValueError, match="not an integer"):
        parse_word_token_ids('[[12, "3"], [4]]')
    with pytest.raises(ValueError, match="not an integer"):
        parse_word_token_ids("[[12, 3.0], [4]]")


def test_reference_profile_rejects_wrong_direction() -> None:
    entry = PhraseEntry(
        phrase_id="rev_phrase",
        direction="rev",
        dictionary_cut="normal",
        ngram_order=2,
        word_token_ids=((1,), (2,)),
        rune_token_ids=(1, 2),
    )
    result = scan_chunk_reference([1, 2], [entry], _profile(min_phrase_token_length=2))

    assert result.phrase_entries_considered == 0
    assert result.phrase_hits == ()


def test_candidate_tokens_are_strict_ints() -> None:
    entry = _entry("p1", ((1,), (2,)))
    with pytest.raises(ValueError, match="not an integer"):
        scan_chunk_reference(["1", 2], [entry], _profile(min_phrase_token_length=2))  # type: ignore[list-item]
    with pytest.raises(ValueError, match="not an integer"):
        scan_chunk_reference([True, 2], [entry], _profile(min_phrase_token_length=2))  # type: ignore[list-item]


def test_candidate_tokens_are_non_empty_and_bounded() -> None:
    entry = _entry("p1", ((1,), (2,)))
    with pytest.raises(ValueError, match="empty"):
        scan_chunk_reference([], [entry], _profile(min_phrase_token_length=2))
    with pytest.raises(ValueError, match="outside"):
        scan_chunk_reference([29, 2], [entry], _profile(min_phrase_token_length=2))


def test_debug_example_limit_does_not_change_scores() -> None:
    entries = [_entry("p1", ((1,), (2,))), _entry("p2", ((1,), (2,)))]
    profile = _profile(min_phrase_token_length=2)

    normal = scan_chunk_reference([1, 2], entries, profile, debug_example_limit=0)
    debug = scan_chunk_reference([1, 2], entries, profile, debug_example_limit=1)

    assert len(normal.phrase_hits) == len(debug.phrase_hits) == 2
    assert normal.phrase_hits_per_opportunity == debug.phrase_hits_per_opportunity
    assert len(debug.debug_examples) == 1


def test_phrase_hits_per_opportunity_can_exceed_one() -> None:
    entries = [_entry("p1", ((1,), (2,))), _entry("p2", ((1,), (2,)))]
    result = scan_chunk_reference([1, 2], entries, _profile(min_phrase_token_length=2))

    assert result.opportunity_count == 1
    assert len(result.phrase_hits) == 2
    assert result.phrase_hits_per_opportunity == pytest.approx(2.0)


def test_positive_start_offset_fraction_is_bounded() -> None:
    entries = [_entry("p1", ((1,), (2,))), _entry("p2", ((1,), (2,)))]
    result = scan_chunk_reference([1, 2], entries, _profile(min_phrase_token_length=2))

    assert result.positive_start_offset_count == 1
    assert result.positive_start_offset_fraction == pytest.approx(1.0)
    assert 0.0 <= result.positive_start_offset_fraction <= 1.0
