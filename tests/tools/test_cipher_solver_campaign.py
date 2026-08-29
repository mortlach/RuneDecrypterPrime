from __future__ import annotations
import importlib
import json
from dataclasses import replace
from pathlib import Path
from rdp import api
import pytest
from tests._helpers.reports import completed_status, make_solver_report

pytestmark = pytest.mark.tier_a
ROOT = Path(__file__).resolve().parents[2]
LM_ROOT = ROOT / "assets" / "language_model"


def _campaign():
    return importlib.import_module("tools.robustness.cipher_solver_campaign")


def _result(
    case,
    *,
    plaintext=None,
    key=None,
    stop_reason="work_limit",
    execution_status="completed",
    score=0.5,
):
    recovered_plaintext = tuple(case.reference if plaintext is None else plaintext)
    recovered_key = tuple((case.expected_key or []) if key is None else key)
    reason = (
        api.advanced.StopReason.TARGET_SCORE_REACHED
        if stop_reason == "target_score"
        else api.advanced.StopReason.CONFIGURED_WORK_LIMIT_REACHED
    )
    status = completed_status(reason, runtime_reason=stop_reason)
    if execution_status != "completed":
        status = api.RunStatus(
            execution_status=api.advanced.ExecutionStatus.ERROR,
            stop_category=api.advanced.StopCategory.ERROR,
            stop_reason=api.advanced.StopReason.UNEXPECTED_EXCEPTION,
        )
    report = make_solver_report(
        requested_seed=11,
        effective_seed=11,
        status=status,
        best_key=recovered_key,
        best_score=score,
    )
    return api.RunResult(
        plaintext=recovered_plaintext,
        plaintext_text=None,
        key=recovered_key,
        score=score,
        status=status,
        solver_report=report,
        scorer_report=api.advanced.ScorerReport(
            objective=api.advanced.ScoringObjective.percentile_log_probability(
                window_size=10
            ),
            score=score,
        ),
        configuration=api.advanced.RunConfigurationReport(
            solver=report.parameters,
            scoring=api.advanced.ConfigurationResolution(),
            cipher=api.advanced.ConfigurationResolution(),
        ),
        reproducibility=api.advanced.ReproducibilityMetadata(),
        oracle=api.advanced.OracleReport(),
    )


def test_registry_uses_central_groups_and_registered_builders() -> None:
    campaign = _campaign()
    campaign.validate_campaign_recipes(tuple(campaign.FAMILIES))
    assert set(campaign.FAMILIES) == set(campaign.config.FAMILY_GROUPS)
    assert set(campaign.FAMILIES) == set(campaign.config.CAMPAIGN_RECIPES)
    recipe_ids = [
        recipe.recipe_id for recipe in campaign.config.CAMPAIGN_RECIPES.values()
    ]
    assert len(recipe_ids) == len(set(recipe_ids))
    assert all(
        (definition.name == name for name, definition in campaign.FAMILIES.items())
    )
    assert campaign.FAMILIES["autokey_beam"].group == "STANDARD"
    assert campaign.FAMILIES["two_period_cribs"].group == "SPECIALIST"
    assert campaign.FAMILIES["vigenere_beam"].group == "STANDARD"


def test_recipe_validator_rejects_duplicate_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = _campaign()
    changed = replace(
        campaign.config.CAMPAIGN_RECIPES["mono_ga"],
        recipe_id=campaign.config.CAMPAIGN_RECIPES["vigenere_beam"].recipe_id,
    )
    monkeypatch.setitem(campaign.config.CAMPAIGN_RECIPES, "mono_ga", changed)
    with pytest.raises(ValueError, match="recipe_id values must be unique"):
        campaign.validate_campaign_recipes(tuple(campaign.FAMILIES))


def test_recipe_validator_rejects_non_positive_attempt_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = _campaign()
    changed = replace(campaign.config.CAMPAIGN_RECIPES["mono_ga"], attempt_count=0)
    monkeypatch.setitem(campaign.config.CAMPAIGN_RECIPES, "mono_ga", changed)
    with pytest.raises(ValueError, match="attempt_count must be positive"):
        campaign.validate_campaign_recipes(tuple(campaign.FAMILIES))


def test_direction_schedule_can_balance_ltr_and_rtl() -> None:
    campaign = _campaign()
    scheduled = [campaign.trial_direction(index).value for index in range(4)]
    assert scheduled.count("left_to_right") == 2
    assert scheduled.count("right_to_left") == 2


def test_campaign_mode_selects_trial_count_from_config() -> None:
    campaign = _campaign()
    assert (
        campaign.campaign_trial_count("pilot")
        == campaign.config.PILOT_TRIALS_PER_ORDINARY_FAMILY
    )
    assert (
        campaign.campaign_trial_count("full") == campaign.config.FULL_TRIALS_PER_FAMILY
    )
    with pytest.raises(ValueError, match="unknown campaign mode"):
        campaign.campaign_trial_count("unknown")


@pytest.mark.parametrize(
    "family", ("railfence_beam", "vigenere_interruptors_beam", "mono_ga")
)
def test_full_family_plan_contains_exactly_twenty_cases(family: str) -> None:
    campaign = _campaign()
    plan = campaign.campaign_plan("full", family)
    assert plan == [(family, index) for index in range(20)]
    assert all((name != "two_period_cribs" for name, _ in plan))


def test_mono_canonical_recipe_contract_is_exact() -> None:
    campaign = _campaign()
    recipe = campaign.resolved_recipe("mono_ga")
    case = campaign.build_case("mono_ga", 0)
    assert recipe.recipe_id == "mono_char2_wli12_3start_v1"
    assert recipe.scoring == campaign.config.MONO_SCORING
    assert recipe.solver == campaign.config.GeneticPlan(
        128, 160, 0.08, 0.85, 0.25, 4, 30, 160, 2
    )
    assert recipe.attempt_count == 3
    assert recipe.selection == "highest_valid_solver_score"
    assert recipe.acceptance == campaign.config.AcceptanceRule(0.97)
    assert case.solver.seed == campaign.attempt_seed("mono_ga", 0, 0)
    assert case.solver.parameters["population_size"] == 128
    assert case.solver.parameters["generations"] == 160
    assert dict(case.scoring.character_order_weights or {}) == {2: 0.3}
    assert dict(case.scoring.word_length_order_weights or {}) == {1: 0.21, 2: 0.49}


def test_qualification_status_is_group_and_mode_aware() -> None:
    campaign = _campaign()
    standard_review = {"classification": "REVIEW", "campaign_group": "STANDARD"}
    development_review = {"classification": "REVIEW", "campaign_group": "DEVELOPMENT"}
    specialist_review = {"classification": "REVIEW", "campaign_group": "SPECIALIST"}
    failure = {"classification": "FAIL", "campaign_group": "DEVELOPMENT"}
    assert campaign.qualification_exit_code([standard_review], "pilot") == 0
    assert campaign.qualification_exit_code([development_review], "full") == 0
    assert campaign.qualification_exit_code([standard_review], "full") == 1
    assert campaign.qualification_exit_code([specialist_review], "full") == 1
    assert campaign.qualification_exit_code([failure], "pilot") == 1


def test_trial_and_attempt_seeds_are_repeatable_and_namespaced() -> None:
    campaign = _campaign()
    trial = campaign.trial_seed("vigenere_beam", 0)
    assert trial == campaign.trial_seed("vigenere_beam", 0)
    assert trial != campaign.trial_seed("vigenere_beam", 1)
    assert trial != campaign.trial_seed("railfence_beam", 0)
    assert campaign.attempt_seed("vigenere_beam", 0, 0) == trial
    assert campaign.attempt_seed("vigenere_beam", 0, 1) == campaign.attempt_seed(
        "vigenere_beam", 0, 1
    )
    assert campaign.attempt_seed("vigenere_beam", 0, 1) != trial


def test_autokey_solver_rename_preserves_the_problem_stream() -> None:
    campaign = _campaign()
    assert campaign.case_seed_namespace("autokey_beam") == "autokey_ga"
    assert campaign.case_seed_namespace("vigenere_beam") == "vigenere_beam"


def test_same_trial_reconstructs_same_problem_with_new_attempt_seed() -> None:
    campaign = _campaign()
    first = campaign.build_case("vigenere_beam", 0, 0)
    repeated = campaign.build_case("vigenere_beam", 0, 0)
    retry = campaign.build_case("vigenere_beam", 0, 1)
    assert first.reference == repeated.reference == retry.reference
    assert first.ciphertext == repeated.ciphertext == retry.ciphertext
    assert (
        first.cipher_parameters == repeated.cipher_parameters == retry.cipher_parameters
    )
    assert first.source == repeated.source == retry.source


@pytest.mark.parametrize(
    "family",
    (
        "vigenere_beam",
        "railfence_beam",
        "autokey_beam",
        "columnar_hybrid",
        "mono_ga",
        "vigenere_interruptors_beam",
        "generic_map_multiply_beam",
        "scheduled_stream_beam",
    ),
)
def test_registered_ordinary_cases_retain_wli(family: str) -> None:
    campaign = _campaign()
    case = campaign.build_case(family, 0)
    assert len(case.reference) == len(case.wli)
    assert 270 <= len(case.reference) <= 330
    assert case.scoring.word_length_lane_enabled is True
    assert "stop_score" not in case.solver_parameters


def test_configured_difficulty_minima_are_respected() -> None:
    campaign = _campaign()
    for family, field in (
        ("vigenere_beam", "key_length"),
        ("generic_map_multiply_beam", "key_length"),
        ("scheduled_stream_beam", "period"),
        ("columnar_hybrid", "columns"),
    ):
        case = campaign.build_case(family, 0)
        minimum = min(campaign.config.CIPHER_RANGES[family].values())[0]
        assert case.cipher_parameters[field] >= minimum


def test_autokey_uses_the_qualified_beam_and_wli_profile() -> None:
    campaign = _campaign()
    case = campaign.build_case("autokey_beam", 0)
    assert case.solver.kind is api.advanced.SolverKind.BEAM_SEARCH
    assert case.solver.parameters["restarts"] == 3
    assert case.scoring.character_lane_enabled is False
    assert case.scoring.word_length_lane_enabled is True
    assert dict(case.scoring.character_order_weights or {}) == {}
    assert dict(case.scoring.word_length_order_weights or {}) == {1: 0.3, 2: 0.7}


@pytest.mark.full_assets
@pytest.mark.skipif(
    not LM_ROOT.exists(), reason="requires the external language-model asset bundle"
)
def test_mono_asset_provenance_covers_exact_effective_lanes() -> None:
    campaign = _campaign()
    provenance = campaign.language_model_asset_provenance("mono_ga")
    assert provenance["asset_profile"] == "ci_light"
    assert provenance["language_model_lanes"] == {"char": [2], "wli": [1, 2]}
    assert len(provenance["language_model_assets"]) == 13
    assert len(provenance["language_model_assets_sha256"]) == 64
    for asset in provenance["language_model_assets"]:
        assert not Path(asset["logical_path"]).is_absolute()
        assert len(asset["sha256"]) == 64
        assert asset["size_bytes"] > 0


def test_runtime_provenance_fingerprints_native_scorer() -> None:
    campaign = _campaign()
    provenance = campaign.runtime_provenance()
    assert provenance["python_version"]
    assert provenance["numpy_version"]
    assert provenance["zstandard_version"]
    assert provenance["fastlm_filename"].startswith("_fastlm")
    assert len(provenance["fastlm_sha256"]) == 64
    assert len(provenance["runtime_fingerprint"]) == 64


def test_truth_not_target_score_controls_classification() -> None:
    campaign = _campaign()
    case = campaign.build_case("vigenere_beam", 0)
    wrong = list(case.reference)
    wrong[0] = (wrong[0] + 1) % 29
    assessment = campaign.assess_result(
        case, _result(case, plaintext=wrong, stop_reason="target_score")
    )
    assert assessment["classification"] == "REVIEW"
    assert assessment["truth_accepted"] is False


def test_non_completed_execution_is_invalid_even_with_exact_truth() -> None:
    campaign = _campaign()
    case = campaign.build_case("vigenere_beam", 0)
    assessment = campaign.assess_result(
        case, _result(case, execution_status="interrupted")
    )
    assert assessment["classification"] == "FAIL"
    assert assessment["truth_accepted"] is True


def test_family_key_equivalence_handles_rtl_and_undefined_families() -> None:
    campaign = _campaign()
    case = campaign.build_case("vigenere_beam", 1)
    expected = list(case.expected_key or [])
    shift = len(case.reference) % len(expected)
    transformed = list(reversed(expected))
    transformed = transformed[-shift:] + transformed[:-shift]
    assessment = campaign.assess_result(case, _result(case, key=transformed))
    assert assessment["key_equivalent"] is True
    assert campaign.FAMILIES["railfence_beam"].key_equivalence is None
    assert campaign.FAMILIES["mono_ga"].key_equivalence is None


def test_interruptor_pass_requires_structural_truth() -> None:
    campaign = _campaign()
    case = campaign.build_case("vigenere_interruptors_beam", 0)
    exact_key = [*(case.expected_key or []), *(case.expected_interruptors or [])]
    accepted = campaign.assess_result(case, _result(case, key=exact_key))
    wrong = campaign.assess_result(case, _result(case, key=case.expected_key))
    assert accepted["classification"] == "PASS"
    assert accepted["interruptor_match"] is True
    assert wrong["classification"] == "REVIEW"
    assert wrong["interruptor_match"] is False


def test_specialist_adapter_supplies_ciphertext_and_wli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = _campaign()
    case = campaign.build_case("two_period_cribs", 0)
    captured = {}

    def fake_run(spec):
        captured["spec"] = spec
        return object()

    monkeypatch.setattr(campaign.api, "run", fake_run)
    campaign.execute_case(case)
    spec = captured["spec"]
    assert spec.problem_input == api.RuneIndexInput(
        indices=case.ciphertext, word_lengths=case.wli
    )


def test_exceptions_become_fail_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    campaign = _campaign()
    monkeypatch.setattr(
        campaign,
        "build_case",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("broken")),
    )
    record = campaign.run_trial("vigenere_beam", 0)
    assert record["classification"] == "FAIL"
    assert record["attempts"][0]["notes"] == "RuntimeError: broken"


def test_multiple_attempt_pipeline_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = _campaign()
    calls = 0

    def fake_execute(case):
        nonlocal calls
        index = calls
        calls += 1
        plaintext = list(case.reference)
        if index == 0:
            plaintext[:20] = [(value + 1) % 29 for value in plaintext[:20]]
        return _result(case, plaintext=plaintext, score=(0.9, 0.1, 0.5)[index])

    monkeypatch.setattr(campaign, "execute_case", fake_execute)
    record = campaign.run_trial("mono_ga", 0)
    assert record["attempt_count"] == 3
    assert len(set(record["attempt_seeds"])) == 3
    assert len(record["attempts"]) == 3
    assert record["selected_attempt"] == 0
    assert record["classification"] == "REVIEW"
    assert record["selection_policy"] == "highest_valid_solver_score"
    assert record["truth_used_for_selection"] is False
    assert record["recipe_id"] == "mono_char2_wli12_3start_v1"
    assert record["recipe_fingerprint"] == campaign.recipe_fingerprint("mono_ga")
    assert record["configuration_fingerprint"] == campaign.configuration_fingerprint(
        "mono_ga", "pilot"
    )
    assert record["scorer_profile"]["wli_weights"] == {1: 0.21, 2: 0.49}


def test_multiple_attempt_selection_uses_score_not_benchmark_truth() -> None:
    campaign = _campaign()
    exact_lower_score = {
        "attempt_index": 0,
        "valid": True,
        "classification": "PASS",
        "match_ratio": 1.0,
        "best_score": 0.4,
    }
    wrong_higher_score = {
        "attempt_index": 1,
        "valid": True,
        "classification": "REVIEW",
        "match_ratio": 0.5,
        "best_score": 0.5,
    }
    assert (
        max((exact_lower_score, wrong_higher_score), key=campaign._selection_key)
        is wrong_higher_score
    )


def test_multiple_attempt_selection_prefers_valid_and_breaks_score_ties_early() -> None:
    campaign = _campaign()
    invalid = {"attempt_index": 0, "valid": False, "best_score": 1.0}
    first = {"attempt_index": 1, "valid": True, "best_score": 0.5}
    tied_later = {"attempt_index": 2, "valid": True, "best_score": 0.5}
    assert max((invalid, first, tied_later), key=campaign._selection_key) is first


def test_output_is_external_and_jsonl_schema_is_exact(tmp_path: Path) -> None:
    campaign = _campaign()
    output_path = campaign.qualification_output_path("full", "mono_ga")
    assert not output_path.is_relative_to(ROOT)
    assert output_path.name == "full_mono_char2_wli12_3start_v1_seed20260822.jsonl"
    record = campaign.failure_record("vigenere_beam", 0, 7, RuntimeError("broken"), 0.5)
    assert set(record) == set(campaign.RESULT_FIELDS)
    output = tmp_path / "result.jsonl"
    campaign.write_records([record], output)
    assert json.loads(output.read_text(encoding="utf-8")) == json.loads(
        json.dumps(record)
    )
    campaign.append_record(record, output)
    assert len(output.read_text(encoding="utf-8").splitlines()) == 2


def test_resume_repairs_partial_tail_without_duplicate_trials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _campaign()
    monkeypatch.setattr(campaign, "OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(
        campaign,
        "source_state",
        lambda: {
            "source_dirty": False,
            "tracked_dirty": False,
            "untracked_runtime_files": [],
            "source_diff_sha256": None,
        },
    )
    monkeypatch.setattr(
        campaign, "campaign_plan", lambda mode, family: [(family, 0), (family, 1)]
    )
    monkeypatch.setattr(
        campaign,
        "language_model_asset_provenance",
        lambda family: {
            "asset_profile": "test",
            "language_model_lanes": {},
            "language_model_assets": [],
            "language_model_assets_sha256": "0" * 64,
        },
    )
    calls: list[int] = []

    def fake_trial(family: str, trial_index: int, mode: str | None = None):
        calls.append(trial_index)
        return campaign.failure_record(
            family,
            trial_index,
            campaign.trial_seed(family, trial_index),
            RuntimeError("synthetic preflight"),
            0.0,
            mode=mode,
        )

    monkeypatch.setattr(campaign, "run_trial", fake_trial)
    output = campaign.qualification_output_path("full", "railfence_beam")
    arguments = ["--mode", "full", "--family", "railfence_beam"]
    assert campaign.main(arguments) == 1
    initial = campaign.load_completed_records(output)
    assert [record["trial_id"] for record in initial] == [
        "railfence_beam.0",
        "railfence_beam.1",
    ]
    campaign.write_records(initial[:1], output)
    with output.open("ab") as handle:
        handle.write(b'{"trial_id":"railfence_beam.1"')
    calls.clear()
    assert campaign.main([*arguments, "--resume"]) == 1
    resumed = campaign.load_completed_records(output)
    assert calls == [1]
    assert [record["trial_id"] for record in resumed] == [
        "railfence_beam.0",
        "railfence_beam.1",
    ]
    assert campaign.main(arguments) == 2


def test_loader_rejects_duplicate_completed_trial_ids(tmp_path: Path) -> None:
    campaign = _campaign()
    record = campaign.failure_record(
        "railfence_beam", 0, 7, RuntimeError("synthetic preflight"), 0.0
    )
    output = tmp_path / "duplicates.jsonl"
    campaign.write_records([record, record], output)
    with pytest.raises(ValueError, match="duplicate completed trial IDs"):
        campaign.load_completed_records(output)


def test_resume_refuses_different_recipe_fingerprint(tmp_path: Path) -> None:
    campaign = _campaign()
    output = tmp_path / "fingerprint.jsonl"
    provenance = {
        "git_commit": "head",
        "runner_sha256": "runner",
        "config_sha256": "config",
        "recipe_id": "recipe",
        "recipe_fingerprint": "accepted",
        "configuration_fingerprint": "configuration",
        "campaign_configuration_sha256": "campaign",
        "output": str(output),
    }
    campaign.initialise_run(output=output, provenance=provenance, resume=False)
    changed = {**provenance, "recipe_fingerprint": "different"}
    with pytest.raises(ValueError, match="recipe_fingerprint"):
        campaign.initialise_run(output=output, provenance=changed, resume=True)


def test_full_provenance_refuses_dirty_runtime_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _campaign()
    monkeypatch.setattr(
        campaign,
        "source_state",
        lambda: {
            "source_dirty": True,
            "tracked_dirty": True,
            "untracked_runtime_files": [],
            "source_diff_sha256": "dirty",
        },
    )
    with pytest.raises(RuntimeError, match="clean runtime source tree"):
        campaign.build_provenance(
            mode="full",
            family="mono_ga",
            output=tmp_path / "result.jsonl",
            plan=[("mono_ga", 0)],
            command=["python", "campaign.py"],
        )


def test_resume_refuses_different_language_model_assets(tmp_path: Path) -> None:
    campaign = _campaign()
    output = tmp_path / "asset_fingerprint.jsonl"
    provenance = {
        "git_commit": "head",
        "source_diff_sha256": None,
        "runner_sha256": "runner",
        "config_sha256": "config",
        "recipe_id": "recipe",
        "recipe_fingerprint": "recipe-fingerprint",
        "configuration_fingerprint": "configuration",
        "campaign_configuration_sha256": "campaign",
        "asset_profile": "ci_light",
        "asset_profile_manifest_sha256": "profile",
        "asset_verification_manifest_sha256": "manifest",
        "language_model_assets_sha256": "accepted",
        "output": str(output),
    }
    campaign.initialise_run(output=output, provenance=provenance, resume=False)
    changed = {**provenance, "language_model_assets_sha256": "different"}
    with pytest.raises(ValueError, match="language_model_assets_sha256"):
        campaign.initialise_run(output=output, provenance=changed, resume=True)
