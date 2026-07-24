from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cipher_development.shared.archive import (
    ArchivePolicy,
    CandidateArchive,
    read_candidate_archive,
)
from cipher_development.two_period_overlay.config import (
    CRIB_RUNES,
    DECISION_SCORE,
    BenchmarkSpec,
    benchmark_for,
)
from cipher_development.two_period_overlay.coordinate_supply import (
    SUPPLY_BENCHMARK_IDS,
    SUPPLY_MIN_UNIQUE,
    SUPPLY_RESTARTS,
    SUPPLY_SEED_BLOCK,
    SUPPLY_SWEEPS,
    SUPPLY_WALLCLOCK_LIMIT_S,
    _candidate_record,
    coordinate_supply_evaluation_budget,
    coordinate_supply_seed,
    run_coordinate_supply,
    write_coordinate_supply_artifacts,
)
from cipher_development.two_period_overlay.diagnostics import discovery_diagnostics
from cipher_development.two_period_overlay.keyspace import (
    crib_space,
    deterministic_key,
)


def _linear_fixture(benchmark: BenchmarkSpec):
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
    return particular, basis, variables


def _target_evaluator(target: np.ndarray):
    def evaluate(values: np.ndarray) -> np.ndarray:
        batch = np.asarray(values, dtype=np.int64)
        return -np.sum((batch - target[None, :]) ** 2, axis=1).astype(np.float64)

    return evaluate


def test_coordinate_supply_contract_is_frozen() -> None:
    assert SUPPLY_BENCHMARK_IDS == (
        "alice_308_p05_p13_d04",
        "alice_308_p09_p13_d08",
    )
    assert SUPPLY_RESTARTS == 32
    assert SUPPLY_SWEEPS == 8
    assert SUPPLY_SEED_BLOCK == 0
    assert SUPPLY_MIN_UNIQUE == 16
    assert SUPPLY_WALLCLOCK_LIMIT_S == 900.0
    assert coordinate_supply_evaluation_budget() == 89_152


def test_coordinate_supply_seed_is_stable_and_partitioned() -> None:
    first = coordinate_supply_seed("alice_308_p05_p13_d04", 0, 0)
    assert first == coordinate_supply_seed("alice_308_p05_p13_d04", 0, 0)
    assert first != coordinate_supply_seed("alice_308_p05_p13_d04", 0, 1)
    assert first != coordinate_supply_seed("alice_308_p05_p13_d04", 1, 0)
    assert first != coordinate_supply_seed("alice_308_p09_p13_d08", 0, 0)


def test_coordinate_supply_retains_every_unique_restart_and_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cipher_development.two_period_overlay.coordinate_supply as supply

    benchmark = benchmark_for("alice_308_p05_p13_d04")
    particular, basis, variables = _linear_fixture(benchmark)
    monkeypatch.setattr(supply, "SUPPLY_RESTARTS", 4)
    monkeypatch.setattr(supply, "SUPPLY_SWEEPS", 3)
    monkeypatch.setattr(supply, "SUPPLY_SEED_BLOCK", 2)
    monkeypatch.setattr(supply, "SUPPLY_WALLCLOCK_LIMIT_S", 30.0)

    outcome = run_coordinate_supply(
        _target_evaluator(variables),
        particular,
        basis,
        benchmark,
    )

    assert outcome.generated_candidates == 4
    assert outcome.unique_candidates == 1
    assert outcome.duplicate_candidates == 3
    assert len(outcome.pool_archive.records) == 1
    assert len(outcome.restart_rows) == 4
    for index, row in enumerate(outcome.restart_rows):
        assert row["restart_index"] == index
        assert row["restart_seed"] == coordinate_supply_seed(
            benchmark.benchmark_id, 2, index
        )
        assert row["evaluations_used"] > 0
        assert 1 <= row["sweeps_completed"] <= 3
        record = outcome.pool_archive.get(row["candidate_id"])
        assert record.provenance.details["restart_index"] == 0
        assert record.provenance.details["benchmark_id"] == benchmark.benchmark_id

    diagnostics = discovery_diagnostics(
        outcome.pool_archive, outcome.restart_rows
    )
    names = write_coordinate_supply_artifacts(tmp_path, outcome, diagnostics)
    assert set(names) == {
        "discovery_pool_archive",
        "coordinate_archive",
        "discovery_restarts",
        "discovery_diagnostics",
    }
    restored = read_candidate_archive(tmp_path / names["discovery_pool_archive"])
    assert restored.get(outcome.best_candidate_id)
    assert diagnostics["exact_duplicate_count"] == 3
    assert diagnostics["candidate_count"] == 1


def test_discovery_diagnostics_are_order_independent_and_hand_checked() -> None:
    benchmark = benchmark_for("alice_308_p05_p13_d04")
    particular, basis, _variables = _linear_fixture(benchmark)
    variables = (
        np.asarray([0, 0, 0, 0], dtype=np.uint8),
        np.asarray([1, 0, 0, 0], dtype=np.uint8),
        np.asarray([1, 1, 0, 0], dtype=np.uint8),
    )
    records = [
        _candidate_record(
            value,
            score,
            particular,
            basis,
            benchmark,
            evaluation_index=index,
            details={"restart_index": index},
        )
        for index, (value, score) in enumerate(
            zip(variables, (1.0, 2.0, 3.0), strict=True)
        )
    ]
    first = CandidateArchive(ArchivePolicy(3, DECISION_SCORE))
    second = CandidateArchive(ArchivePolicy(3, DECISION_SCORE))
    for record in records:
        first.offer(record)
    for record in reversed(records):
        second.offer(record)
    restart_rows = [{"candidate_id": record.candidate_id} for record in records]

    first_diagnostics = discovery_diagnostics(first, restart_rows)
    second_diagnostics = discovery_diagnostics(
        second, list(reversed(restart_rows))
    )

    assert first_diagnostics == second_diagnostics
    assert first_diagnostics["nearest_neighbour_summary"] == {
        "minimum": 1,
        "median": 1.0,
        "maximum": 1,
    }
    assert first_diagnostics["exact_duplicate_count"] == 0
    entropies = [
        row["entropy_bits"]
        for row in first_diagnostics["coordinate_coverage"]
    ]
    assert entropies[:2] == pytest.approx([0.9182958340544896] * 2)
    assert entropies[2:] == [0.0, 0.0]


def test_supply_artifacts_and_diagnostics_are_truth_free() -> None:
    source = Path(__file__).resolve().parents[2]
    for relative in (
        Path("cipher_development/two_period_overlay/coordinate_supply.py"),
        Path("cipher_development/two_period_overlay/diagnostics.py"),
    ):
        text = (source / relative).read_text(encoding="utf-8")
        for token in ("os.environ", "os.getenv", "sys.argv", "argparse"):
            assert token not in text
    assert "true_key" not in coordinate_supply_outcome_fields()


def coordinate_supply_outcome_fields() -> set[str]:
    from cipher_development.two_period_overlay.coordinate_supply import (
        CoordinateSupplyOutcome,
    )

    return set(CoordinateSupplyOutcome.__dataclass_fields__)
