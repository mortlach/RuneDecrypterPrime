from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cipher_development.shared.archive import ArchivePolicy, CandidateArchive
from cipher_development.two_period_overlay.config import (
    CRIB_RUNES,
    DECISION_SCORE,
    benchmark_for,
)
from cipher_development.two_period_overlay.coordinate_supply import (
    _candidate_record,
    coordinate_supply_evaluation_budget,
    run_coordinate_supply,
)
from cipher_development.two_period_overlay.keyspace import (
    crib_space,
    deterministic_key,
)
from cipher_development.two_period_overlay.target_supply import (
    TARGET_SUPPLY_BENCHMARK_ID,
    TARGET_SUPPLY_MIN_COMBINED_UNIQUE,
    TARGET_SUPPLY_MIN_UNIQUE_PER_BLOCK,
    TARGET_SUPPLY_RESTARTS_PER_BLOCK,
    TARGET_SUPPLY_SEED_BLOCKS,
    TARGET_SUPPLY_SWEEPS,
    TARGET_SUPPLY_WALLCLOCK_LIMIT_S_PER_BLOCK,
    _combined_archive,
    _combined_restart_rows,
    target_supply_evaluation_ceiling,
    target_supply_gate,
)


def _linear_fixture():
    benchmark = benchmark_for(TARGET_SUPPLY_BENCHMARK_ID)
    true_key = deterministic_key(benchmark)
    crib = np.asarray(CRIB_RUNES, dtype=np.uint8)
    ciphertext = np.zeros(benchmark.text_length, dtype=np.uint8)
    for offset, plain in enumerate(crib):
        position = benchmark.crib_start + offset
        ciphertext[position] = (
            int(plain)
            + int(true_key[position % benchmark.period_a])
            + int(true_key[benchmark.period_a + position % benchmark.period_b])
        ) % benchmark.alphabet_size
    particular, basis, free = crib_space(ciphertext, crib, benchmark)
    variables = np.asarray([true_key[index] for index in free], dtype=np.uint8)
    return benchmark, particular, basis, variables


def _target_evaluator(target: np.ndarray):
    def evaluate(values: np.ndarray) -> np.ndarray:
        batch = np.asarray(values, dtype=np.int64)
        return -np.sum((batch - target[None, :]) ** 2, axis=1).astype(np.float64)

    return evaluate


def test_target_supply_contract_is_frozen() -> None:
    assert TARGET_SUPPLY_BENCHMARK_ID == "alice_308_p13_p17_d16"
    assert TARGET_SUPPLY_SEED_BLOCKS == (0, 1)
    assert TARGET_SUPPLY_RESTARTS_PER_BLOCK == 32
    assert TARGET_SUPPLY_SWEEPS == 12
    assert TARGET_SUPPLY_MIN_UNIQUE_PER_BLOCK == 16
    assert TARGET_SUPPLY_MIN_COMBINED_UNIQUE == 32
    assert TARGET_SUPPLY_WALLCLOCK_LIMIT_S_PER_BLOCK == 1_800.0
    assert target_supply_evaluation_ceiling() == 356_416


def test_coordinate_supply_accepts_explicit_target_budget() -> None:
    benchmark, particular, basis, target = _linear_fixture()
    outcome = run_coordinate_supply(
        _target_evaluator(target),
        particular,
        basis,
        benchmark,
        restarts=3,
        sweeps=2,
        seed_block=7,
        wallclock_limit_s=30.0,
    )
    assert outcome.generated_candidates == 3
    assert len(outcome.restart_rows) == 3
    assert all(row["seed_block"] == 7 for row in outcome.restart_rows)
    assert all(row["sweeps_requested"] == 2 for row in outcome.restart_rows)
    assert outcome.evaluations <= coordinate_supply_evaluation_budget(
        (benchmark.benchmark_id,),
        restarts=3,
        sweeps=2,
    )


def test_target_supply_gate_requires_both_blocks_and_thresholds() -> None:
    assert target_supply_gate({0: 16, 1: 16}, 32, 356_416)
    assert not target_supply_gate({0: 15, 1: 16}, 32, 100)
    assert not target_supply_gate({0: 16, 1: 16}, 31, 100)
    assert not target_supply_gate({0: 16, 1: 16}, 32, 356_417)
    with pytest.raises(ValueError, match="both declared seed blocks"):
        target_supply_gate({0: 16}, 32, 100)


def test_combined_archive_deduplicates_candidate_identity() -> None:
    benchmark, particular, basis, target = _linear_fixture()
    first = CandidateArchive(ArchivePolicy(2, DECISION_SCORE))
    second = CandidateArchive(ArchivePolicy(2, DECISION_SCORE))
    shared = _candidate_record(
        target,
        3.0,
        particular,
        basis,
        benchmark,
        evaluation_index=1,
        details={"seed_block": 0},
    )
    distinct_values = target.copy()
    distinct_values[0] = (int(distinct_values[0]) + 1) % benchmark.alphabet_size
    distinct = _candidate_record(
        distinct_values,
        2.0,
        particular,
        basis,
        benchmark,
        evaluation_index=2,
        details={"seed_block": 1},
    )
    first.offer(shared)
    second.offer(shared)
    second.offer(distinct)

    combined = _combined_archive({0: first, 1: second})

    assert len(combined.records) == 2
    assert combined.records[0].candidate_id == shared.candidate_id


def test_combined_restart_rows_preserve_block_and_global_indices() -> None:
    rows = _combined_restart_rows({
        0: (
            {"seed_block": 0, "evaluation_index": 10, "candidate_id": "a"},
            {"seed_block": 0, "evaluation_index": 20, "candidate_id": "b"},
        ),
        1: (
            {"seed_block": 1, "evaluation_index": 7, "candidate_id": "c"},
            {"seed_block": 1, "evaluation_index": 15, "candidate_id": "d"},
        ),
    })
    assert [row["block_evaluation_index"] for row in rows] == [10, 20, 7, 15]
    assert [row["global_evaluation_index"] for row in rows] == [10, 20, 27, 35]


def test_target_supply_source_is_explicit_and_truth_free() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    text = (
        repo_root
        / "cipher_development/two_period_overlay/target_supply.py"
    ).read_text(encoding="utf-8")
    for token in ("os.environ", "os.getenv", "argparse", "sys.argv"):
        assert token not in text
    assert "reference_metrics(" in text
    assert "reference_evaluation=" in text
    assert "truth" not in {
        field
        for field in (
            "target_supply_gate_passed",
            "combined",
            "blocks",
        )
    }


def test_review_pack_requires_complete_target_supply_evidence() -> None:
    from cipher_development.two_period_overlay.review_pack import (
        _required_artifacts,
    )

    required = set(_required_artifacts("target_coordinate_supply_v1"))
    assert "artifacts/replay_context.json" in required
    assert "artifacts/target_coordinate_supply_summary.json" in required
    assert (
        "artifacts/target_coordinate_supply/combined_pool_archive.json"
        in required
    )
    assert (
        "artifacts/target_coordinate_supply/combined_diagnostics.json"
        in required
    )
    for seed_block in TARGET_SUPPLY_SEED_BLOCKS:
        prefix = f"artifacts/target_coordinate_supply/seed_block_{seed_block}"
        for filename in (
            "discovery_pool_archive.json",
            "coordinate_archive.json",
            "discovery_restarts.json",
            "discovery_diagnostics.json",
        ):
            assert f"{prefix}/{filename}" in required
