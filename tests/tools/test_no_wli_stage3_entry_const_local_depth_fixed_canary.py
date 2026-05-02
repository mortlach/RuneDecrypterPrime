from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli import fixture_matrix_api as fixture_api
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_stage3_entry_const_local_depth_fixed_canary_v1 as extract_mod,
    run_stage3_entry_const_local_depth_fixed_canary_v1 as run_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixed_instance_io import (
    load_fixed_cipher_panel_spec,
    load_fixed_instance_spec_map,
)


pytestmark = pytest.mark.tier_a


def test_fixed_canary_driver_materializes_two_jobs() -> None:
    config = run_mod.build_matrix_mainflow_config()
    repo_root = Path.cwd()
    panel = load_fixed_cipher_panel_spec(repo_root / run_mod.FIXED_PANEL_PATH)
    fixed_spec_map = load_fixed_instance_spec_map(
        fixture_dir=repo_root / run_mod.FIXED_INSTANCE_FIXTURE_DIR
    )
    fixtures = [fixed_spec_map[str(x)] for x in panel.instance_fixture_ids]
    schedules = fixture_api.build_schedule_matrix(
        mode=str(config.schedule_coverage_mode),
        explicit_schedules=config.explicit_schedules,
    )
    jobs = fixture_api.build_fixed_instance_jobs(
        fixed_instance_specs=fixtures,
        search_seeds=panel.search_seeds,
        run_mode=str(config.run_mode),
        profile_id=str(config.no_wli_profile_id),
        heartbeat_seconds=int(config.heartbeat_seconds),
        scorer_impl=str(config.scorer_impl),
        scorer_stage3_impl_avg_fulltext=str(config.scorer_stage3_impl_avg_fulltext),
        scoring_experiment_profiles=config.scoring_experiment_profiles,
        stage3_tuning_preset_ids=config.stage3_tuning_preset_ids,
        schedules=schedules,
        enable_span_ab_pair=bool(config.enable_span_ab_pair),
        span_ab_decision_role=str(config.span_ab_decision_role),
    )

    presets = run_mod.build_active_presets()

    assert str(panel.panel_id) == "p9_c3_solver_panel_1111_search7004_v1"
    assert tuple(int(x) for x in panel.search_seeds) == (7004,)
    assert tuple(int(x) for x in config.text_offsets) == (5,)
    assert tuple(str(x) for x in config.stage3_tuning_preset_ids) == (
        run_mod.CONTROL_PRESET_ID,
        run_mod.CANDIDATE_PRESET_ID,
    )
    assert len(jobs) == 2
    assert float(config.max_wallclock_seconds) == pytest.approx(8.0 * 60.0 * 60.0)
    assert bool(config.stop_on_error) is True
    assert (
        presets[run_mod.CANDIDATE_PRESET_ID].force_stage3_entry_allocation_policy
        == "constant_local_depth"
    )
    assert int(presets[run_mod.CANDIDATE_PRESET_ID].force_stage3_init_keys_cap) == 288
    assert bool(presets[run_mod.CONTROL_PRESET_ID].force_stage35_enabled) is True


def test_fixed_canary_recommendation_thresholds() -> None:
    rows = [
        {
            "preset_id": run_mod.CONTROL_PRESET_ID,
            "best_match_ratio": 0.423,
            "best_match_delta_vs_retained": 0.0,
            "entry_target_before_cap": 64,
            "stage3_init3_count": 64,
            "elapsed_seconds": 7200.0,
        },
        {
            "preset_id": run_mod.CANDIDATE_PRESET_ID,
            "best_match_ratio": 0.429,
            "best_match_delta_vs_retained": 0.006,
            "entry_target_before_cap": 144,
            "stage3_init3_count": 144,
            "elapsed_seconds": 7200.0,
        },
    ]

    recommendation = extract_mod.build_recommendation(
        rows,
        missing_job_count=0,
        expected_job_count=2,
    )

    assert recommendation["recommendation"] == "promote"
    assert recommendation["best_preset_id"] == run_mod.CANDIDATE_PRESET_ID
    assert recommendation["candidate_minus_control"] == pytest.approx(0.006)
