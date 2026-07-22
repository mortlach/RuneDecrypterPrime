from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
import pytest

from cipher_development.periodic_sub_trans_wli.benchmark import (
    ReferenceCase,
    SearchCase,
    SolverEvidence,
    build_rdp_case,
    candidate_generation_seed,
    deterministic_truth_key,
    resolve_whole_word_slice,
    scorer_params_for_run,
    scoring_kwargs,
    tile_text_and_wli,
    validate_structured_key,
)
from cipher_development.periodic_sub_trans_wli.config import (
    ALPHABET_SIZE,
    ARCHIVE_CAPACITY,
    CANARY_CASES,
    ORDER,
    POSITIVE_CONTROL,
    RAW_SCORE,
    RAW_SCORING_CONTRACT,
    RUN_BUDGETS,
    TARGET_CASE,
    WLI_SCORE,
    WLI_SCORING_CONTRACT,
    BenchmarkSpec,
    RunBudget,
    SeedPoolPlan,
)
from cipher_development.periodic_sub_trans_wli.run import _case_configuration
from cipher_development.periodic_sub_trans_wli.search import (
    candidate_record_for_key,
    case_summary,
    exploitation_seed,
    generate_seed_pool,
    panel_decision,
    run_case,
    select_ranking_batches,
    write_case_artifacts,
)
from cipher_development.shared.archive import read_candidate_archive
from cipher_development.shared.replay import read_candidate_batch


def _assert_perm(values: Sequence[int], size: int) -> None:
    assert sorted(int(value) for value in values) == list(range(size))


def _key(period: int, columns: int, shift: int) -> np.ndarray:
    blocks = [
        np.roll(np.arange(ALPHABET_SIZE, dtype=np.int16), shift + phase)
        for phase in range(period)
    ]
    tail = np.roll(np.arange(columns, dtype=np.int16), shift % columns)
    return np.concatenate([*blocks, tail]).astype(np.int16)


def _budget(**overrides) -> RunBudget:
    values = {
        "candidate_pool_size": 8,
        "handoff_candidates": 2,
        "exploitation_replicates": 1,
        "solver_restarts": 1,
        "solver_steps": 4,
        "solver_inner_batch": 2,
        "minimum_policy_exclusive": 1,
        "minimum_completed_target_cases": 1,
        "wallclock_limit_s": 60.0,
        "seed_plan": SeedPoolPlan(2, 2, 8, 0, 0.4, 0.05, 0.01),
    }
    values.update(overrides)
    return RunBudget(**values)


def _synthetic_case(*, calls: list[tuple[int, int]] | None = None) -> SearchCase:
    period, columns = 2, 3

    def validate(key):
        return validate_structured_key(
            key,
            period=period,
            columns=columns,
            permutation_validator=_assert_perm,
        )

    def generate(count: int):
        return [_key(period, columns, index) for index in range(count)]

    def score(keys):
        batch = np.asarray(keys, dtype=np.int16)
        if batch.ndim == 1:
            batch = batch[None, :]
        raw = batch[:, 0].astype(np.float64)
        wli = -raw
        return raw, wli

    def exploit(key, seed: int, budget: RunBudget):
        if calls is not None:
            calls.append((seed, budget.solver_steps))
        valid = validate(key)
        return SolverEvidence(
            final_key=tuple(int(value) for value in valid),
            reported_score=float(-valid[0]),
            evaluations=5,
            elapsed_s=0.01,
            stop_reason="max_steps",
            telemetry={"moves": 4},
        )

    return SearchCase(
        benchmark_id="synthetic_periodic_columnar",
        family="target",
        period=period,
        columns=columns,
        length=12,
        order=ORDER,
        sample_start=0,
        ciphertext=tuple(range(12)),
        wli=tuple((index % 3, 3) for index in range(12)),
        validate_key=validate,
        generate_seed_keys=generate,
        score_keys=score,
        exploit_key=exploit,
    )


def test_fixed_benchmark_contracts() -> None:
    assert (
        POSITIVE_CONTROL.period, POSITIVE_CONTROL.columns, POSITIVE_CONTROL.length
    ) == (7, 5, 400)
    assert (TARGET_CASE.period, TARGET_CASE.columns, TARGET_CASE.length) == (13, 13, 300)
    assert ORDER == "col_then_sub"
    assert ALPHABET_SIZE == 29
    assert CANARY_CASES == (POSITIVE_CONTROL, TARGET_CASE)


def test_profiles_use_full_wli_and_no_hard_crib() -> None:
    assert WLI_SCORING_CONTRACT["use_word_breaks"] is True
    assert WLI_SCORING_CONTRACT["hard_crib"] is False
    assert RAW_SCORING_CONTRACT["use_word_breaks"] is False
    assert RAW_SCORING_CONTRACT["hard_crib"] is False
    assert RUN_BUDGETS["full"].candidate_pool_size == ARCHIVE_CAPACITY


def test_whole_word_slice_resolution_rejects_broken_boundaries() -> None:
    wli = [(0, 2), (1, 2), (0, 3), (1, 3), (2, 3), (0, 1)]
    assert resolve_whole_word_slice(wli, length=5, offset_hint=0) == 0
    assert resolve_whole_word_slice(wli, length=4, offset_hint=1) == 2
    with pytest.raises(ValueError):
        resolve_whole_word_slice(wli, length=2, offset_hint=1)


def test_text_and_wli_tiling_preserves_word_boundaries() -> None:
    plaintext = [4, 5, 6]
    wli = [(0, 2), (1, 2), (0, 1)]
    tiled_plaintext, tiled_wli = tile_text_and_wli(
        plaintext, wli, minimum_length=8
    )
    assert tiled_plaintext.tolist() == plaintext * 3
    assert tiled_wli == tuple(wli) * 3
    assert resolve_whole_word_slice(tiled_wli, length=3, offset_hint=4) == 5


def test_whole_word_resolution_rejects_malformed_internal_wli() -> None:
    malformed = [(0, 3), (2, 3), (1, 3)]
    with pytest.raises(ValueError, match="complete contiguous words"):
        resolve_whole_word_slice(malformed, length=3, offset_hint=0)



def test_candidate_generation_seed_does_not_depend_on_truth_key_seed() -> None:
    first = BenchmarkSpec("a", "target", 13, 13, 300, 0, 111)
    second = BenchmarkSpec("b", "target", 13, 13, 300, 0, 222)
    assert candidate_generation_seed(first, 0) == candidate_generation_seed(second, 0)


def test_truth_key_is_deterministic_and_structurally_valid() -> None:
    first = deterministic_truth_key(POSITIVE_CONTROL)
    second = deterministic_truth_key(POSITIVE_CONTROL)
    assert np.array_equal(first, second)
    valid = validate_structured_key(
        first,
        period=POSITIVE_CONTROL.period,
        columns=POSITIVE_CONTROL.columns,
        permutation_validator=_assert_perm,
    )
    assert len(valid) == POSITIVE_CONTROL.period * ALPHABET_SIZE + POSITIVE_CONTROL.columns


def test_structured_key_validation_rejects_bad_block_and_tail() -> None:
    key = _key(2, 3, 0)
    bad_block = key.copy()
    bad_block[0] = bad_block[1]
    with pytest.raises(AssertionError):
        validate_structured_key(bad_block, period=2, columns=3, permutation_validator=_assert_perm)
    bad_tail = key.copy()
    bad_tail[-1] = bad_tail[-2]
    with pytest.raises(AssertionError):
        validate_structured_key(bad_tail, period=2, columns=3, permutation_validator=_assert_perm)


def test_scoring_kwargs_are_driven_by_contract() -> None:
    class Direction:
        def __init__(self, value):
            self.value = value

    kwargs = scoring_kwargs(WLI_SCORING_CONTRACT, Direction)
    assert kwargs["objective"] == WLI_SCORING_CONTRACT["objective"]
    assert kwargs["char_weights"] == WLI_SCORING_CONTRACT["char_weights"]
    assert kwargs["encoding_dir"].value == "ltr"
    assert kwargs["hard_crib"] is None


def test_run_scorer_params_reject_hard_crib_drift() -> None:
    assert scorer_params_for_run(WLI_SCORING_CONTRACT)["hard_crib"] is None
    with pytest.raises(ValueError, match="hard crib"):
        scorer_params_for_run({**WLI_SCORING_CONTRACT, "hard_crib": True})


def test_experiment_case_configuration_excludes_truth_seed() -> None:
    payload = _case_configuration(POSITIVE_CONTROL)
    assert payload["benchmark_id"] == POSITIVE_CONTROL.benchmark_id
    assert all("key_seed" not in key and "truth" not in key for key in payload)


def test_search_case_has_no_truth_fields() -> None:
    fields = set(SearchCase.__dataclass_fields__)
    assert fields.isdisjoint({"plaintext", "true_key", "truth", "reference"})
    assert {"plaintext", "true_key"}.issubset(ReferenceCase.__dataclass_fields__)


def test_candidate_identity_contains_structure_and_complete_key() -> None:
    case = _synthetic_case()
    key = _key(case.period, case.columns, 1)
    record = candidate_record_for_key(
        case,
        key,
        raw_score=1.0,
        wli_score=2.0,
        source="test",
        operation="seed",
        evaluation_index=1,
    )
    assert record.identity["cipher"] == "periodic_columnar"
    assert record.identity["period"] == case.period
    assert record.identity["columns"] == case.columns
    assert record.payload["expanded_key"] == key.astype(int).tolist()
    assert set(record.scores) == {RAW_SCORE, WLI_SCORE}


def test_seed_pool_is_deterministic_and_shared_between_rankings() -> None:
    case = _synthetic_case()
    first_wli, first_raw, first_evidence = generate_seed_pool(case, _budget())
    second_wli, second_raw, second_evidence = generate_seed_pool(case, _budget())
    assert [r.candidate_id for r in first_wli.records] == [
        r.candidate_id for r in second_wli.records
    ]
    assert {r.candidate_id for r in first_wli.records} == {
        r.candidate_id for r in first_raw.records
    }
    assert {r.candidate_id for r in second_wli.records} == {
        r.candidate_id for r in second_raw.records
    }
    assert first_evidence == second_evidence
    assert len(first_evidence.raw_score_distribution) == first_evidence.unique_candidates
    assert len(first_evidence.wli_score_distribution) == first_evidence.unique_candidates
    assert first_evidence.duplicate_rate == 0.0


def test_raw_and_wli_ranking_use_candidate_id_tie_breaks() -> None:
    case = _synthetic_case()
    wli_archive, raw_archive, _ = generate_seed_pool(case, _budget())
    assert [r.scores[WLI_SCORE] for r in wli_archive.records] == sorted(
        (r.scores[WLI_SCORE] for r in wli_archive.records), reverse=True
    )
    assert [r.scores[RAW_SCORE] for r in raw_archive.records] == sorted(
        (r.scores[RAW_SCORE] for r in raw_archive.records), reverse=True
    )


def test_selection_evidence_records_policy_difference() -> None:
    case = _synthetic_case()
    wli_archive, raw_archive, _ = generate_seed_pool(case, _budget())
    wli_batch, raw_batch, evidence = select_ranking_batches(wli_archive, raw_archive, _budget())
    assert len(wli_batch.candidates) == len(raw_batch.candidates) == 2
    assert evidence.raw_candidate_ids != evidence.wli_candidate_ids
    assert evidence.policy_exclusive_minimum >= 1
    assert evidence.ranking_test_valid


def test_exploitation_seed_is_stable_and_candidate_specific() -> None:
    first = exploitation_seed("case", "a" * 40, 0)
    assert first == exploitation_seed("case", "a" * 40, 0)
    assert first != exploitation_seed("case", "b" * 40, 0)
    assert first != exploitation_seed("case", "a" * 40, 1)


def test_overlapping_candidates_are_executed_once() -> None:
    calls: list[tuple[int, int]] = []
    case = _synthetic_case(calls=calls)
    outcome = run_case(case, _budget(handoff_candidates=4, minimum_policy_exclusive=1))
    union = set(outcome.raw_handoff_batch.candidate_ids) | set(
        outcome.wli_handoff_batch.candidate_ids
    )
    assert len(calls) == len(union)
    assert len(outcome.exploitation_rows) == len(union)


def test_final_candidates_preserve_parent_provenance() -> None:
    outcome = run_case(_synthetic_case(), _budget())
    for archive in (outcome.raw_final_archive, outcome.wli_final_archive):
        for record in archive.records:
            assert len(record.provenance.parent_ids) == 1
            assert record.provenance.operation == "kaeding_seeded_solve"


def test_terminal_best_candidate_is_persisted() -> None:
    outcome = run_case(_synthetic_case(), _budget())
    retained = {
        record.candidate_id
        for archive in (outcome.raw_final_archive, outcome.wli_final_archive)
        for record in archive.records
    }
    assert outcome.best_candidate_id in retained
    assert outcome.best_membership


def test_case_artifacts_round_trip(tmp_path: Path) -> None:
    outcome = run_case(_synthetic_case(), _budget())
    names = write_case_artifacts(tmp_path, outcome)
    assert set(names) == {
        "seed_pool_archive",
        "wli_handoff_batch",
        "raw_handoff_batch",
        "wli_final_archive",
        "raw_final_archive",
        "selection_evidence",
    }
    assert read_candidate_archive(tmp_path / names["seed_pool_archive"]).records
    assert read_candidate_archive(tmp_path / names["wli_final_archive"]).records
    assert read_candidate_archive(tmp_path / names["raw_final_archive"]).records
    assert read_candidate_batch(tmp_path / names["wli_handoff_batch"]).candidates
    assert read_candidate_batch(tmp_path / names["raw_handoff_batch"]).candidates


def test_case_summary_contains_no_candidate_payloads() -> None:
    case = _synthetic_case()
    summary = case_summary(case, run_case(case, _budget()))
    assert "expanded_key" not in repr(summary)
    assert summary["valid"] is True
    assert summary["raw_arm"]["completed_runs"] == 2
    assert summary["wli_arm"]["completed_runs"] == 2


def test_canary_and_underpowered_panels_refine() -> None:
    case = _synthetic_case()
    summary = case_summary(case, run_case(case, _budget()))
    assert panel_decision([summary], "canary", _budget()) == "refine"
    invalid = dict(summary)
    invalid["valid"] = False
    assert panel_decision([invalid], "full", _budget()) == "refine"


def test_full_panel_promote_and_close_rules_require_valid_targets() -> None:
    base = {
        "valid": True,
        "family": "target",
        "wli_best_advantage": 1.0,
        "wli_median_advantage": 0.5,
    }
    assert panel_decision([base], "full", _budget()) == "promote"
    closed = {**base, "wli_best_advantage": 0.0, "wli_median_advantage": 0.0}
    assert panel_decision([closed], "full", _budget()) == "close"


def test_budget_rejects_invalid_contracts() -> None:
    with pytest.raises(ValueEError):
        _budget(candidate_pool_size=ARCHIVE_CAPACITY + 1)
    with pytest.raises(ValueError):
        _budget(handoff_candidates=9)
    with pytest.raises(ValueError):
        _budget(wallclock_limit_s=0)


def test_campaign_source_uses_no_environment_or_cli_configuration() -> None:
    root = Path(__file__).resolve().parents[2]
    for relative in (
        "cipher_development/periodic_sub_trans_wli/config.py",
        "cipher_development/periodic_sub_trans_wli/benchmark.py",
        "cipher_development/periodic_sub_trans_wli/search.py",
        "cipher_development/periodic_sub_trans_wli/run.py",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        for token in ("os.environ", "os.getenv", "sys.argv", "argparse"):
            assert token not in text


def test_real_rdp_positive_control_constructs_and_scores() -> None:
    pytest.importorskip("rune_decrypter_prime")
    try:
        case, _reference = build_rdp_case(POSITIVE_CONTROL, RUN_BUDGETS["canary"])
        keys = case.generate_seed_keys(2)
        raw, wli = case.score_keys(keys)
    except FileNotFoundError as exc:
        pytest.skip(f"full RDP language-model assets are unavailable: {exc}")
    assert case.length == 400
    assert len(keys) == 2
    assert raw.shape == wli.shape == (2,)
    assert np.all(np.isfinite(raw)) and np.all(np.isfinite(wli))


def test_real_rdp_target_contract_is_declared() -> None:
    assert TARGET_CASE == BenchmarkSpec(
        benchmark_id="periodic_col_p13_c13_l300",
        family="target",
        period=13,
        columns=13,
        length=300,
        text_offset_hint=0,
        truth_key_seed=111,
    )


def test_real_rdp_target_case_constructs() -> None:
    pytest.importorskip("rune_decrypter_prime")
    try:
        case, _reference = build_rdp_case(TARGET_CASE, RUN_BUDGETS["canary"])
    except FileNotFoundError as exc:
        pytest.skip(f"full RDP language-model assets are unavailable: {exc}")
    assert (case.period, case.columns, case.length, case.order) == (13, 13, 300, ORDER)
