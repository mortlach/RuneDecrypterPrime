from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_jobs import apply_job
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_runtime import (
    run_jobs_with_checkpoints,
)


pytestmark = pytest.mark.tier_a


def _job(case_id: str, decision: bool) -> SimpleNamespace:
    return SimpleNamespace(
        fixture_id="fixture_001",
        period=7,
        columns=3,
        length=1000,
        run_seed=111,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1",
        scoring_experiment_profile="off",
        schedule_early="a_char2_avg_fulltext",
        schedule_middle="m_char4_avg_fulltext",
        schedule_late="b_char4_avg_fulltext",
        span_ab_case_id=case_id,
        span_decision_role_enabled=decision,
        as_dict=lambda: {
            "span_ab_case_id": case_id,
            "span_decision_role_enabled": decision,
        },
    )


def test_runtime_emits_span_ab_pair_delta_event(tmp_path: Path) -> None:
    run_state = tmp_path / "state.json"
    run_events = tmp_path / "events.jsonl"
    jobs = [_job("span_shadow", False), _job("span_prune", True)]

    def _write_json(path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    run_jobs_with_checkpoints(
        jobs=jobs,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1",
        dry_run_only=False,
        stop_on_error=True,
        max_wallclock_seconds=None,
        resume_skip_completed=True,
        run_state_path=run_state,
        run_events_path=run_events,
        plan_job_count=2,
        base_state_fields={},
        write_json_fn=_write_json,
        job_key_fn=lambda job: f"{job.span_ab_case_id}",
        run_job_fn=lambda _job: None,
        print_fn=lambda *args, **kwargs: None,
        load_json_fn=lambda path: json.loads(path.read_text(encoding="utf-8")),
    )
    rows = [
        json.loads(line)
        for line in run_events.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    delta_rows = [r for r in rows if str(r.get("event")) == "span_ab_pair_delta"]
    assert len(delta_rows) == 1
    delta = delta_rows[0]
    assert delta["shadow_case_id"] == "span_shadow"
    assert delta["decision_case_id"] == "span_prune"
    assert isinstance(delta["delta_elapsed_seconds"], float)


def test_apply_job_sets_span_decision_role_controls() -> None:
    calls: list[dict[str, object]] = []
    no_wli = SimpleNamespace(
        RUN_STAGE3_SPAN_BASIN_K_SWEEP=True,
        STAGE3_SPAN_BASIN_K_SWEEP_VALUES=[96],
        STAGE3_SPAN_BASIN_JUDGE_K=96,
        SPAN_DECISION_ROLE_ENABLED=False,
        STAGE3_SPAN_AUX_ROLE="off",
        SCORING_EXPERIMENT_PROFILE="off",
    )
    no_wli.configure_campaign_run = lambda **kwargs: calls.append(dict(kwargs))
    job = SimpleNamespace(
        run_seed=111,
        period=7,
        columns=3,
        length=1000,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1",
        heartbeat_seconds=3600,
        text_offsets=(0,),
        scorer_impl="numpy",
        scorer_stage3_impl_avg_fulltext="numpy",
        scoring_experiment_profile="off",
        span_ab_case_id="span_prune",
        span_decision_role_enabled=True,
        tier_name=lambda: "fixture_fixture_001_p7_c3_l1000",
        scorer_schedule=lambda: {
            "early": "a_char2_avg_fulltext",
            "middle": "m_char4_avg_fulltext",
            "late": "b_char4_avg_fulltext",
        },
    )
    apply_job(
        job=job,
        no_wli=no_wli,
        disable_stage3_span_basin_k_sweep=True,
        stage3_span_basin_k_sweep_values=(96,),
    )
    assert calls, "configure_campaign_run should be called"
    assert no_wli.SPAN_DECISION_ROLE_ENABLED is True
    assert no_wli.STAGE3_SPAN_AUX_ROLE == "prune"


def test_apply_job_sets_conservative_early_overrides() -> None:
    calls: list[dict[str, object]] = []
    no_wli = SimpleNamespace(
        RUN_STAGE3_SPAN_BASIN_K_SWEEP=True,
        STAGE3_SPAN_BASIN_K_SWEEP_VALUES=[96],
        STAGE3_SPAN_BASIN_JUDGE_K=96,
        SPAN_DECISION_ROLE_ENABLED=False,
        STAGE3_SPAN_AUX_ROLE="off",
        SCORING_EXPERIMENT_PROFILE="off",
        STAGE1_SEED_RESTARTS=96,
        STAGE1_SEED_TOTAL=256,
        STAGE1_SCOUT_MIN_STEPS=900,
        STAGE12_ARCHIVE_KEEP=192,
    )
    no_wli.configure_campaign_run = lambda **kwargs: calls.append(dict(kwargs))
    job = SimpleNamespace(
        run_seed=111,
        period=9,
        columns=3,
        length=1000,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1",
        heartbeat_seconds=3600,
        text_offsets=(0,),
        scorer_impl="torch",
        scorer_stage3_impl_avg_fulltext="torch",
        scoring_experiment_profile="c_min_late",
        span_ab_case_id="none",
        span_decision_role_enabled=False,
        tier_name=lambda: "fixture_fixture_001_p9_c3_l1000",
        scorer_schedule=lambda: {
            "early": "a_char1_avg_fulltext",
            "middle": "m_char12_avg_fulltext",
            "late": "b_char4_avg_fulltext",
        },
    )
    apply_job(
        job=job,
        no_wli=no_wli,
        disable_stage3_span_basin_k_sweep=False,
        stage3_span_basin_k_sweep_values=(96,),
        force_stage1_seed_restarts=88,
        force_stage1_seed_total=224,
        force_stage1_scout_min_steps=850,
        force_stage12_archive_keep=160,
    )
    assert calls, "configure_campaign_run should be called"
    assert int(no_wli.STAGE1_SEED_RESTARTS) == 88
    assert int(no_wli.STAGE1_SEED_TOTAL) == 224
    assert int(no_wli.STAGE1_SCOUT_MIN_STEPS) == 850
    assert int(no_wli.STAGE12_ARCHIVE_KEEP) == 160
