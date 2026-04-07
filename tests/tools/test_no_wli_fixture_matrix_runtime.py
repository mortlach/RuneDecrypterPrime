from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.benchmarks.community._campaign_common import load_json
from tools.benchmarks.periodic_sub_trans.no_wli import fixture_matrix_api as fixture_api
from tools.benchmarks.periodic_sub_trans.no_wli import (
    fixture_matrix_config as fixture_matrix_config_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli import (
    fixture_matrix_mainflow as fixture_mainflow_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli import run_fixture_matrix as run_matrix_mod
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


def test_current_fixture_matrix_config_materializes_expected_seed411_stage35_selector_lane_set() -> None:
    compare_mode = str(
        fixture_matrix_config_mod.STAGE35_BASELINE_SELECTOR_COMPARE_MODE
    )
    repo_root = Path.cwd()
    campaign_path = run_matrix_mod._resolve_path(
        path_like=run_matrix_mod.CAMPAIGN_CONFIG_PATH,
        repo_root=repo_root,
    )
    campaign_config = load_json(campaign_path)
    fixtures = run_matrix_mod.load_fixture_specs(
        campaign_config=campaign_config,
        repo_root=repo_root,
        fixture_ids=run_matrix_mod.FIXTURE_IDS,
        fixture_length_override=run_matrix_mod.FIXTURE_LENGTH_OVERRIDE,
    )
    period_columns = run_matrix_mod.resolve_period_columns(
        campaign_config=campaign_config,
        use_campaign_grid=run_matrix_mod.USE_CAMPAIGN_GRID,
        periods_override=run_matrix_mod.PERIODS_OVERRIDE,
        columns_override_by_period=run_matrix_mod.COLUMNS_OVERRIDE_BY_PERIOD,
    )
    schedules = run_matrix_mod.build_schedule_matrix(
        mode=str(run_matrix_mod.SCHEDULE_COVERAGE_MODE),
        explicit_schedules=run_matrix_mod.EXPLICIT_SCHEDULES,
    )
    jobs = run_matrix_mod.build_fixture_jobs(
        fixtures=fixtures,
        period_columns=period_columns,
        run_seeds=run_matrix_mod.RUN_SEEDS,
        run_mode=run_matrix_mod.RUN_MODE,
        profile_id=run_matrix_mod.NO_WLI_PROFILE_ID,
        heartbeat_seconds=int(run_matrix_mod.HEARTBEAT_SECONDS),
        text_offsets=run_matrix_mod.TEXT_OFFSETS,
        scorer_impl=run_matrix_mod.SCORER_IMPL,
        scorer_stage3_impl_avg_fulltext=run_matrix_mod.SCORER_STAGE3_IMPL_AVG_FULLTEXT,
        scoring_experiment_profiles=run_matrix_mod.SCORING_EXPERIMENT_PROFILES,
        stage3_tuning_preset_ids=run_matrix_mod.STAGE3_TUNING_PRESET_IDS,
        schedules=schedules,
        enable_span_ab_pair=bool(run_matrix_mod.ENABLE_SPAN_AB_PAIR),
        span_ab_decision_role=str(run_matrix_mod.SPAN_AB_DECISION_ROLE),
    )
    if run_matrix_mod.MAX_JOBS is not None:
        jobs = jobs[: max(0, int(run_matrix_mod.MAX_JOBS))]

    if compare_mode == "candidate_ladder_small":
        assert tuple(int(x) for x in run_matrix_mod.RUN_SEEDS) == (611, 711)
        assert tuple(int(x) for x in run_matrix_mod.PERIODS_OVERRIDE or ()) == (5, 9)
        assert {
            int(period): tuple(int(c) for c in columns)
            for period, columns in dict(
                run_matrix_mod.COLUMNS_OVERRIDE_BY_PERIOD
            ).items()
        } == {
            5: (1,),
            9: (1, 3),
        }
        assert int(run_matrix_mod.MAX_JOBS) == 6
    elif compare_mode == "candidate_family_overnight":
        assert tuple(int(x) for x in run_matrix_mod.RUN_SEEDS) == (411, 611)
        assert tuple(int(x) for x in run_matrix_mod.PERIODS_OVERRIDE or ()) == (7, 9)
        assert {
            int(period): tuple(int(c) for c in columns)
            for period, columns in dict(
                run_matrix_mod.COLUMNS_OVERRIDE_BY_PERIOD
            ).items()
        } == {
            7: (1,),
            9: (3,),
        }
        assert int(run_matrix_mod.MAX_JOBS) == 4
    elif compare_mode == "candidate_single_p5":
        assert tuple(int(x) for x in run_matrix_mod.RUN_SEEDS) == (511,)
        assert tuple(int(x) for x in run_matrix_mod.PERIODS_OVERRIDE or ()) == (5,)
        assert {
            int(period): tuple(int(c) for c in columns)
            for period, columns in dict(
                run_matrix_mod.COLUMNS_OVERRIDE_BY_PERIOD
            ).items()
        } == {
            5: (1,),
        }
        assert int(run_matrix_mod.MAX_JOBS) == 1
    elif compare_mode == "candidate_single_p7":
        assert tuple(int(x) for x in run_matrix_mod.RUN_SEEDS) == (411,)
        assert tuple(int(x) for x in run_matrix_mod.PERIODS_OVERRIDE or ()) == (7,)
        assert {
            int(period): tuple(int(c) for c in columns)
            for period, columns in dict(
                run_matrix_mod.COLUMNS_OVERRIDE_BY_PERIOD
            ).items()
        } == {
            7: (1,),
        }
        assert int(run_matrix_mod.MAX_JOBS) == 1
    elif compare_mode == "candidate_single_p9_seed611":
        assert tuple(int(x) for x in run_matrix_mod.RUN_SEEDS) == (611,)
        assert tuple(int(x) for x in run_matrix_mod.PERIODS_OVERRIDE or ()) == (9,)
        assert {
            int(period): tuple(int(c) for c in columns)
            for period, columns in dict(
                run_matrix_mod.COLUMNS_OVERRIDE_BY_PERIOD
            ).items()
        } == {
            9: (3,),
        }
        assert int(run_matrix_mod.MAX_JOBS) == 1
    elif compare_mode == "candidate_single_p9_seed711":
        assert tuple(int(x) for x in run_matrix_mod.RUN_SEEDS) == (711,)
        assert tuple(int(x) for x in run_matrix_mod.PERIODS_OVERRIDE or ()) == (9,)
        assert {
            int(period): tuple(int(c) for c in columns)
            for period, columns in dict(
                run_matrix_mod.COLUMNS_OVERRIDE_BY_PERIOD
            ).items()
        } == {
            9: (3,),
        }
        assert int(run_matrix_mod.MAX_JOBS) == 1
    elif compare_mode == "candidate_single_p9_seed811":
        assert tuple(int(x) for x in run_matrix_mod.RUN_SEEDS) == (811,)
        assert tuple(int(x) for x in run_matrix_mod.PERIODS_OVERRIDE or ()) == (9,)
        assert {
            int(period): tuple(int(c) for c in columns)
            for period, columns in dict(
                run_matrix_mod.COLUMNS_OVERRIDE_BY_PERIOD
            ).items()
        } == {
            9: (3,),
        }
        assert int(run_matrix_mod.MAX_JOBS) == 1
    elif compare_mode == "candidate_single_p9_seed911":
        assert tuple(int(x) for x in run_matrix_mod.RUN_SEEDS) == (911,)
        assert tuple(int(x) for x in run_matrix_mod.PERIODS_OVERRIDE or ()) == (9,)
        assert {
            int(period): tuple(int(c) for c in columns)
            for period, columns in dict(
                run_matrix_mod.COLUMNS_OVERRIDE_BY_PERIOD
            ).items()
        } == {
            9: (3,),
        }
        assert int(run_matrix_mod.MAX_JOBS) == 1
    elif compare_mode == "candidate_single_p9_seed1011":
        assert tuple(int(x) for x in run_matrix_mod.RUN_SEEDS) == (1011,)
        assert tuple(int(x) for x in run_matrix_mod.PERIODS_OVERRIDE or ()) == (9,)
        assert {
            int(period): tuple(int(c) for c in columns)
            for period, columns in dict(
                run_matrix_mod.COLUMNS_OVERRIDE_BY_PERIOD
            ).items()
        } == {
            9: (3,),
        }
        assert int(run_matrix_mod.MAX_JOBS) == 1
    elif compare_mode == "candidate_pair_p9_seed1111_1211":
        assert tuple(int(x) for x in run_matrix_mod.RUN_SEEDS) == (1111, 1211)
        assert tuple(int(x) for x in run_matrix_mod.PERIODS_OVERRIDE or ()) == (9,)
        assert {
            int(period): tuple(int(c) for c in columns)
            for period, columns in dict(
                run_matrix_mod.COLUMNS_OVERRIDE_BY_PERIOD
            ).items()
        } == {
            9: (3,),
        }
        assert int(run_matrix_mod.MAX_JOBS) == 2
    elif compare_mode == "candidate_triple_p9_seed1311_1411_1511":
        assert tuple(int(x) for x in run_matrix_mod.RUN_SEEDS) == (1311, 1411, 1511)
        assert tuple(int(x) for x in run_matrix_mod.PERIODS_OVERRIDE or ()) == (9,)
        assert {
            int(period): tuple(int(c) for c in columns)
            for period, columns in dict(
                run_matrix_mod.COLUMNS_OVERRIDE_BY_PERIOD
            ).items()
        } == {
            9: (3,),
        }
        assert int(run_matrix_mod.MAX_JOBS) == 3
    elif compare_mode == "candidate_single_p9_seed611_legacy":
        assert tuple(int(x) for x in run_matrix_mod.RUN_SEEDS) == (611,)
        assert tuple(int(x) for x in run_matrix_mod.PERIODS_OVERRIDE or ()) == (9,)
        assert {
            int(period): tuple(int(c) for c in columns)
            for period, columns in dict(
                run_matrix_mod.COLUMNS_OVERRIDE_BY_PERIOD
            ).items()
        } == {
            9: (3,),
        }
        assert int(run_matrix_mod.MAX_JOBS) == 1
    else:
        assert tuple(int(x) for x in run_matrix_mod.RUN_SEEDS) == (411,)
        assert int(run_matrix_mod.MAX_JOBS) in {1, 2}
        assert tuple(int(x) for x in run_matrix_mod.PERIODS_OVERRIDE or ()) == (9,)
        assert {
            int(period): tuple(int(c) for c in columns)
            for period, columns in dict(
                run_matrix_mod.COLUMNS_OVERRIDE_BY_PERIOD
            ).items()
        } == {
            9: (3,),
        }
    preset_ids = tuple(str(x) for x in run_matrix_mod.STAGE3_TUNING_PRESET_IDS)
    assert preset_ids in {
        (
            "stage35_baseline_legacy_canary_p9",
            "stage35_baseline_score_plus_novelty_canary_p9",
        ),
        (
            "stage35_baseline_legacy_live_p9",
            "stage35_baseline_score_plus_novelty_live_p9",
        ),
        ("stage35_baseline_score_plus_novelty_live_p9",),
        ("stage35_baseline_score_plus_novelty_live_bounded_p9",),
        ("stage35_baseline_legacy_live_bounded_p9",),
    }
    if compare_mode == "candidate_ladder_small":
        assert len(jobs) == 6
        assert [str(job.stage3_tuning_preset_id) for job in jobs] == [
            "stage35_baseline_score_plus_novelty_live_bounded_p9",
        ] * 6
        assert [int(job.period) for job in jobs] == [5, 5, 9, 9, 9, 9]
        assert [int(job.columns) for job in jobs] == [1, 1, 1, 1, 3, 3]
        assert [int(job.run_seed) for job in jobs] == [611, 711, 611, 711, 611, 711]
    elif compare_mode == "candidate_family_overnight":
        assert len(jobs) == 4
        assert [str(job.stage3_tuning_preset_id) for job in jobs] == [
            "stage35_baseline_score_plus_novelty_live_bounded_p9",
        ] * 4
        assert [int(job.period) for job in jobs] == [7, 7, 9, 9]
        assert [int(job.columns) for job in jobs] == [1, 1, 3, 3]
        assert [int(job.run_seed) for job in jobs] == [411, 611, 411, 611]
    elif compare_mode == "candidate_single_p5":
        assert len(jobs) == 1
        assert [str(job.stage3_tuning_preset_id) for job in jobs] == [
            "stage35_baseline_score_plus_novelty_live_bounded_p9",
        ]
        assert [int(job.period) for job in jobs] == [5]
        assert [int(job.columns) for job in jobs] == [1]
        assert [int(job.run_seed) for job in jobs] == [511]
    elif compare_mode == "candidate_single_p7":
        assert len(jobs) == 1
        assert [str(job.stage3_tuning_preset_id) for job in jobs] == [
            "stage35_baseline_score_plus_novelty_live_bounded_p9",
        ]
        assert [int(job.period) for job in jobs] == [7]
        assert [int(job.columns) for job in jobs] == [1]
        assert [int(job.run_seed) for job in jobs] == [411]
    elif compare_mode == "candidate_single_p9_seed611":
        assert len(jobs) == 1
        assert [str(job.stage3_tuning_preset_id) for job in jobs] == [
            "stage35_baseline_score_plus_novelty_live_bounded_p9",
        ]
        assert [int(job.period) for job in jobs] == [9]
        assert [int(job.columns) for job in jobs] == [3]
        assert [int(job.run_seed) for job in jobs] == [611]
    elif compare_mode == "candidate_single_p9_seed711":
        assert len(jobs) == 1
        assert [str(job.stage3_tuning_preset_id) for job in jobs] == [
            "stage35_baseline_score_plus_novelty_live_bounded_p9",
        ]
        assert [int(job.period) for job in jobs] == [9]
        assert [int(job.columns) for job in jobs] == [3]
        assert [int(job.run_seed) for job in jobs] == [711]
    elif compare_mode == "candidate_single_p9_seed811":
        assert len(jobs) == 1
        assert [str(job.stage3_tuning_preset_id) for job in jobs] == [
            "stage35_baseline_score_plus_novelty_live_bounded_p9",
        ]
        assert [int(job.period) for job in jobs] == [9]
        assert [int(job.columns) for job in jobs] == [3]
        assert [int(job.run_seed) for job in jobs] == [811]
    elif compare_mode == "candidate_single_p9_seed911":
        assert len(jobs) == 1
        assert [str(job.stage3_tuning_preset_id) for job in jobs] == [
            "stage35_baseline_score_plus_novelty_live_bounded_p9",
        ]
        assert [int(job.period) for job in jobs] == [9]
        assert [int(job.columns) for job in jobs] == [3]
        assert [int(job.run_seed) for job in jobs] == [911]
    elif compare_mode == "candidate_single_p9_seed1011":
        assert len(jobs) == 1
        assert [str(job.stage3_tuning_preset_id) for job in jobs] == [
            "stage35_baseline_score_plus_novelty_live_bounded_p9",
        ]
        assert [int(job.period) for job in jobs] == [9]
        assert [int(job.columns) for job in jobs] == [3]
        assert [int(job.run_seed) for job in jobs] == [1011]
    elif compare_mode == "candidate_pair_p9_seed1111_1211":
        assert len(jobs) == 2
        assert [str(job.stage3_tuning_preset_id) for job in jobs] == [
            "stage35_baseline_score_plus_novelty_live_bounded_p9",
            "stage35_baseline_score_plus_novelty_live_bounded_p9",
        ]
        assert [int(job.period) for job in jobs] == [9, 9]
        assert [int(job.columns) for job in jobs] == [3, 3]
        assert [int(job.run_seed) for job in jobs] == [1111, 1211]
    elif compare_mode == "candidate_triple_p9_seed1311_1411_1511":
        assert len(jobs) == 3
        assert [str(job.stage3_tuning_preset_id) for job in jobs] == [
            "stage35_baseline_score_plus_novelty_live_bounded_p9",
            "stage35_baseline_score_plus_novelty_live_bounded_p9",
            "stage35_baseline_score_plus_novelty_live_bounded_p9",
        ]
        assert [int(job.period) for job in jobs] == [9, 9, 9]
        assert [int(job.columns) for job in jobs] == [3, 3, 3]
        assert [int(job.run_seed) for job in jobs] == [1311, 1411, 1511]
    elif compare_mode == "candidate_single_p9_seed611_legacy":
        assert len(jobs) == 1
        assert [str(job.stage3_tuning_preset_id) for job in jobs] == [
            "stage35_baseline_legacy_live_bounded_p9",
        ]
        assert [int(job.period) for job in jobs] == [9]
        assert [int(job.columns) for job in jobs] == [3]
        assert [int(job.run_seed) for job in jobs] == [611]
    else:
        expected_presets = list(preset_ids)
        assert [int(job.run_seed) for job in jobs] == [411] * len(expected_presets)
        assert [str(job.stage3_tuning_preset_id) for job in jobs] == expected_presets


def test_current_fixture_matrix_control_files_are_derived_from_experiment_id() -> None:
    experiment_run_id = str(run_matrix_mod.MATRIX_CONTROL_FILES.experiment_run_id)
    assert str(run_matrix_mod.MATRIX_CONTROL_FILES.experiment_run_id) == experiment_run_id
    assert run_matrix_mod.RUN_STATE_PATH == run_matrix_mod.MATRIX_CONTROL_FILES.run_state_path
    assert run_matrix_mod.RUN_EVENTS_PATH == run_matrix_mod.MATRIX_CONTROL_FILES.run_events_path
    assert run_matrix_mod.PLAN_OUTPUT_PATH == run_matrix_mod.MATRIX_CONTROL_FILES.plan_output_path
    assert experiment_run_id.startswith("tune_v")
    assert "stage35_baseline_selector" in experiment_run_id
    preset_ids = tuple(str(x) for x in run_matrix_mod.STAGE3_TUNING_PRESET_IDS)
    compare_mode = str(
        fixture_matrix_config_mod.STAGE35_BASELINE_SELECTOR_COMPARE_MODE
    )
    if compare_mode == "candidate_ladder_small":
        assert "ladder_small" in experiment_run_id
        assert "6job" in experiment_run_id
        assert "candidate_live_bounded" in experiment_run_id
    elif compare_mode == "candidate_family_overnight":
        assert "family_overnight" in experiment_run_id
        assert "seed411_611" in experiment_run_id
        assert "4job" in experiment_run_id
        assert "candidate_live_bounded" in experiment_run_id
    elif compare_mode == "candidate_single_p5":
        assert "p5c1" in experiment_run_id
        assert "seed511" in experiment_run_id
        assert "1job" in experiment_run_id
        assert "candidate_live_bounded" in experiment_run_id
    elif compare_mode == "candidate_single_p7":
        assert "p7c1" in experiment_run_id
        assert "seed411" in experiment_run_id
        assert "1job" in experiment_run_id
        assert "candidate_live_bounded" in experiment_run_id
    elif compare_mode == "candidate_single_p9_seed611":
        assert "p9c3" in experiment_run_id
        assert "seed611" in experiment_run_id
        assert "1job" in experiment_run_id
        assert "candidate_live_bounded" in experiment_run_id
        assert "space_map_v1" in experiment_run_id
    elif compare_mode == "candidate_single_p9_seed711":
        assert "p9c3" in experiment_run_id
        assert "seed711" in experiment_run_id
        assert "1job" in experiment_run_id
        assert "candidate_live_bounded" in experiment_run_id
        assert "space_map_v1" in experiment_run_id
    elif compare_mode == "candidate_single_p9_seed811":
        assert "p9c3" in experiment_run_id
        assert "seed811" in experiment_run_id
        assert "1job" in experiment_run_id
        assert "candidate_live_bounded" in experiment_run_id
        assert "space_map_v1" in experiment_run_id
    elif compare_mode == "candidate_single_p9_seed911":
        assert "p9c3" in experiment_run_id
        assert "seed911" in experiment_run_id
        assert "1job" in experiment_run_id
        assert "candidate_live_bounded" in experiment_run_id
        assert "space_map_v1" in experiment_run_id
    elif compare_mode == "candidate_single_p9_seed1011":
        assert "p9c3" in experiment_run_id
        assert "seed1011" in experiment_run_id
        assert "1job" in experiment_run_id
        assert "candidate_live_bounded" in experiment_run_id
        assert "space_map_v1" in experiment_run_id
    elif compare_mode == "candidate_pair_p9_seed1111_1211":
        assert "p9c3" in experiment_run_id
        assert "seed1111_1211" in experiment_run_id
        assert "2job" in experiment_run_id
        assert "candidate_live_bounded" in experiment_run_id
        assert "space_map_v1" in experiment_run_id
    elif compare_mode == "candidate_triple_p9_seed1311_1411_1511":
        assert "p9c3" in experiment_run_id
        assert "seed1311_1411_1511" in experiment_run_id
        assert "3job" in experiment_run_id
        assert "candidate_live_bounded" in experiment_run_id
        assert "space_map_v1" in experiment_run_id
    elif compare_mode == "candidate_single_p9_seed611_legacy":
        assert "p9c3" in experiment_run_id
        assert "seed611" in experiment_run_id
        assert "1job" in experiment_run_id
        assert "legacy_control" in experiment_run_id
        assert "live_bounded" in experiment_run_id
        assert "space_map_v1" in experiment_run_id
    else:
        assert "seed411" in experiment_run_id
    if compare_mode == "candidate_ladder_small":
        assert preset_ids == ("stage35_baseline_score_plus_novelty_live_bounded_p9",)
    elif compare_mode == "candidate_family_overnight":
        assert preset_ids == ("stage35_baseline_score_plus_novelty_live_bounded_p9",)
    elif compare_mode == "candidate_single_p5":
        assert preset_ids == ("stage35_baseline_score_plus_novelty_live_bounded_p9",)
    elif compare_mode == "candidate_single_p7":
        assert preset_ids == ("stage35_baseline_score_plus_novelty_live_bounded_p9",)
    elif compare_mode == "candidate_single_p9_seed611":
        assert preset_ids == ("stage35_baseline_score_plus_novelty_live_bounded_p9",)
    elif compare_mode == "candidate_single_p9_seed711":
        assert preset_ids == ("stage35_baseline_score_plus_novelty_live_bounded_p9",)
    elif compare_mode == "candidate_single_p9_seed811":
        assert preset_ids == ("stage35_baseline_score_plus_novelty_live_bounded_p9",)
    elif compare_mode == "candidate_single_p9_seed911":
        assert preset_ids == ("stage35_baseline_score_plus_novelty_live_bounded_p9",)
    elif compare_mode == "candidate_single_p9_seed1011":
        assert preset_ids == ("stage35_baseline_score_plus_novelty_live_bounded_p9",)
    elif compare_mode == "candidate_pair_p9_seed1111_1211":
        assert preset_ids == ("stage35_baseline_score_plus_novelty_live_bounded_p9",)
    elif compare_mode == "candidate_triple_p9_seed1311_1411_1511":
        assert preset_ids == ("stage35_baseline_score_plus_novelty_live_bounded_p9",)
    elif compare_mode == "candidate_single_p9_seed611_legacy":
        assert preset_ids == ("stage35_baseline_legacy_live_bounded_p9",)
    elif preset_ids == (
        "stage35_baseline_legacy_canary_p9",
        "stage35_baseline_score_plus_novelty_canary_p9",
    ):
        assert "2job" in experiment_run_id
        assert "canary" in experiment_run_id
    elif preset_ids in {
        ("stage35_baseline_score_plus_novelty_live_p9",),
        ("stage35_baseline_score_plus_novelty_live_bounded_p9",),
    }:
        assert "1job" in experiment_run_id
        assert "candidate_live" in experiment_run_id
    else:
        assert "2job" in experiment_run_id
        assert "live_compare" in experiment_run_id


def test_build_matrix_mainflow_state_is_narrow_and_explicit() -> None:
    state = run_matrix_mod.build_matrix_mainflow_state()

    assert "main" not in state
    assert "load_json" not in state
    assert "write_json" not in state
    assert "refresh_catalog_safely" not in state
    assert str(state["EXPERIMENT_RUN_ID"]) == str(run_matrix_mod.MATRIX_CONTROL_FILES.experiment_run_id)
    assert state["RUN_STATE_PATH"] == run_matrix_mod.RUN_STATE_PATH
    assert state["RUN_EVENTS_PATH"] == run_matrix_mod.RUN_EVENTS_PATH
    assert state["PLAN_OUTPUT_PATH"] == run_matrix_mod.PLAN_OUTPUT_PATH
    compare_mode = str(
        fixture_matrix_config_mod.STAGE35_BASELINE_SELECTOR_COMPARE_MODE
    )
    if compare_mode == "candidate_ladder_small":
        assert tuple(int(x) for x in state["RUN_SEEDS"]) == (611, 711)
    elif compare_mode == "candidate_family_overnight":
        assert tuple(int(x) for x in state["RUN_SEEDS"]) == (411, 611)
    elif compare_mode == "candidate_single_p5":
        assert tuple(int(x) for x in state["RUN_SEEDS"]) == (511,)
    elif compare_mode == "candidate_single_p7":
        assert tuple(int(x) for x in state["RUN_SEEDS"]) == (411,)
    elif compare_mode == "candidate_single_p9_seed611":
        assert tuple(int(x) for x in state["RUN_SEEDS"]) == (611,)
    elif compare_mode == "candidate_single_p9_seed711":
        assert tuple(int(x) for x in state["RUN_SEEDS"]) == (711,)
    elif compare_mode == "candidate_single_p9_seed811":
        assert tuple(int(x) for x in state["RUN_SEEDS"]) == (811,)
    elif compare_mode == "candidate_single_p9_seed911":
        assert tuple(int(x) for x in state["RUN_SEEDS"]) == (911,)
    elif compare_mode == "candidate_single_p9_seed1011":
        assert tuple(int(x) for x in state["RUN_SEEDS"]) == (1011,)
    elif compare_mode == "candidate_pair_p9_seed1111_1211":
        assert tuple(int(x) for x in state["RUN_SEEDS"]) == (1111, 1211)
    elif compare_mode == "candidate_triple_p9_seed1311_1411_1511":
        assert tuple(int(x) for x in state["RUN_SEEDS"]) == (1311, 1411, 1511)
    elif compare_mode == "candidate_single_p9_seed611_legacy":
        assert tuple(int(x) for x in state["RUN_SEEDS"]) == (611,)
    else:
        assert tuple(int(x) for x in state["RUN_SEEDS"]) == (411,)
    expected_presets = tuple(str(x) for x in run_matrix_mod.STAGE3_TUNING_PRESET_IDS)
    assert tuple(str(x) for x in state["STAGE3_TUNING_PRESET_IDS"]) == expected_presets
    if compare_mode == "candidate_single_p5":
        assert tuple(int(x) for x in state["PERIODS_OVERRIDE"] or ()) == (5,)
    elif compare_mode == "candidate_single_p7":
        assert tuple(int(x) for x in state["PERIODS_OVERRIDE"] or ()) == (7,)
    elif compare_mode == "candidate_single_p9_seed611":
        assert tuple(int(x) for x in state["PERIODS_OVERRIDE"] or ()) == (9,)
    elif compare_mode == "candidate_single_p9_seed711":
        assert tuple(int(x) for x in state["PERIODS_OVERRIDE"] or ()) == (9,)
    elif compare_mode == "candidate_single_p9_seed811":
        assert tuple(int(x) for x in state["PERIODS_OVERRIDE"] or ()) == (9,)
    elif compare_mode == "candidate_single_p9_seed911":
        assert tuple(int(x) for x in state["PERIODS_OVERRIDE"] or ()) == (9,)
    elif compare_mode == "candidate_single_p9_seed1011":
        assert tuple(int(x) for x in state["PERIODS_OVERRIDE"] or ()) == (9,)
    elif compare_mode == "candidate_pair_p9_seed1111_1211":
        assert tuple(int(x) for x in state["PERIODS_OVERRIDE"] or ()) == (9,)
    elif compare_mode == "candidate_single_p9_seed611_legacy":
        assert tuple(int(x) for x in state["PERIODS_OVERRIDE"] or ()) == (9,)
    elif compare_mode == "candidate_family_overnight":
        assert tuple(int(x) for x in state["PERIODS_OVERRIDE"] or ()) == (7, 9)


def test_fixture_matrix_run_state_campaign_config_path_is_repo_relative() -> None:
    repo_root = Path.cwd()
    rel_path = fixture_mainflow_mod._repo_relative_path_str(
        path=repo_root / "tools/benchmarks/community/examples/campaign_config_v1_1.json",
        repo_root=repo_root,
    )

    assert rel_path == "tools/benchmarks/community/examples/campaign_config_v1_1.json"
    assert not Path(rel_path).is_absolute()


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


def test_apply_job_sets_stage3_entry_policy_overrides() -> None:
    calls: list[dict[str, object]] = []
    no_wli = SimpleNamespace(
        RUN_STAGE3_SPAN_BASIN_K_SWEEP=True,
        STAGE3_SPAN_BASIN_K_SWEEP_VALUES=[96],
        STAGE3_SPAN_BASIN_JUDGE_K=96,
        SPAN_DECISION_ROLE_ENABLED=False,
        STAGE3_SPAN_AUX_ROLE="off",
        SCORING_EXPERIMENT_PROFILE="off",
        STAGE3_INIT_KEYS_CAP=192,
        STAGE3_ENTRY_ALLOCATION_POLICY="legacy_fixed_budget",
        STAGE3_ENTRY_MUTATIONS_PER_PROMOTED=1,
        SOLVER_STAGE3={
            "steps": 3200,
        },
    )
    no_wli.configure_campaign_run = lambda **kwargs: calls.append(dict(kwargs))
    job = SimpleNamespace(
        run_seed=211,
        period=9,
        columns=3,
        length=1000,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m12_b34_stage3avg_fulltext_v1",
        heartbeat_seconds=180,
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
        stage3_span_basin_k_sweep_values=(64,),
        force_stage3_init_keys_cap=288,
        force_stage3_entry_allocation_policy="constant_local_depth",
        force_stage3_entry_mutations_per_promoted=1,
    )
    assert calls, "configure_campaign_run should be called"
    assert int(no_wli.STAGE3_INIT_KEYS_CAP) == 288
    assert str(no_wli.STAGE3_ENTRY_ALLOCATION_POLICY) == "constant_local_depth"
    assert int(no_wli.STAGE3_ENTRY_MUTATIONS_PER_PROMOTED) == 1
    assert "entry_allocation_policy" not in dict(no_wli.SOLVER_STAGE3)
    assert "entry_mutations_per_promoted" not in dict(no_wli.SOLVER_STAGE3)


def test_apply_job_sets_stage3_phasec_start_policy_override() -> None:
    calls: list[dict[str, object]] = []
    no_wli = SimpleNamespace(
        RUN_STAGE3_SPAN_BASIN_K_SWEEP=True,
        STAGE3_SPAN_BASIN_K_SWEEP_VALUES=[96],
        STAGE3_SPAN_BASIN_JUDGE_K=96,
        SPAN_DECISION_ROLE_ENABLED=False,
        STAGE3_SPAN_AUX_ROLE="off",
        SCORING_EXPERIMENT_PROFILE="off",
        STAGE3_PHASEC_START_POLICY="source_order",
    )
    no_wli.configure_campaign_run = lambda **kwargs: calls.append(dict(kwargs))
    job = SimpleNamespace(
        run_seed=411,
        period=9,
        columns=3,
        length=1000,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m12_b34_stage3avg_fulltext_v1",
        heartbeat_seconds=180,
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
        stage3_span_basin_k_sweep_values=(64,),
        force_stage3_phasec_start_policy="balanced_sources_v1",
    )
    assert calls, "configure_campaign_run should be called"
    assert str(no_wli.STAGE3_PHASEC_START_POLICY) == "balanced_sources_v1"


def test_apply_job_sets_stage35_baseline_selector_override() -> None:
    calls: list[dict[str, object]] = []
    no_wli = SimpleNamespace(
        RUN_STAGE3_SPAN_BASIN_K_SWEEP=True,
        STAGE3_SPAN_BASIN_K_SWEEP_VALUES=[96],
        STAGE3_SPAN_BASIN_JUDGE_K=96,
        SPAN_DECISION_ROLE_ENABLED=False,
        STAGE3_SPAN_AUX_ROLE="off",
        SCORING_EXPERIMENT_PROFILE="off",
        STAGE35_BASELINE_SELECTOR="legacy",
    )
    no_wli.configure_campaign_run = lambda **kwargs: calls.append(dict(kwargs))
    job = SimpleNamespace(
        run_seed=411,
        period=9,
        columns=3,
        length=1000,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m12_b34_stage3avg_fulltext_v1",
        heartbeat_seconds=180,
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
        stage3_span_basin_k_sweep_values=(64,),
        force_stage35_baseline_selector="score_plus_novelty",
    )
    assert calls, "configure_campaign_run should be called"
    assert str(no_wli.STAGE35_BASELINE_SELECTOR) == "score_plus_novelty"


def test_apply_job_preserves_stage35_runtime_cap_as_float() -> None:
    calls: list[dict[str, object]] = []
    no_wli = SimpleNamespace(
        RUN_STAGE3_SPAN_BASIN_K_SWEEP=True,
        STAGE3_SPAN_BASIN_K_SWEEP_VALUES=[96],
        STAGE3_SPAN_BASIN_JUDGE_K=96,
        SPAN_DECISION_ROLE_ENABLED=False,
        STAGE3_SPAN_AUX_ROLE="off",
        SCORING_EXPERIMENT_PROFILE="off",
        STAGE35_CFG={},
    )
    no_wli.configure_campaign_run = lambda **kwargs: calls.append(dict(kwargs))
    job = SimpleNamespace(
        run_seed=411,
        period=9,
        columns=3,
        length=1000,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m12_b34_stage3avg_fulltext_v1",
        heartbeat_seconds=180,
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
        stage3_span_basin_k_sweep_values=(64,),
        force_stage35_cfg={
            "seed_keep": 2,
            "beam_width": 1,
            "max_runtime_seconds": 12.5,
        },
    )
    assert calls, "configure_campaign_run should be called"
    assert dict(no_wli.STAGE35_CFG) == {
        "seed_keep": 2,
        "beam_width": 1,
        "max_runtime_seconds": pytest.approx(12.5),
    }


def test_apply_job_sets_stage3_phaseb_family_preservation_override() -> None:
    calls: list[dict[str, object]] = []
    no_wli = SimpleNamespace(
        RUN_STAGE3_SPAN_BASIN_K_SWEEP=True,
        STAGE3_SPAN_BASIN_K_SWEEP_VALUES=[96],
        STAGE3_SPAN_BASIN_JUDGE_K=96,
        SPAN_DECISION_ROLE_ENABLED=False,
        STAGE3_SPAN_AUX_ROLE="off",
        SCORING_EXPERIMENT_PROFILE="off",
        STAGE3_PHASEB_FAMILY_PRESERVATION_POLICY="off",
        STAGE3_PHASEB_FAMILY_VIEW_ID="prefix_hamming_le_24",
        STAGE3_PHASEB_FAMILY_RESERVED_SLOTS=0,
    )
    no_wli.configure_campaign_run = lambda **kwargs: calls.append(dict(kwargs))
    job = SimpleNamespace(
        run_seed=411,
        period=9,
        columns=3,
        length=1000,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m12_b34_stage3avg_fulltext_v1",
        heartbeat_seconds=180,
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
        stage3_span_basin_k_sweep_values=(64,),
        force_stage3_phaseb_family_preservation_policy="reserve_by_family_v1",
        force_stage3_phaseb_family_view_id="prefix_hamming_le_24",
        force_stage3_phaseb_family_reserved_slots=2,
    )
    assert calls, "configure_campaign_run should be called"
    assert (
        str(no_wli.STAGE3_PHASEB_FAMILY_PRESERVATION_POLICY)
        == "reserve_by_family_v1"
    )
    assert str(no_wli.STAGE3_PHASEB_FAMILY_VIEW_ID) == "prefix_hamming_le_24"
    assert int(no_wli.STAGE3_PHASEB_FAMILY_RESERVED_SLOTS) == 2


def test_fixture_matrix_api_forwards_stage35_proof_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_apply_job_impl(**kwargs) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(fixture_api, "_apply_job_impl", _fake_apply_job_impl)

    job = SimpleNamespace(
        fixture_id="fixture_001",
        period=9,
        columns=3,
        length=1000,
        run_seed=511,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m12_b34_stage3avg_fulltext_v1",
        heartbeat_seconds=180,
        text_offsets=(0,),
        scorer_impl="torch",
        scorer_stage3_impl_avg_fulltext="torch",
        scoring_experiment_profile="c_min_late",
        schedule_early="a_char1_avg_fulltext",
        schedule_middle="m_char12_avg_fulltext",
        schedule_late="b_char4_avg_fulltext",
        stage3_tuning_preset_id="stage35_proof_p9_8h",
        span_ab_case_id="none",
        span_decision_role_enabled=False,
        tier_name=lambda: "fixture_fixture_001_p9_c3_l1000",
        scorer_schedule=lambda: {
            "early": "a_char1_avg_fulltext",
            "middle": "m_char12_avg_fulltext",
            "late": "b_char4_avg_fulltext",
        },
    )

    overrides = fixture_api._resolve_stage3_tuning_overrides_for_job(job)
    assert int(overrides["force_stage3_initial_keys"]) == 64
    assert int(overrides["force_stage3_phaseb_top_n"]) == 8
    assert dict(overrides["force_stage3_phaseb_cfg"]) == {
        "steps": 2200,
        "inner_batch": 128,
        "col_every": 1,
        "col_batch": 96,
        "slip_every": 70,
        "stall_rounds": 240,
        "stall_slip_limit": 8,
        "slip_swaps": 28,
        "progress_pct": 1,
        "print_progress": True,
    }
    assert bool(overrides["force_stage3_phasec_enabled"]) is True
    assert dict(overrides["force_stage3_phasec_cfg"]) == {
        "steps": 96,
        "proposals_per_step": 16,
        "three_cycle_prob": 0.2,
        "lexical_min_match": 0.72,
        "lexical_match_tie_eps": 0.01,
        "lexical_score_tie_eps": 0.002,
        "lexical_max_calls": 128,
    }
    assert bool(overrides["force_stage35_enabled"]) is True
    assert dict(overrides["force_stage35_cfg"]) == {
        "seed_keep": 4,
        "beam_width": 4,
        "archive_keep": 16,
        "rounds": 3,
        "mini_search_steps": 2,
        "mini_search_beam_width": 3,
        "mini_search_top_symbols": 10,
        "mini_search_final_keep": 2,
        "mini_search_keep_all_rows": 1,
        "accept_score_min_gain": 0,
        "accept_search_score_max_drop": 0,
    }

    fixture_api.apply_job(job)

    assert int(captured["force_stage3_initial_keys"]) == 64
    assert int(captured["force_stage3_phaseb_top_n"]) == 8
    assert dict(captured["force_stage3_phaseb_cfg"]) == {
        "steps": 2200,
        "inner_batch": 128,
        "col_every": 1,
        "col_batch": 96,
        "slip_every": 70,
        "stall_rounds": 240,
        "stall_slip_limit": 8,
        "slip_swaps": 28,
        "progress_pct": 1,
        "print_progress": True,
    }
    assert bool(captured["force_stage3_phasec_enabled"]) is True
    assert dict(captured["force_stage3_phasec_cfg"]) == {
        "steps": 96,
        "proposals_per_step": 16,
        "three_cycle_prob": 0.2,
        "lexical_min_match": 0.72,
        "lexical_match_tie_eps": 0.01,
        "lexical_score_tie_eps": 0.002,
        "lexical_max_calls": 128,
    }
    assert bool(captured["force_stage35_enabled"]) is True
    assert dict(captured["force_stage35_cfg"]) == {
        "seed_keep": 4,
        "beam_width": 4,
        "archive_keep": 16,
        "rounds": 3,
        "mini_search_steps": 2,
        "mini_search_beam_width": 3,
        "mini_search_top_symbols": 10,
        "mini_search_final_keep": 2,
        "mini_search_keep_all_rows": 1,
        "accept_score_min_gain": 0,
        "accept_search_score_max_drop": 0,
    }


def test_fixture_matrix_api_forwards_stage35_baseline_selector_compare_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_apply_job_impl(**kwargs) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(fixture_api, "_apply_job_impl", _fake_apply_job_impl)

    job = SimpleNamespace(
        fixture_id="fixture_001",
        period=9,
        columns=3,
        length=1000,
        run_seed=411,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m12_b34_stage3avg_fulltext_v1",
        heartbeat_seconds=180,
        text_offsets=(0,),
        scorer_impl="torch",
        scorer_stage3_impl_avg_fulltext="torch",
        scoring_experiment_profile="c_min_late",
        schedule_early="a_char1_avg_fulltext",
        schedule_middle="m_char12_avg_fulltext",
        schedule_late="b_char4_avg_fulltext",
        stage3_tuning_preset_id="stage35_baseline_score_plus_novelty_canary_p9",
        span_ab_case_id="none",
        span_decision_role_enabled=False,
        tier_name=lambda: "fixture_fixture_001_p9_c3_l1000",
        scorer_schedule=lambda: {
            "early": "a_char1_avg_fulltext",
            "middle": "m_char12_avg_fulltext",
            "late": "b_char4_avg_fulltext",
        },
    )

    overrides = fixture_api._resolve_stage3_tuning_overrides_for_job(job)
    assert int(overrides["force_stage3_phaseb_top_n"]) == 16
    assert int(overrides["force_stage3_phasec_start_keys"]) == 4
    assert bool(overrides["force_stage35_enabled"]) is True
    assert str(overrides["force_stage35_baseline_selector"]) == "score_plus_novelty"
    assert dict(overrides["force_stage35_cfg"]) == {
        "seed_keep": 2,
        "beam_width": 2,
        "archive_keep": 6,
        "rounds": 1,
        "mini_search_steps": 1,
        "mini_search_beam_width": 2,
        "mini_search_top_symbols": 6,
        "mini_search_final_keep": 1,
        "mini_search_keep_all_rows": 0,
        "accept_score_min_gain": 0,
        "accept_search_score_max_drop": 0,
    }

    fixture_api.apply_job(job)

    assert int(captured["force_stage3_phaseb_top_n"]) == 16
    assert bool(captured["force_stage35_enabled"]) is True
    assert str(captured["force_stage35_baseline_selector"]) == "score_plus_novelty"
    assert dict(captured["force_stage35_cfg"]) == {
        "seed_keep": 2,
        "beam_width": 2,
        "archive_keep": 6,
        "rounds": 1,
        "mini_search_steps": 1,
        "mini_search_beam_width": 2,
        "mini_search_top_symbols": 6,
        "mini_search_final_keep": 1,
        "mini_search_keep_all_rows": 0,
        "accept_score_min_gain": 0,
        "accept_search_score_max_drop": 0,
    }


def test_fixture_matrix_api_forwards_stage3_recovery_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_apply_job_impl(**kwargs) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(fixture_api, "_apply_job_impl", _fake_apply_job_impl)

    job = SimpleNamespace(
        fixture_id="fixture_001",
        period=9,
        columns=3,
        length=1000,
        run_seed=511,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m12_b34_stage3avg_fulltext_v1",
        heartbeat_seconds=180,
        text_offsets=(0,),
        scorer_impl="torch",
        scorer_stage3_impl_avg_fulltext="torch",
        scoring_experiment_profile="c_min_late",
        schedule_early="a_char1_avg_fulltext",
        schedule_middle="m_char12_avg_fulltext",
        schedule_late="b_char4_avg_fulltext",
        stage3_tuning_preset_id="stage3_recovery_p9_8h",
        span_ab_case_id="none",
        span_decision_role_enabled=False,
        tier_name=lambda: "fixture_fixture_001_p9_c3_l1000",
        scorer_schedule=lambda: {
            "early": "a_char1_avg_fulltext",
            "middle": "m_char12_avg_fulltext",
            "late": "b_char4_avg_fulltext",
        },
    )

    overrides = fixture_api._resolve_stage3_tuning_overrides_for_job(job)
    assert int(overrides["force_stage3_initial_keys"]) == 64
    assert int(overrides["force_stage3_phaseb_top_n"]) == 8
    assert dict(overrides["force_stage3_phaseb_cfg"]) == {
        "steps": 2200,
        "inner_batch": 128,
        "col_every": 1,
        "col_batch": 96,
        "slip_every": 70,
        "stall_rounds": 240,
        "stall_slip_limit": 8,
        "slip_swaps": 28,
        "progress_pct": 1,
        "print_progress": True,
    }
    assert bool(overrides["force_stage3_phasec_enabled"]) is True
    assert dict(overrides["force_stage3_phasec_cfg"]) == {
        "steps": 96,
        "proposals_per_step": 16,
        "three_cycle_prob": 0.2,
        "lexical_min_match": 0.72,
        "lexical_match_tie_eps": 0.01,
        "lexical_score_tie_eps": 0.002,
        "lexical_max_calls": 128,
    }
    assert bool(overrides["force_stage35_enabled"]) is False

    fixture_api.apply_job(job)

    assert int(captured["force_stage3_initial_keys"]) == 64
    assert int(captured["force_stage3_phaseb_top_n"]) == 8
    assert dict(captured["force_stage3_phaseb_cfg"]) == {
        "steps": 2200,
        "inner_batch": 128,
        "col_every": 1,
        "col_batch": 96,
        "slip_every": 70,
        "stall_rounds": 240,
        "stall_slip_limit": 8,
        "slip_swaps": 28,
        "progress_pct": 1,
        "print_progress": True,
    }
    assert bool(captured["force_stage3_phasec_enabled"]) is True
    assert dict(captured["force_stage3_phasec_cfg"]) == {
        "steps": 96,
        "proposals_per_step": 16,
        "three_cycle_prob": 0.2,
        "lexical_min_match": 0.72,
        "lexical_match_tie_eps": 0.01,
        "lexical_score_tie_eps": 0.002,
        "lexical_max_calls": 128,
    }
    assert bool(captured["force_stage35_enabled"]) is False


def test_fixture_matrix_api_forwards_stage3_preserve_tieband_probe_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_apply_job_impl(**kwargs) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(fixture_api, "_apply_job_impl", _fake_apply_job_impl)

    job = SimpleNamespace(
        fixture_id="fixture_001",
        period=9,
        columns=3,
        length=1000,
        run_seed=211,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m12_b34_stage3avg_fulltext_v1",
        heartbeat_seconds=180,
        text_offsets=(0,),
        scorer_impl="torch",
        scorer_stage3_impl_avg_fulltext="torch",
        scoring_experiment_profile="c_min_late",
        schedule_early="a_char1_avg_fulltext",
        schedule_middle="m_char12_avg_fulltext",
        schedule_late="b_char4_avg_fulltext",
        stage3_tuning_preset_id="stage3_preserve_tieband_probe_p9",
        span_ab_case_id="none",
        span_decision_role_enabled=False,
        tier_name=lambda: "fixture_fixture_001_p9_c3_l1000",
        scorer_schedule=lambda: {
            "early": "a_char1_avg_fulltext",
            "middle": "m_char12_avg_fulltext",
            "late": "b_char4_avg_fulltext",
        },
    )

    overrides = fixture_api._resolve_stage3_tuning_overrides_for_job(job)
    assert int(overrides["force_stage3_initial_keys"]) == 64
    assert int(overrides["force_stage3_phaseb_top_n"]) == 8
    assert float(overrides["force_stage3_span_basin_judge_tie_eps"]) == pytest.approx(0.005)
    assert int(overrides["force_stage3_span_basin_judge_tie_max_seeds"]) == 16
    assert bool(overrides["force_stage35_enabled"]) is False

    fixture_api.apply_job(job)

    assert int(captured["force_stage3_initial_keys"]) == 64
    assert int(captured["force_stage3_phaseb_top_n"]) == 8
    assert float(captured["force_stage3_span_basin_judge_tie_eps"]) == pytest.approx(0.005)
    assert int(captured["force_stage3_span_basin_judge_tie_max_seeds"]) == 16
    assert bool(captured["force_stage35_enabled"]) is False


def test_fixture_matrix_api_forwards_stage3_entry_const_local_depth_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_apply_job_impl(**kwargs) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(fixture_api, "_apply_job_impl", _fake_apply_job_impl)

    job = SimpleNamespace(
        fixture_id="fixture_001",
        period=9,
        columns=3,
        length=1000,
        run_seed=211,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m12_b34_stage3avg_fulltext_v1",
        heartbeat_seconds=180,
        text_offsets=(0,),
        scorer_impl="torch",
        scorer_stage3_impl_avg_fulltext="torch",
        scoring_experiment_profile="c_min_late",
        schedule_early="a_char1_avg_fulltext",
        schedule_middle="m_char12_avg_fulltext",
        schedule_late="b_char4_avg_fulltext",
        stage3_tuning_preset_id="stage3_entry_const_local_depth_p9",
        span_ab_case_id="none",
        span_decision_role_enabled=False,
        tier_name=lambda: "fixture_fixture_001_p9_c3_l1000",
        scorer_schedule=lambda: {
            "early": "a_char1_avg_fulltext",
            "middle": "m_char12_avg_fulltext",
            "late": "b_char4_avg_fulltext",
        },
    )

    overrides = fixture_api._resolve_stage3_tuning_overrides_for_job(job)
    assert int(overrides["force_stage3_initial_keys"]) == 64
    assert int(overrides["force_stage3_init_keys_cap"]) == 288
    assert str(overrides["force_stage3_entry_allocation_policy"]) == "constant_local_depth"
    assert int(overrides["force_stage3_entry_mutations_per_promoted"]) == 1
    assert overrides["force_solver_stage3_overrides"] is None

    fixture_api.apply_job(job)

    assert int(captured["force_stage3_initial_keys"]) == 64
    assert int(captured["force_stage3_init_keys_cap"]) == 288
    assert str(captured["force_stage3_entry_allocation_policy"]) == "constant_local_depth"
    assert int(captured["force_stage3_entry_mutations_per_promoted"]) == 1
    assert captured["force_solver_stage3_overrides"] is None


def test_fixture_matrix_api_forwards_stage3_phasec_start_balanced_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_apply_job_impl(**kwargs) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(fixture_api, "_apply_job_impl", _fake_apply_job_impl)

    job = SimpleNamespace(
        fixture_id="fixture_001",
        period=9,
        columns=3,
        length=1000,
        run_seed=411,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m12_b34_stage3avg_fulltext_v1",
        heartbeat_seconds=180,
        text_offsets=(0,),
        scorer_impl="torch",
        scorer_stage3_impl_avg_fulltext="torch",
        scoring_experiment_profile="c_min_late",
        schedule_early="a_char1_avg_fulltext",
        schedule_middle="m_char12_avg_fulltext",
        schedule_late="b_char4_avg_fulltext",
        stage3_tuning_preset_id="stage3_phasec_start_balanced_p9",
        span_ab_case_id="none",
        span_decision_role_enabled=False,
        tier_name=lambda: "fixture_fixture_001_p9_c3_l1000",
        scorer_schedule=lambda: {
            "early": "a_char1_avg_fulltext",
            "middle": "m_char12_avg_fulltext",
            "late": "b_char4_avg_fulltext",
        },
    )

    overrides = fixture_api._resolve_stage3_tuning_overrides_for_job(job)
    assert int(overrides["force_stage3_initial_keys"]) == 64
    assert int(overrides["force_stage3_phasec_start_keys"]) == 6
    assert str(overrides["force_stage3_phasec_start_policy"]) == "balanced_sources_v1"
    assert bool(overrides["force_stage35_enabled"]) is False

    fixture_api.apply_job(job)

    assert int(captured["force_stage3_initial_keys"]) == 64
    assert int(captured["force_stage3_phasec_start_keys"]) == 6
    assert str(captured["force_stage3_phasec_start_policy"]) == "balanced_sources_v1"
    assert bool(captured["force_stage35_enabled"]) is False


def test_fixture_matrix_api_forwards_stage3_phaseb_family_preserve_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_apply_job_impl(**kwargs) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(fixture_api, "_apply_job_impl", _fake_apply_job_impl)

    job = SimpleNamespace(
        fixture_id="fixture_001",
        period=9,
        columns=3,
        length=1000,
        run_seed=411,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m12_b34_stage3avg_fulltext_v1",
        heartbeat_seconds=180,
        text_offsets=(0,),
        scorer_impl="torch",
        scorer_stage3_impl_avg_fulltext="torch",
        scoring_experiment_profile="c_min_late",
        schedule_early="a_char1_avg_fulltext",
        schedule_middle="m_char12_avg_fulltext",
        schedule_late="b_char4_avg_fulltext",
        stage3_tuning_preset_id="stage3_phaseb_family_preserve_p9",
        span_ab_case_id="none",
        span_decision_role_enabled=False,
        tier_name=lambda: "fixture_fixture_001_p9_c3_l1000",
        scorer_schedule=lambda: {
            "early": "a_char1_avg_fulltext",
            "middle": "m_char12_avg_fulltext",
            "late": "b_char4_avg_fulltext",
        },
    )

    overrides = fixture_api._resolve_stage3_tuning_overrides_for_job(job)
    assert int(overrides["force_stage3_initial_keys"]) == 64
    assert int(overrides["force_stage3_phasec_start_keys"]) == 6
    assert (
        str(overrides["force_stage3_phaseb_family_preservation_policy"])
        == "reserve_by_family_v1"
    )
    assert str(overrides["force_stage3_phaseb_family_view_id"]) == "prefix_hamming_le_24"
    assert int(overrides["force_stage3_phaseb_family_reserved_slots"]) == 2
    assert bool(overrides["force_stage35_enabled"]) is False

    fixture_api.apply_job(job)

    assert int(captured["force_stage3_initial_keys"]) == 64
    assert int(captured["force_stage3_phasec_start_keys"]) == 6
    assert (
        str(captured["force_stage3_phaseb_family_preservation_policy"])
        == "reserve_by_family_v1"
    )
    assert str(captured["force_stage3_phaseb_family_view_id"]) == "prefix_hamming_le_24"
    assert int(captured["force_stage3_phaseb_family_reserved_slots"]) == 2
    assert bool(captured["force_stage35_enabled"]) is False


def test_fixture_matrix_api_rejects_unknown_stage3_tuning_preset_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        fixture_api,
        "STAGE3_TUNING_PRESETS",
        {"known_preset": {"force_stage3_phaseb_top_n": 8}},
    )

    job = SimpleNamespace(
        stage3_tuning_preset_id="missing_preset",
    )

    with pytest.raises(KeyError, match="unknown stage3 tuning preset id: missing_preset"):
        fixture_api._resolve_stage3_tuning_overrides_for_job(job)


def test_fixture_matrix_api_rejects_unknown_configured_preset_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fixture_api, "ENABLE_STAGE3_TUNING_PRESET_MATRIX", True)
    monkeypatch.setattr(fixture_api, "STAGE3_TUNING_PRESET_IDS", ("missing_preset",))
    monkeypatch.setattr(
        fixture_api,
        "STAGE3_TUNING_PRESETS",
        {"known_preset": {"force_stage3_phaseb_top_n": 8}},
    )

    with pytest.raises(KeyError, match="unknown stage3 tuning preset id: missing_preset"):
        fixture_api.resolve_stage3_tuning_preset_ids()
