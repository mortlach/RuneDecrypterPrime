from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_runeberg_nose_damage_ladder_v1 as phaseb,
)


EXPECTED_MAX_HD_BY_LENGTH = {
    1: 0,
    2: 0,
    3: 1,
    4: 1,
    5: 1,
    6: 2,
    7: 2,
    8: 3,
    9: 3,
    10: 4,
    11: 4,
    12: 5,
    13: 5,
    14: 5,
}


def _npz_path(tmp_path: Path, name: str) -> Path:
    return tmp_path / name


def _clean_chunk() -> phaseb.CleanChunk:
    tokens = tuple((idx % 29) for idx in range(phaseb.CHUNK_SIZE))
    return phaseb.CleanChunk(
        book="book_a",
        direction="fwd",
        chunk_index=0,
        chunk_start=0,
        chunk_end=phaseb.CHUNK_SIZE,
        tokens=tokens,
        wli=tuple((idx // 5, idx % 5) for idx in range(phaseb.CHUNK_SIZE)),
    )


def test_complete_books_requires_fwd_and_rev(tmp_path: Path) -> None:
    rows = [
        ("book_a", "fwd", tmp_path / "book_a_fwd.npz"),
        ("book_a", "rev", tmp_path / "book_a_rev.npz"),
        ("book_b", "fwd", tmp_path / "book_b_fwd.npz"),
        ("book_c", "rev", tmp_path / "book_c_rev.npz"),
    ]

    assert phaseb.complete_books_from_rows(rows) == ["book_a"]
    assert phaseb.select_books(rows, max_books=10) == ["book_a"]


def test_load_tokenized_nose_rejects_missing_arrays(tmp_path: Path) -> None:
    path = _npz_path(tmp_path, "book_a_fwd.npz")
    np.savez(path, pt_nose_data=np.array([0, 1, 2], dtype=np.uint8))

    with pytest.raises(KeyError, match="wli_nose_data"):
        phaseb.load_tokenized_nose("book_a", "fwd", path)


def test_load_tokenized_nose_rejects_token_wli_length_mismatch(tmp_path: Path) -> None:
    path = _npz_path(tmp_path, "book_a_fwd.npz")
    np.savez(
        path,
        pt_nose_data=np.array([0, 1, 2], dtype=np.uint8),
        wli_nose_data=np.array([0, 1, 2, 3], dtype=np.uint8),
    )

    with pytest.raises(ValueError, match="token/WLI length mismatch"):
        phaseb.load_tokenized_nose("book_a", "fwd", path)


def test_load_tokenized_nose_rejects_odd_wli_length(tmp_path: Path) -> None:
    path = _npz_path(tmp_path, "book_a_fwd.npz")
    np.savez(
        path,
        pt_nose_data=np.array([0, 1], dtype=np.uint8),
        wli_nose_data=np.array([0, 1, 2], dtype=np.uint8),
    )

    with pytest.raises(ValueError, match="length is not even"):
        phaseb.load_tokenized_nose("book_a", "fwd", path)


def test_damage_functions_are_deterministic() -> None:
    clean_chunk = _clean_chunk()
    global_probs = np.ones(29, dtype=np.float64) / 29.0
    book_probs = phaseb._empirical_probs(clean_chunk.tokens)
    limits = {
        "damage_repeats_per_chunk": 1,
        "damage_levels": (0.30,),
        "include_damage_models": (
            "independent_substitution",
            "frequency_matched_global",
            "frequency_matched_book",
            "word_local_substitution",
            "burst_substitution",
            "lane_period_substitution",
        ),
        "include_null_models": (
            "uniform_random",
            "global_frequency_random",
            "within_chunk_shuffle",
            "block_shuffle_25",
        ),
    }

    first = list(phaseb.iter_samples_for_chunk(clean_chunk, global_probs=global_probs, book_probs=book_probs, limits=limits))
    second = list(phaseb.iter_samples_for_chunk(clean_chunk, global_probs=global_probs, book_probs=book_probs, limits=limits))

    assert [(row.sample_id, row.seed, row.tokens) for row in first] == [
        (row.sample_id, row.seed, row.tokens) for row in second
    ]


def test_damage_functions_preserve_length_and_token_range() -> None:
    clean_chunk = _clean_chunk()
    global_probs = np.ones(29, dtype=np.float64) / 29.0
    book_probs = phaseb._empirical_probs(clean_chunk.tokens)
    samples = list(
        phaseb.iter_samples_for_chunk(
            clean_chunk,
            global_probs=global_probs,
            book_probs=book_probs,
            limits=phaseb.MODE_LIMITS["smoke"],
        )
    )

    assert {sample.source_kind for sample in samples} == {"clean", "damaged", "null"}
    assert all(len(sample.tokens) == phaseb.CHUNK_SIZE for sample in samples)
    assert all(min(sample.tokens) >= 0 and max(sample.tokens) <= 28 for sample in samples)


def test_full_ladder_matches_v0_3() -> None:
    assert phaseb.SPAN_LENGTHS == tuple(range(1, 15))
    assert phaseb.MAX_HD_BY_LENGTH == EXPECTED_MAX_HD_BY_LENGTH
    assert sum(max_hd + 1 for max_hd in phaseb.MAX_HD_BY_LENGTH.values()) == 50


def test_estimate_total_samples_matches_mode_config() -> None:
    limits = phaseb.MODE_LIMITS["smoke"]
    expected_per_chunk = (
        1
        + int(limits["damage_repeats_per_chunk"])
        * len(tuple(limits["damage_levels"]))
        * len(tuple(limits["include_damage_models"]))
        + int(limits["damage_repeats_per_chunk"]) * len(tuple(limits["include_null_models"]))
    )

    assert expected_per_chunk == 15
    assert phaseb.estimate_total_samples(8, limits) == 120
