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
    solver_params_for_run,
    tile_text_and_wli,
    validate_structured_key,
)
from cipher_development.periodic_sub_trans_wli.config import (
    ALPHABET_SIZE,
    ARCHIVE_CAPACITY,
    CANARY_CASES,
    KAEDING_SOLVER_CONTRACT,
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
from cipher_development.periodic_sub_trans_wli.run import (
    _archive_reference_metrics,
    _case_configuration,
)
from cipher_development.periodic_sub_trans_wli.search import (
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
    return np.concatenate([*blocks, tail])


def _budget(**overrides) -> RunBudget:
    values = dict(
        candidate_pool_size=8,
        handoff_candidates=2,
        exploitation_replicates=1,
        solver_restarts=1,
        solver_steps=4,
        solver_inner_batch=2,
        minimum_policy_exclusive=1,
        minimum_completed_target_cases=1,
        minimum_completed_positive_controls=1,
        wallclock_overrun_limit_s=60.0,
        seed_plan=SeedPoolPlan(2, 2, 8, 0, 0.4, 0.05, 0.01),
    )
    values.update(overrides)
    return RunBudget(**values)


def _case(*, calls: list[tuple[int, int]] | None = None) -> SearchCase:
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
        return raw, -raw

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


def test_fixed_campaign_contract() -> None:
    assert (POSITIVE_CONTROL.period, POSITIVE_CONTROL.columns, POSITIVE_CONTROL.length) == (7, 5, 400)
    assert (TARGET_CASE.period, TARGET_CASE.columns, TARGET_CASE.length) == (13, 13, 300)
    assert CANARY_CASES == (POSITIVE_CONTROL, TARGET_CASE)
    assert ORDER == "col_then_sub" and ALPHABET_SIZE == 29
    assert WLI_SCORING_CONTRACT["use_word_breaks"] is True
    assert RAW_SCORING_CONTRACT["use_word_breaks"] is False
    assert not WLI_SCORING_CONTRACT["hard_crib"]
    assert RUN_BUDGETS["full"].candidate_pool_size == ARCHIVE_CAPACITY
    assert RUN_BUDGETS["full"].solver_restarts == 1
    assert RUN_BUDGETS["full"].exploitation_replicates == 2
    assert KAEDING_SOLVER_CONTRACT["use_raw_score"] is False
    assert KAEDING_SOLVER_CONTRACT["seed_selection_metric"] == "pct"
    assert KAEDING_SOLVER_CONTRACT["seed_restarts"] == 1


def test_whole_word_tiling_and_resolution() -> None:
    plaintext = [4, 5, 6]
    wli = [(0, 2), (1, 2), (0, 1)]
    tiled_plaintext, tiled_wli = tile_text_and_wli(plaintext, wli, minimum_length=8)
    assert tiled_plaintext.tolist() == plaintext * 3
    assert tiled_wli == tuple(wli) * 3
    assert resolve_whole_word_slice(tiled_wli, length=3, offset_hint=4) == 5
    with pytest.raises(ValueError):
        resolve_whole_word_slice([(0, 3), (2, 3), (1, 3)], length=3, offset_hint=0)


def test_truth_and_candidate_seeds_are_separated() -> None:
    assert np.array_equal(
        deterministic_truth_key(POSITIVE_CONTROL),
        deterministic_truth_key(POSITIVE_CONTROL),
    )
    first = candidate_generation_seed(period=13, columns=13, length=300, sample_start=0)
    second = candidate_generation_seed(period=13, columns=13, length=300, sample_start=0)
    assert first == second
    payload = _case_configuration(POSITIVE_CONTROL)
    assert all("truth" not in key and "key_seed" not in key for key in payload)
    assert set(SearchCase.__dataclass_fields__).isdisjoint({"plaintext", "true_key", "truth"})


@pytest.mark.parametrize("bad", [1.5, float("nan"), True, 100_000])
def test_structured_key_rejects_noncanonical_values(bad) -> None:
    key = _key(2, 3, 0).astype(object)
    key[0] = bad
    expected = (TypeError, ValueError) if bad is True else ValueError
    with pytest.raises(expected):
        validate_structured_key(
            key,
            period=2,
            columns=3,
            permutation_validator=_assert_perm,
        )


def test_structured_key_rejects_invalid_permutations() -> None:
    key = _key(2, 3, 0)
    key[0] = key[1]
    with pytest.raises(AssertionError):
        validate_structured_key(key, period=2, columns=3, permutation_validator=_assert_perm)


def test_scorer_and_solver_contracts_materialise() -> None:
    class Direction:
        def __init__(self, value):
            self.value = value

    kwargs = scoring_kwargs(WLI_SCORING_CONTRACT, Direction)
    assert kwargs["objective"] == "pct.logp.win10"
    assert kwargs["encoding_dir"].value == "ltr"
    assert kwargs["hard_crib"] is None
    params = scorer_params_for_run(WLI_SCORING_CONTRACT)
    assert params["compute_dtype"] == "float32"
    assert params["ecdf_clamp_min"] == 1e-6
    solver = solver_params_for_run(_budget(), 123)
    assert solver["seed"] == 123 and solver["restarts"] == 1
    assert solver["use_raw_score"] is False
    assert solver["seed_selection_metric"] == "pct"


def test_seed_pool_and_ranking_are_deterministic() -> None:
    first_wli, first_raw, first_evidence = generate_seed_pool(_case(), _budget())
    second_wli, second_raw, second_evidence = generate_seed_pool(_case(), _budget())
    assert [r.candidate_id for r in first_wli.records] == [r.candidate_id for r in second_wli.records]
    assert {r.candidate_id for r in first_wli.records} == {r.candidate_id for r in first_raw.records}
    assert {r.candidate_id for r in second_wli.records} == {r.candidate_id for r in second_raw.records}
    assert first_evidence == second_evidence
    assert first_evidence.last_retained_improvement_evaluation == 1
    wli_batch, raw_batch, selection = select_ranking_batches(first_wli, first_raw, _budget())
    assert wli_batch.candidate_ids != raw_batch.candidate_ids
    assert selection.ranking_test_valid
    assert all(rank > 0 for rank in selection.raw_rank_of_wli.values())
    assert max(selection.raw_rank_of_wli.values()) > len(raw_batch.candidate_ids)


def test_overlap_is_executed_once_and_final_evidence_is_replayable(tmp_path: Path) -> None:
    calls: list[tuple[int, int]] = []
    outcome = run_case(_case(calls=calls), _budget(handoff_candidates=4))
    union = set(outcome.raw_handoff_batch.candidate_ids) | set(outcome.wli_handoff_batch.candidate_ids)
    assert len(calls) == len(union) == len(outcome.exploitation_rows)
    retained = {
        record.candidate_id
        for archive in (outcome.raw_final_archive, outcome.wli_final_archive)
        for record in archive.records
    }
    assert outcome.best_candidate_id in retained
    for archive in (outcome.raw_final_archive, outcome.wli_final_archive):
        assert all(len(record.provenance.parent_ids) == 1 for record in archive.records)
    names = write_case_artifacts(tmp_path, outcome)
    assert read_candidate_archive(tmp_path / names["seed_pool_archive"]).records
    assert read_candidate_archive(tmp_path / names["raw_final_archive"]).records
    assert read_candidate_archive(tmp_path / names["wli_final_archive"]).records
    assert read_candidate_batch(tmp_path / names["raw_handoff_batch"]).candidates
    assert read_candidate_batch(tmp_path / names["wli_handoff_batch"]).candidates


def test_summary_and_decision_require_valid_positive_controls() -> None:
    summary = case_summary(_case(), run_case(_case(), _budget()))
    assert "expanded_key" not in repr(summary)
    assert panel_decision([summary], "canary", _budget()) == "refine"
    target = {
        "valid": True,
        "family": "target",
        "wli_best_advantage": 1.0,
        "wli_median_advantage": 0.5,
    }
    control = {
        "valid": True,
        "family": "positive_control",
        "wli_best_advantage": 0.0,
        "wli_median_advantage": 0.0,
    }
    assert panel_decision([target], "full", _budget()) == "refine"
    assert panel_decision([target, control], "full", _budget()) == "promote"
    invalid_control = {**control, "valid": False}
    assert panel_decision([target, invalid_control], "full", _budget()) == "refine"


def test_budget_validation_and_source_policy() -> None:
    with pytest.raises(ValueError):
        _budget(candidate_pool_size=ARCHIVE_CAPACITY + 1)
    with pytest.raises(ValueError):
        _budget(handoff_candidates=9)
    with pytest.raises(ValueError, match="one seeded solver restart"):
        _budget(solver_restarts=2)
    root = Path(__file__).resolve().parents[2]
    for relative in (
        "cipher_development/periodic_sub_trans_wli/config.py",
        "cipher_development/periodic_sub_trans_wli/benchmark.py",
        "cipher_development/periodic_sub_trans_wli/search.py",
        "cipher_development/periodic_sub_trans_wli/run.py",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        assert not any(token in text for token in ("os.environ", "os.getenv", "sys.argv", "argparse"))


def test_search_callbacks_do_not_capture_truth_spec() -> None:
    case = _case()
    for callback in (case.validate_key, case.generate_seed_keys, case.score_keys, case.exploit_key):
        cells = tuple(cell.cell_contents for cell in (callback.__closure__ or ()))
        assert not any(isinstance(value, BenchmarkSpec) for value in cells)
        assert "truth_key_seed" not in repr(cells)


def test_reference_metrics_cover_every_unique_final_candidate() -> None:
    class Cipher:
        def decrypt_single(self, *, ciphertext, key):
            return np.asarray(key[: len(ciphertext)], dtype=np.uint8)

    reference = ReferenceCase(
        cipher=Cipher(),
        plaintext=np.asarray([0, 1, 2], dtype=np.uint8),
        ciphertext=np.asarray([8, 8, 8], dtype=np.uint8),
        wli=((0, 3), (1, 3), (2, 3)),
        true_key=np.asarray([0, 1, 2], dtype=np.int16),
    )
    outcome = run_case(_case(), _budget())
    metrics = _archive_reference_metrics(reference, outcome.wli_final_archive)
    assert metrics["candidate_count"] == len(outcome.wli_final_archive.records)
    assert set(metrics["candidates"]) == {
        record.candidate_id for record in outcome.wli_final_archive.records
    }


def _real_case(spec):
    pytest.importorskip("rune_decrypter_prime")
    try:
        return build_rdp_case(spec, RUN_BUDGETS["canary"])
    except FileNotFoundError as exc:
        pytest.skip(f"full RDP language-model assets are unavailable: {exc}")


def test_real_rdp_positive_control_constructs_and_scores() -> None:
    case, _reference = _real_case(POSITIVE_CONTROL)
    keys = case.generate_seed_keys(2)
    raw, wli = case.score_keys(keys)
    assert len(keys) == 2 and raw.shape == wli.shape == (2,)
    assert np.all(np.isfinite(raw)) and np.all(np.isfinite(wli))


def test_real_rdp_seed_generator_order_matches_recorded_raw_score() -> None:
    case, _reference = _real_case(POSITIVE_CONTROL)
    keys = case.generate_seed_keys(4)
    raw, _wli = case.score_keys(keys)
    assert np.all(raw[:-1] >= raw[1:] - 1e-12)


def test_real_rdp_kaeding_is_seeded_and_wli_driven() -> None:
    case, _reference = _real_case(POSITIVE_CONTROL)
    initial = case.generate_seed_keys(1)[0]
    solved = case.exploit_key(initial, 12345, RUN_BUDGETS["canary"])
    _raw, wli = case.score_keys([solved.final_key])
    assert np.isclose(solved.reported_score, wli[0], rtol=1e-6, atol=1e-8)
    kaeding = solved.telemetry["kaeding"]
    assert kaeding["seed_selection_metric"] == "pct"
    assert kaeding["seed_restarts_used"] == 1
    assert len(kaeding["restart_start_hashes"]) == 1
    assert solved.telemetry["run"]["params"]["use_raw_score"] is False


def test_real_rdp_target_case_constructs() -> None:
    case, _reference = _real_case(TARGET_CASE)
    assert (case.period, case.columns, case.length, case.order) == (13, 13, 300, ORDER)
