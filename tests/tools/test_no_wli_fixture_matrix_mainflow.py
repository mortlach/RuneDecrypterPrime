from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_mainflow import (
    _derive_acceptance_fixture_ids,
    run_mainflow,
)


pytestmark = pytest.mark.tier_a


def _base_state() -> dict[str, Any]:
    return {
        "CAMPAIGN_CONFIG_PATH": Path("tools/benchmarks/community/examples/campaign_config_v1_1.json"),
        "FIXTURE_IDS": None,
        "FIXTURE_LENGTH_OVERRIDE": 1000,
        "USE_CAMPAIGN_GRID": False,
        "PERIODS_OVERRIDE": (7,),
        "COLUMNS_OVERRIDE_BY_PERIOD": {7: (1,)},
        "SCHEDULE_COVERAGE_MODE": "explicit",
        "EXPLICIT_SCHEDULES": ({"early": "a_char2_avg_fulltext", "middle": "m_char4_avg_fulltext", "late": "b_char4_avg_fulltext"},),
        "RUN_SEEDS": (111,),
        "RUN_MODE": "adaptive_fixture_v1",
        "NO_WLI_PROFILE_ID": "no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1",
        "HEARTBEAT_SECONDS": 3600,
        "TEXT_OFFSETS": (0,),
        "SCORER_IMPL": "numpy",
        "SCORER_STAGE3_IMPL_AVG_FULLTEXT": "numpy",
        "SCORING_EXPERIMENT_PROFILES": ("off",),
        "ENABLE_SPAN_AB_PAIR": False,
        "SPAN_AB_DECISION_ROLE": "prune",
        "MAX_JOBS": None,
        "REQUIRE_NO_WIN10_OBJECTIVES": True,
        "REQUIRE_FULL_TEXT_EFFECTIVE": True,
        "DISABLE_STAGE3_SPAN_BASIN_K_SWEEP": False,
        "STAGE3_SPAN_BASIN_K_SWEEP_VALUES": (96,),
        "WRITE_PLAN_JSON": False,
        "PLAN_OUTPUT_PATH": Path("output/x.json"),
        "DRY_RUN_ONLY": True,
        "RUN_STATE_PATH": Path("output/state.json"),
        "RUN_EVENTS_PATH": Path("output/events.jsonl"),
        "RESUME_SKIP_COMPLETED": True,
        "STOP_ON_ERROR": True,
        "MAX_WALLCLOCK_SECONDS": None,
        "EXPERIMENT_RUN_ID": "test_fixture_matrix_mainflow",
        "_utc_now_iso": lambda: "2026-03-07T00:00:00Z",
        "ENABLE_ACCEPTANCE_HARNESS_500X5": False,
        "ACCEPTANCE_HARNESS_FIXTURE_COUNT": 5,
        "ACCEPTANCE_HARNESS_LENGTH": 500,
    }


def test_derive_acceptance_fixture_ids_uses_first_n_rows() -> None:
    cfg = {
        "fixtures": [
            {"text_fixture_id": "fixture_001"},
            {"text_fixture_id": "fixture_002"},
            {"text_fixture_id": "fixture_003"},
        ]
    }
    out = _derive_acceptance_fixture_ids(campaign_config=cfg, fixture_count=2)
    assert out == ("fixture_001", "fixture_002")


def test_run_mainflow_acceptance_harness_sets_fixture_ids_and_length() -> None:
    state = _base_state()
    state["ENABLE_ACCEPTANCE_HARNESS_500X5"] = True

    captured: dict[str, Any] = {}

    def _load_fixture_specs(**kwargs):
        captured["fixture_ids"] = kwargs["fixture_ids"]
        captured["fixture_length_override"] = kwargs["fixture_length_override"]
        return []

    run_mainflow(
        state=state,
        repo_root=Path("."),
        resolve_path_fn=lambda p: p,
        load_json_fn=lambda _p: {
            "fixtures": [
                {"text_fixture_id": "fixture_001"},
                {"text_fixture_id": "fixture_002"},
                {"text_fixture_id": "fixture_003"},
                {"text_fixture_id": "fixture_004"},
                {"text_fixture_id": "fixture_005"},
                {"text_fixture_id": "fixture_006"},
            ]
        },
        write_json_fn=lambda *_args, **_kwargs: None,
        load_fixture_specs_fn=_load_fixture_specs,
        resolve_period_columns_fn=lambda **_kwargs: {7: (1,)},
        build_schedule_matrix_fn=lambda **_kwargs: [{"early": "a", "middle": "m", "late": "b"}],
        build_fixture_jobs_fn=lambda **_kwargs: [],
        build_plan_payload_fn=lambda **_kwargs: {"job_count": 0},
        run_jobs_with_checkpoints_fn=lambda **_kwargs: None,
        load_run_state_fn=lambda _p: {},
        job_key_fn=lambda _job: "k",
        run_job_fn=lambda _job: None,
        runtime_preflight_fn=lambda **_kwargs: {},
        print_fn=lambda *_args, **_kwargs: None,
    )

    assert captured["fixture_ids"] == (
        "fixture_001",
        "fixture_002",
        "fixture_003",
        "fixture_004",
        "fixture_005",
    )
    assert int(captured["fixture_length_override"]) == 500


def test_run_mainflow_acceptance_harness_respects_explicit_fixture_ids() -> None:
    state = _base_state()
    state["ENABLE_ACCEPTANCE_HARNESS_500X5"] = True
    state["FIXTURE_IDS"] = ("fixture_custom",)

    captured: dict[str, Any] = {}

    def _load_fixture_specs(**kwargs):
        captured["fixture_ids"] = kwargs["fixture_ids"]
        captured["fixture_length_override"] = kwargs["fixture_length_override"]
        return []

    run_mainflow(
        state=state,
        repo_root=Path("."),
        resolve_path_fn=lambda p: p,
        load_json_fn=lambda _p: {"fixtures": [{"text_fixture_id": "fixture_001"}]},
        write_json_fn=lambda *_args, **_kwargs: None,
        load_fixture_specs_fn=_load_fixture_specs,
        resolve_period_columns_fn=lambda **_kwargs: {7: (1,)},
        build_schedule_matrix_fn=lambda **_kwargs: [{"early": "a", "middle": "m", "late": "b"}],
        build_fixture_jobs_fn=lambda **_kwargs: [],
        build_plan_payload_fn=lambda **_kwargs: {"job_count": 0},
        run_jobs_with_checkpoints_fn=lambda **_kwargs: None,
        load_run_state_fn=lambda _p: {},
        job_key_fn=lambda _job: "k",
        run_job_fn=lambda _job: None,
        runtime_preflight_fn=lambda **_kwargs: {},
        print_fn=lambda *_args, **_kwargs: None,
    )

    assert captured["fixture_ids"] == ("fixture_custom",)
    assert int(captured["fixture_length_override"]) == 500


def test_run_mainflow_aborts_on_failed_runtime_preflight() -> None:
    state = _base_state()
    state["DRY_RUN_ONLY"] = False
    writes: list[dict[str, Any]] = []
    run_jobs_called = False

    def _write_json(_path: Path, payload) -> None:
        writes.append(dict(payload))

    def _run_jobs(**_kwargs) -> None:
        nonlocal run_jobs_called
        run_jobs_called = True

    with pytest.raises(RuntimeError, match="runtime preflight failed"):
        run_mainflow(
            state=state,
            repo_root=Path("."),
            resolve_path_fn=lambda p: p,
            load_json_fn=lambda _p: {
                "fixtures": [{"text_fixture_id": "fixture_001"}]
            },
            write_json_fn=_write_json,
            load_fixture_specs_fn=lambda **_kwargs: [],
            resolve_period_columns_fn=lambda **_kwargs: {7: (1,)},
            build_schedule_matrix_fn=lambda **_kwargs: [
                {"early": "a", "middle": "m", "late": "b"}
            ],
            build_fixture_jobs_fn=lambda **_kwargs: ["job_1"],
            build_plan_payload_fn=lambda **_kwargs: {"job_count": 1},
            run_jobs_with_checkpoints_fn=_run_jobs,
            load_run_state_fn=lambda _p: {},
            job_key_fn=lambda _job: "k",
            run_job_fn=lambda _job: None,
            runtime_preflight_fn=lambda **_kwargs: {
                "required": True,
                "status": "failed",
                "cuda_available": True,
                "cuda_smoke_ok": False,
                "error_type": "AcceleratorError",
                "error": "CUDA error: unknown error",
            },
            print_fn=lambda *_args, **_kwargs: None,
        )

    assert run_jobs_called is False
    assert writes, "run state should be written before aborting"
    last = writes[-1]
    assert int(last["stopped_early"]) == 1
    assert str(last["experiment_run_id"]) == str(state["EXPERIMENT_RUN_ID"])
    assert str(last["last_error"]["job_key"]) == "<runtime_preflight>"
    assert str(last["runtime_preflight"]["status"]) == "failed"
