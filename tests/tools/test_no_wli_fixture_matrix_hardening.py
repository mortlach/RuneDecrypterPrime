from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli import fixture_matrix_api as fixture_api
from tools.benchmarks.periodic_sub_trans.no_wli import run_fixture_matrix as run_matrix_mod
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_models import (
    Stage3TuningPreset,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_runtime import (
    planned_job_keys_signature,
    run_jobs_with_checkpoints,
)


pytestmark = pytest.mark.tier_a


def _job(*, key: str) -> SimpleNamespace:
    return SimpleNamespace(
        fixture_id="fixture_001",
        period=9,
        columns=3,
        length=1000,
        run_seed=411,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m12_b34_stage3avg_fulltext_v1",
        scoring_experiment_profile="c_min_late",
        schedule_early="a_char1_avg_fulltext",
        schedule_middle="m_char12_avg_fulltext",
        schedule_late="b_char4_avg_fulltext",
        span_ab_case_id="none",
        span_decision_role_enabled=False,
        as_dict=lambda: {"job_key": key},
    )


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_stage3_tuning_preset_from_mapping_normalizes_types() -> None:
    preset = Stage3TuningPreset.from_mapping(
        preset_id="Stage3_PhaseB_Width_Probe_P9",
        raw={
            "force_stage3_phaseb_top_n": "32",
            "force_stage3_initial_keys_by_columns": {"3": "64"},
            "force_stage3_phasec_start_policy": "Balanced_Sources_V1",
            "stage3_span_basin_k_sweep_values": ["64", 96],
        },
    )

    assert str(preset.preset_id) == "stage3_phaseb_width_probe_p9"
    assert int(preset.force_stage3_phaseb_top_n) == 32
    assert preset.force_stage3_initial_keys_by_columns == {3: 64}
    assert str(preset.force_stage3_phasec_start_policy) == "balanced_sources_v1"
    assert preset.stage3_span_basin_k_sweep_values == (64, 96)
    assert preset.as_dict()["force_stage3_phaseb_top_n"] == 32


def test_resolve_stage3_tuning_presets_rejects_unknown_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        fixture_api,
        "STAGE3_TUNING_PRESETS",
        {
            "bad_preset": {
                "force_stage3_phaseb_top_n": 8,
                "unknown_field": 1,
            }
        },
    )

    with pytest.raises(KeyError, match="unknown stage3 tuning preset field\\(s\\)"):
        fixture_api.resolve_stage3_tuning_presets()


def test_build_matrix_mainflow_state_serializes_plain_stage3_tuning_dicts() -> None:
    state = run_matrix_mod.build_matrix_mainflow_state()
    presets = state["STAGE3_TUNING_PRESETS"]

    assert isinstance(presets, dict)
    assert presets
    assert all(isinstance(value, dict) for value in presets.values())
    assert int(presets["stage3_phaseb_width_probe_p9"]["force_stage3_phaseb_top_n"]) == 32


def test_runtime_rejects_duplicate_job_keys(tmp_path: Path) -> None:
    run_state = tmp_path / "state.json"
    run_events = tmp_path / "events.jsonl"
    jobs = [_job(key="dup"), _job(key="dup")]

    with pytest.raises(ValueError, match="duplicate job keys"):
        run_jobs_with_checkpoints(
            jobs=jobs,
            run_mode="adaptive_fixture_v1",
            profile_id="profile_x",
            dry_run_only=False,
            stop_on_error=True,
            max_wallclock_seconds=None,
            resume_skip_completed=True,
            run_state_path=run_state,
            run_events_path=run_events,
            plan_job_count=2,
            base_state_fields={"experiment_run_id": "exp_dup"},
            write_json_fn=_write_json,
            job_key_fn=lambda job: str(job.as_dict()["job_key"]),
            run_job_fn=lambda _job: None,
            print_fn=lambda *args, **kwargs: None,
            load_json_fn=_load_json,
        )


def test_runtime_rejects_stale_run_state_experiment_id_mismatch(tmp_path: Path) -> None:
    run_state = tmp_path / "state.json"
    run_events = tmp_path / "events.jsonl"
    _write_json(
        run_state,
        {
            "experiment_run_id": "wrong_exp",
            "planned_job_keys_signature": planned_job_keys_signature(job_keys=["job_1"]),
            "completed_job_keys": [],
        },
    )

    with pytest.raises(ValueError, match="experiment_run_id mismatch"):
        run_jobs_with_checkpoints(
            jobs=[_job(key="job_1")],
            run_mode="adaptive_fixture_v1",
            profile_id="profile_x",
            dry_run_only=False,
            stop_on_error=True,
            max_wallclock_seconds=None,
            resume_skip_completed=True,
            run_state_path=run_state,
            run_events_path=run_events,
            plan_job_count=1,
            base_state_fields={"experiment_run_id": "expected_exp"},
            write_json_fn=_write_json,
            job_key_fn=lambda job: str(job.as_dict()["job_key"]),
            run_job_fn=lambda _job: None,
            print_fn=lambda *args, **kwargs: None,
            load_json_fn=_load_json,
        )


def test_runtime_rejects_stale_run_state_signature_mismatch(tmp_path: Path) -> None:
    run_state = tmp_path / "state.json"
    run_events = tmp_path / "events.jsonl"
    _write_json(
        run_state,
        {
            "experiment_run_id": "expected_exp",
            "planned_job_keys_signature": planned_job_keys_signature(job_keys=["other_job"]),
            "completed_job_keys": [],
        },
    )

    with pytest.raises(ValueError, match="planned_job_keys_signature mismatch"):
        run_jobs_with_checkpoints(
            jobs=[_job(key="job_1")],
            run_mode="adaptive_fixture_v1",
            profile_id="profile_x",
            dry_run_only=False,
            stop_on_error=True,
            max_wallclock_seconds=None,
            resume_skip_completed=True,
            run_state_path=run_state,
            run_events_path=run_events,
            plan_job_count=1,
            base_state_fields={"experiment_run_id": "expected_exp"},
            write_json_fn=_write_json,
            job_key_fn=lambda job: str(job.as_dict()["job_key"]),
            run_job_fn=lambda _job: None,
            print_fn=lambda *args, **kwargs: None,
            load_json_fn=_load_json,
        )


def test_runtime_writes_identity_fields_and_event_experiment_id(tmp_path: Path) -> None:
    run_state = tmp_path / "state.json"
    run_events = tmp_path / "events.jsonl"

    run_jobs_with_checkpoints(
        jobs=[_job(key="job_1")],
        run_mode="adaptive_fixture_v1",
        profile_id="profile_x",
        dry_run_only=False,
        stop_on_error=True,
        max_wallclock_seconds=None,
        resume_skip_completed=True,
        run_state_path=run_state,
        run_events_path=run_events,
        plan_job_count=1,
        base_state_fields={"experiment_run_id": "exp_identity"},
        write_json_fn=_write_json,
        job_key_fn=lambda job: str(job.as_dict()["job_key"]),
        run_job_fn=lambda _job: None,
        print_fn=lambda *args, **kwargs: None,
        load_json_fn=_load_json,
    )

    payload = _load_json(run_state)
    assert str(payload["experiment_run_id"]) == "exp_identity"
    assert str(payload["run_state_version"]) == "v2"
    assert int(payload["planned_job_count"]) == 1
    assert str(payload["planned_job_keys_signature"]) == planned_job_keys_signature(
        job_keys=["job_1"]
    )

    rows = [
        json.loads(line)
        for line in run_events.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows
    assert {str(row["experiment_run_id"]) for row in rows} == {"exp_identity"}
