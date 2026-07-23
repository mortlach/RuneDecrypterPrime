from __future__ import annotations

import json
import math
from enum import StrEnum
from pathlib import Path

import pytest

import cipher_development.shared.experiment as experiment_module
from cipher_development.shared.experiment import (
    ExperimentDecision,
    ExperimentRun,
    ExperimentSpec,
    FailureMechanism,
    TruthPolicy,
    WliMode,
    canonical_config_hash,
    telemetry_summary,
)
from cipher_development.shared.ledger import read_ledger


class SampleEnum(StrEnum):
    VALUE = "value"


def _spec(**overrides) -> ExperimentSpec:
    values = {
        "campaign_id": "two_period_overlay",
        "experiment_id": "wp1_smoke",
        "benchmark_id": "alice_308",
        "question": "Does the experiment boundary preserve evidence?",
        "hypothesis": "The small contract is sufficient.",
        "alternative": "The small contract omits required evidence.",
        "decision_rule": "Refine if the evidence is incomplete.",
        "mechanisms": (FailureMechanism.EVIDENCE_REPRODUCIBILITY,),
    }
    values.update(overrides)
    return ExperimentSpec(**values)


def _run(tmp_path: Path, configuration=None, **spec_overrides) -> ExperimentRun:
    return ExperimentRun(
        spec=_spec(**spec_overrides),
        configuration=configuration or {"seed": 7, "solver": {"name": "coordinate"}},
        repo_root=tmp_path,
    )


def test_wli_modes_are_deliberately_two_way() -> None:
    assert _spec().wli_mode is WliMode.WITH_WLI
    assert _spec(wli_mode="without_wli").wli_mode is WliMode.WITHOUT_WLI
    for invalid in ("partial_wli", "full_wli", "no_wli"):
        with pytest.raises(ValueError, match="wli_mode"):
            _spec(wli_mode=invalid)


def test_spec_validates_ids_text_budgets_and_unique_mechanisms() -> None:
    with pytest.raises(ValueError, match="campaign_id"):
        _spec(campaign_id="Bad Campaign")
    for field in ("question", "hypothesis", "alternative", "decision_rule"):
        with pytest.raises(ValueError, match=field):
            _spec(**{field: "  "})
    for bad in (0, -1, math.inf, math.nan):
        with pytest.raises(ValueError):
            _spec(budget_seconds=bad)
    with pytest.raises(TypeError):
        _spec(budget_seconds=True)
    for bad in (0, -1):
        with pytest.raises(ValueError):
            _spec(budget_evaluations=bad)
    with pytest.raises(TypeError):
        _spec(budget_evaluations=True)
    with pytest.raises(ValueError, match="unique"):
        _spec(mechanisms=(FailureMechanism.BUDGET, FailureMechanism.BUDGET))
    for bad in ("CSL-1", "csl-001", "CSL-0001"):
        with pytest.raises(ValueError, match="CSL-NNN"):
            _spec(lesson_ids=(bad,))
    with pytest.raises(ValueError, match="unique"):
        _spec(lesson_ids=("CSL-001", "CSL-001"))


def test_spec_is_frozen_and_json_compatible() -> None:
    spec = _spec(
        wli_mode="without_wli",
        truth_policy="none",
        budget_evaluations=10,
        lesson_ids=("CSL-001",),
    )
    payload = spec.to_json_dict()
    assert payload["wli_mode"] == "without_wli"
    assert payload["truth_policy"] == "none"
    assert payload["mechanisms"] == ["evidence_reproducibility"]
    assert payload["alternative"] == "The small contract omits required evidence."
    assert payload["lesson_ids"] == ["CSL-001"]
    with pytest.raises(Exception):
        spec.question = "changed"  # type: ignore[misc]


def test_configuration_hash_is_canonical_and_sensitive() -> None:
    left = {"b": 2, "a": {"enum": SampleEnum.VALUE, "values": (1, 2)}}
    right = {"a": {"values": [1, 2], "enum": "value"}, "b": 2}
    assert canonical_config_hash(left) == canonical_config_hash(right)
    assert canonical_config_hash(left) != canonical_config_hash({"b": 3, "a": right["a"]})


@pytest.mark.parametrize(
    "bad",
    [
        {"path": Path("fixture.json")},
        {"set": {1, 2}},
        {"callable": lambda: None},
        {"object": object()},
        {1: "non-string-key"},
        {"float": math.inf},
        {"float": math.nan},
    ],
)
def test_configuration_hash_rejects_unstable_values(bad) -> None:
    with pytest.raises((TypeError, ValueError)):
        canonical_config_hash(bad)


@pytest.mark.parametrize(
    "configuration",
    [
        {"truth_key": [1, 2]},
        {"nested": {"ground_truth": "answer"}},
        {"oracle": {"key": [1, 2]}},
        {"expected_plaintext": "answer"},
        {"match_ratio": 1.0},
    ],
)
def test_configuration_rejects_reference_truth_and_oracle_fields(
    tmp_path: Path, configuration
) -> None:
    with pytest.raises(ValueError, match="reference or truth"):
        _run(tmp_path, configuration=configuration)


def test_configuration_snapshot_and_hash_cannot_drift(tmp_path: Path) -> None:
    configuration = {"seed": 7, "solver": {"weights": [1, 2]}}
    run = _run(tmp_path, configuration=configuration)
    expected_hash = run.configuration_hash
    configuration["seed"] = 9
    configuration["solver"]["weights"].append(3)
    with run:
        manifest = json.loads(
            (run.run_dir / "artifacts/experiment_manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["configuration"] == {"seed": 7, "solver": {"weights": [1, 2]}}
        assert manifest["configuration_hash"] == expected_hash
        assert canonical_config_hash(manifest["configuration"]) == expected_hash
        run.finish(decision="refine", stop_reason="time_budget")


def test_telemetry_summary_reads_existing_values_without_merging_counts() -> None:
    class Telemetry:
        eval_keys = 5
        eval_batches = 2
        candidates_evaluated = 9
        tokens_processed = 90
        decrypt_time_s = 0.2
        score_time_s = 0.3

    assert telemetry_summary(Telemetry()) == {
        "eval_keys": 5,
        "eval_batches": 2,
        "candidates_evaluated": 9,
        "tokens_processed": 90,
        "decrypt_time_s": 0.2,
        "score_time_s": 0.3,
    }
    assert telemetry_summary({"eval_keys": 5, "candidates_evaluated": 9}) == {
        "eval_keys": 5,
        "candidates_evaluated": 9,
    }


def test_enter_uses_rdp_logging_and_writes_small_manifest(tmp_path: Path) -> None:
    with _run(tmp_path) as run:
        assert run.run_dir is not None
        assert (run.run_dir / "META.json").is_file()
        assert (run.run_dir / "config" / "logging.json").is_file()
        manifest_path = run.run_dir / "artifacts" / "experiment_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["schema"] == "rdp_cipher_development_experiment_manifest.v1"
        assert manifest["standard_artifacts"] == {
            "logging_config": "config/logging.json",
            "run_meta": "META.json",
        }
        assert "git" not in manifest
        assert "host" not in manifest
        assert "python" not in manifest
        run.finish(decision="refine", stop_reason="time_budget")


def test_snapshot_replaces_previous_file_and_forbids_truth_metrics(tmp_path: Path) -> None:
    with _run(tmp_path) as run:
        path = run.snapshot(label="first", metrics={"best_score": 1.0})
        first = path.read_text(encoding="utf-8")
        run.snapshot(label="second", metrics={"best_score": 2.0})
        second = path.read_text(encoding="utf-8")
        assert first != second
        assert json.loads(second)["label"] == "second"
        assert not list(path.parent.glob("*.tmp"))
        with pytest.raises(ValueError, match="reference or truth"):
            run.snapshot(label="bad", metrics={"match_ratio": 1.0})
        run.finish(decision=ExperimentDecision.REFINE, stop_reason="time_budget")


def test_finish_writes_result_and_exactly_one_ledger_row(tmp_path: Path) -> None:
    with _run(
        tmp_path,
        budget_seconds=30.0,
        budget_evaluations=200,
        lesson_ids=("CSL-001", "CSL-007"),
    ) as run:
        result_path = run.finish(
            decision=ExperimentDecision.PROMOTE,
            stop_reason="target_score",
            result_summary={"best_score": 0.98},
            telemetry={"eval_keys": 20, "candidates_evaluated": 20},
            reference_evaluation={"match_ratio": 1.0},
        )
        result = json.loads(result_path.read_text(encoding="utf-8"))
        assert result["result_summary"] == {"best_score": 0.98}
        assert result["reference_evaluation"] == {"match_ratio": 1.0}
        assert result["stop_category"] == "success"
        rows = read_ledger(run.ledger_path)
        assert len(rows) == 1
        assert rows[0].decision == "promote"
        assert rows[0].hypothesis == "The small contract is sufficient."
        assert rows[0].alternative == "The small contract omits required evidence."
        assert rows[0].budget_seconds == 30.0
        assert rows[0].budget_evaluations == 200
        assert rows[0].lesson_ids == ("CSL-001", "CSL-007")
        assert rows[0].telemetry["eval_keys"] == 20
        with pytest.raises(RuntimeError, match="already finished"):
            run.finish(decision="close", stop_reason="done")


def test_ledger_failure_does_not_overwrite_completed_result(tmp_path: Path, monkeypatch) -> None:
    run = _run(tmp_path)

    def fail_append(*args, **kwargs):
        raise OSError("ledger unavailable")

    monkeypatch.setattr(experiment_module, "append_ledger_row", fail_append)
    with pytest.raises(OSError, match="ledger unavailable"):
        with run:
            run.finish(
                decision="promote",
                stop_reason="target_score",
                result_summary={"best_score": 0.98},
            )
    result = json.loads(
        (run.run_dir / "artifacts/experiment_result.json").read_text(encoding="utf-8")
    )
    assert result["status"] == "completed"
    assert result["decision"] == "promote"
    assert result["result_summary"] == {"best_score": 0.98}


def test_truth_policy_none_rejects_reference_evaluation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="forbidden"):
        with _run(tmp_path, truth_policy=TruthPolicy.NONE) as run:
            run.finish(
                decision="close",
                stop_reason="done",
                reference_evaluation={"match_ratio": 1.0},
            )


def test_exception_is_recorded_and_reraised(tmp_path: Path) -> None:
    run = _run(tmp_path)
    machine_path = tmp_path / "private" / "campaign"
    with pytest.raises(RuntimeError, match="campaign failed"):
        with run:
            raise RuntimeError(f"campaign failed at {machine_path}")
    assert run.run_dir is not None
    result = json.loads(
        (run.run_dir / "artifacts" / "experiment_result.json").read_text(encoding="utf-8")
    )
    assert result["status"] == "failed"
    assert result["decision"] is None
    assert str(machine_path) not in result["result_summary"]["error_message"]
    assert len(read_ledger(run.ledger_path)) == 1


def test_normal_exit_without_finish_is_recorded_then_raises(tmp_path: Path) -> None:
    run = _run(tmp_path)
    with pytest.raises(RuntimeError, match="without finish"):
        with run:
            pass
    assert len(read_ledger(run.ledger_path)) == 1
    assert read_ledger(run.ledger_path)[0].status == "failed"


def test_only_one_experiment_run_may_be_active_per_process(tmp_path: Path) -> None:
    first = _run(tmp_path / "first")
    second = _run(tmp_path / "second")
    with first:
        with pytest.raises(RuntimeError, match="only one"):
            second.__enter__()
        first.finish(decision="refine", stop_reason="time_budget")
    with second:
        second.finish(decision="close", stop_reason="done")


def test_output_root_must_stay_below_cipher_development(tmp_path: Path) -> None:
    bad_roots = [
        Path("elsewhere"),
        Path("../output"),
        Path("output/unrelated"),
        tmp_path.resolve() / "outside",
    ]
    for bad in bad_roots:
        with pytest.raises(ValueError, match="cipher_development"):
            ExperimentRun(spec=_spec(), configuration={}, repo_root=tmp_path, output_root=bad)

    run = ExperimentRun(
        spec=_spec(),
        configuration={},
        repo_root=tmp_path,
        output_root=Path("output/cipher_development/controlled"),
    )
    with run:
        assert run.run_dir is not None
        assert "controlled" in run.run_dir.parts
        run.finish(decision="close", stop_reason="done")


def test_new_source_has_no_environment_or_cli_configuration() -> None:
    root = Path(__file__).resolve().parents[2]
    forbidden = ("os.environ", "os.getenv", "sys.argv", "argparse")
    for relpath in (
        Path("cipher_development/shared/experiment.py"),
        Path("cipher_development/shared/ledger.py"),
    ):
        text = (root / relpath).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text
