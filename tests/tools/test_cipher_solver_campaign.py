from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


pytestmark = pytest.mark.tier_a
ROOT = Path(__file__).resolve().parents[2]


def _campaign():
    return importlib.import_module("tools.robustness.cipher_solver_campaign")


def _result(
    case, *, plaintext=None, key=None, stop_reason="work_limit",
    execution_status="completed",
):
    solution = SimpleNamespace(
        plaintext_idx=case.reference if plaintext is None else plaintext,
        key=(case.expected_key or []) if key is None else key,
        score=0.5,
    )
    report = SimpleNamespace(
        details={"run_status": {"execution_status": execution_status}},
        stop_reason=stop_reason,
        best_score=0.5,
        evals=0,
        tokens_processed=0,
        requested_seed=11,
        effective_seed=11,
    )
    return SimpleNamespace(solution=solution, solver_report=report)


def test_registry_uses_central_groups_and_registered_builders() -> None:
    campaign = _campaign()
    assert set(campaign.FAMILIES) == set(campaign.config.FAMILY_GROUPS)
    assert all(definition.name == name for name, definition in campaign.FAMILIES.items())
    assert campaign.FAMILIES["autokey_ga"].group == "DEVELOPMENT"
    assert campaign.FAMILIES["two_period_cribs"].group == "SPECIALIST"
    assert campaign.FAMILIES["vigenere_beam"].group == "STANDARD"


def test_direction_schedule_can_balance_ltr_and_rtl() -> None:
    campaign = _campaign()
    scheduled = [campaign.trial_direction(index).value for index in range(4)]
    assert scheduled.count("ltr") == scheduled.count("rtl") == 2


def test_campaign_mode_selects_trial_count_from_config() -> None:
    campaign = _campaign()
    assert campaign.campaign_trial_count("pilot") == (
        campaign.config.PILOT_TRIALS_PER_ORDINARY_FAMILY
    )
    assert campaign.campaign_trial_count("full") == campaign.config.FULL_TRIALS_PER_FAMILY
    with pytest.raises(ValueError, match="unknown campaign mode"):
        campaign.campaign_trial_count("unknown")


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


def test_same_trial_reconstructs_same_problem_with_new_attempt_seed() -> None:
    campaign = _campaign()
    first = campaign.build_case("vigenere_beam", 0, 0)
    repeated = campaign.build_case("vigenere_beam", 0, 0)
    retry = campaign.build_case("vigenere_beam", 0, 1)
    assert first.reference == repeated.reference == retry.reference
    assert first.ciphertext == repeated.ciphertext == retry.ciphertext
    assert first.cipher_parameters == repeated.cipher_parameters == retry.cipher_parameters
    assert first.source == repeated.source == retry.source


@pytest.mark.parametrize(
    "family",
    (
        "vigenere_beam", "railfence_beam", "autokey_ga", "columnar_hybrid",
        "mono_ga", "vigenere_interruptors_beam",
        "generic_map_multiply_beam", "scheduled_stream_beam",
    ),
)
def test_registered_ordinary_cases_retain_wli(family: str) -> None:
    campaign = _campaign()
    case = campaign.build_case(family, 0)
    assert len(case.reference) == len(case.wli)
    assert 270 <= len(case.reference) <= 330
    assert case.scorer["use_word_breaks"] is True
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


def test_specialist_adapter_supplies_ciphertext_and_wli(monkeypatch: pytest.MonkeyPatch) -> None:
    campaign = _campaign()
    case = campaign.build_case("two_period_cribs", 0)
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(campaign.api, "run", fake_run)
    campaign.execute_case(case)
    assert captured["text"] == (case.ciphertext, case.wli)


def test_exceptions_become_fail_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    campaign = _campaign()
    monkeypatch.setitem(campaign.config.ATTEMPTS_PER_TRIAL, "vigenere_beam", 1)
    monkeypatch.setattr(
        campaign, "build_case", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("broken"))
    )
    record = campaign.run_trial("vigenere_beam", 0)
    assert record["classification"] == "FAIL"
    assert record["attempts"][0]["notes"] == "RuntimeError: broken"


def test_multiple_attempt_pipeline_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    campaign = _campaign()
    monkeypatch.setitem(campaign.config.ATTEMPTS_PER_TRIAL, "railfence_beam", 2)
    monkeypatch.setattr(campaign, "execute_case", lambda case: _result(case))
    first = campaign.run_trial("railfence_beam", 0)
    second = campaign.run_trial("railfence_beam", 0)
    assert first["attempt_count"] == 2
    assert first["attempt_seeds"] == second["attempt_seeds"]
    assert first["selected_attempt"] == second["selected_attempt"]
    assert first["cipher_parameters"] == second["cipher_parameters"]


def test_output_is_external_and_jsonl_schema_is_exact(tmp_path: Path) -> None:
    campaign = _campaign()
    assert not campaign.OUTPUT_PATH.is_relative_to(ROOT)
    record = campaign.failure_record(
        "vigenere_beam", 0, 7, RuntimeError("broken"), 0.5
    )
    assert set(record) == set(campaign.RESULT_FIELDS)
    output = tmp_path / "result.jsonl"
    campaign.write_records([record], output)
    assert json.loads(output.read_text(encoding="utf-8")) == record
    campaign.append_record(record, output)
    assert len(output.read_text(encoding="utf-8").splitlines()) == 2
