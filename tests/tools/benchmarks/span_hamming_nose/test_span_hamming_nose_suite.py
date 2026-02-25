from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from rune_decrypter_prime.scoring.span_hamming import SpanHammingBackend, SpanHammingConfig
from tools.benchmarks.scoring.span_hamming_nose.bench_span_hamming_nose_suite import (
    _book_shard_index,
    score_window_sample,
)
from tools.benchmarks.scoring.span_hamming_nose.schema import (
    PlanRow,
    build_stride_plan,
    load_corpus_records,
)


pytestmark = pytest.mark.tier_a


def _write_nose_npz(path: Path, tokens: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, pt_nose_data=tokens)


def test_stride_plan_is_deterministic_and_capped(tmp_path: Path) -> None:
    npz_a = tmp_path / "book_a_fwd.npz"
    npz_b = tmp_path / "book_b_fwd.npz"
    _write_nose_npz(npz_a, (np.arange(0, 1200, dtype=np.uint16) % 29).astype(np.uint8))
    _write_nose_npz(npz_b, (np.arange(200, 1600, dtype=np.uint16) % 29).astype(np.uint8))

    records = load_corpus_records([npz_a, npz_b], min_length=100, directions=("ltr",))
    plan_1 = build_stride_plan(
        records=records,
        directions=["ltr"],
        length_buckets=[100],
        global_seed=123,
        min_stride=200,
        stride_factor=1.0,
        max_windows_per_book_by_l={100: 4},
        fallback_max_windows=4,
    )
    plan_2 = build_stride_plan(
        records=records,
        directions=["ltr"],
        length_buckets=[100],
        global_seed=123,
        min_stride=200,
        stride_factor=1.0,
        max_windows_per_book_by_l={100: 4},
        fallback_max_windows=4,
    )

    assert plan_1 == plan_2
    assert plan_1

    by_book: dict[str, list[PlanRow]] = {}
    for row in plan_1:
        by_book.setdefault(row.book_id, []).append(row)
    for rows in by_book.values():
        assert len(rows) <= 4
        starts = [row.start for row in rows]
        strides = [row.stride for row in rows]
        assert all(s == 200 for s in strides)
        if len(starts) > 1:
            diffs = [b - a for a, b in zip(starts[:-1], starts[1:])]
            assert all(delta == 200 for delta in diffs)


class _ConstScorer:
    def __init__(self, value: float) -> None:
        self.value = float(value)

    def score(self, plaintext, wli_windows=None) -> float:
        return float(self.value)


def test_score_window_sample_emits_span_and_char_fields() -> None:
    span_backend = SpanHammingBackend(
        config=SpanHammingConfig(
            len_min=3,
            len_max=3,
            max_hd=1,
            max_candidates_per_window=16,
            max_intervals_considered_per_start=2,
            min_quality_threshold=1e-9,
        ),
        wordlists={
            3: [
                [0, 1, 2],
                [1, 2, 3],
                [2, 3, 4],
            ]
        },
    )
    row = PlanRow(
        row_idx=0,
        row_id="row_0",
        direction="ltr",
        length_bucket=20,
        book_id="book_a_fwd",
        book_path="book_a_fwd.npz",
        start=0,
        text_length=20,
        stride=200,
    )
    base_tokens = (np.arange(0, 20, dtype=np.uint16) % 29).astype(np.uint8)
    unigram = np.full((29,), 1.0 / 29.0, dtype=np.float64)
    fake_scorers = {
        ("ltr", 1): _ConstScorer(1.0),
        ("ltr", 2): _ConstScorer(2.0),
        ("ltr", 3): _ConstScorer(3.0),
        ("ltr", 4): _ConstScorer(4.0),
    }

    sample = score_window_sample(
        plan=row,
        base_tokens=base_tokens,
        generator="REAL",
        global_seed=42,
        batch_index=1,
        span_backend=span_backend,
        unigram_probs=unigram,
        corrupt_pcts=[10, 20, 50],
        enable_char_baselines=True,
        char_baseline_scorers=fake_scorers,
    )

    assert "span_raw" in sample
    assert "coverage" in sample
    assert "quality" in sample
    assert "n_windows_total" in sample
    assert "n_candidates_considered" in sample
    assert sample["char1_score"] == pytest.approx(1.0)
    assert sample["char2_score"] == pytest.approx(2.0)
    assert sample["char3_score"] == pytest.approx(3.0)
    assert sample["char4_score"] == pytest.approx(4.0)


def test_book_hash_sharding_is_deterministic_and_non_overlapping(tmp_path: Path) -> None:
    for idx in range(4):
        npz = tmp_path / f"book_{idx}_fwd.npz"
        _write_nose_npz(npz, (np.arange(idx, idx + 1200, dtype=np.uint16) % 29).astype(np.uint8))

    records = load_corpus_records(sorted(tmp_path.glob("*_fwd.npz")), min_length=100, directions=("ltr",))
    plan = build_stride_plan(
        records=records,
        directions=["ltr"],
        length_buckets=[100],
        global_seed=123,
        min_stride=200,
        stride_factor=1.0,
        max_windows_per_book_by_l={100: 3},
        fallback_max_windows=3,
    )
    assert plan

    shard_count = 3
    by_book: dict[str, set[int]] = {}
    for row in plan:
        shard_idx = _book_shard_index(book_id=row.book_id, shard_count=shard_count, global_seed=123)
        by_book.setdefault(row.book_id, set()).add(int(shard_idx))
    assert by_book
    assert all(len(v) == 1 for v in by_book.values())

    shard_row_ids: list[set[str]] = []
    for shard_idx in range(shard_count):
        row_ids = {
            row.row_id
            for row in plan
            if _book_shard_index(book_id=row.book_id, shard_count=shard_count, global_seed=123) == shard_idx
        }
        shard_row_ids.append(row_ids)

    union_ids: set[str] = set()
    for ids in shard_row_ids:
        union_ids |= ids
    assert union_ids == {row.row_id for row in plan}

    for i in range(shard_count):
        for j in range(i + 1, shard_count):
            assert shard_row_ids[i].isdisjoint(shard_row_ids[j])
