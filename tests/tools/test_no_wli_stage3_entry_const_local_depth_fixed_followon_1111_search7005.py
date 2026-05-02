from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli import fixture_matrix_api as fixture_api
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    run_stage3_entry_const_local_depth_fixed_followon_1111_search7005_v1 as run_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixed_instance_io import (
    load_fixed_cipher_panel_spec,
    load_fixed_instance_spec_map,
)


pytestmark = pytest.mark.tier_a


def test_fixed_followon_driver_materializes_two_jobs() -> None:
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

    assert str(panel.panel_id) == "p9_c3_solver_panel_1111_search7005_v1"
    assert tuple(int(x) for x in panel.search_seeds) == (7005,)
    assert tuple(int(x) for x in config.text_offsets) == (5,)
    assert tuple(str(x) for x in config.stage3_tuning_preset_ids) == (
        run_mod.CONTROL_PRESET_ID,
        run_mod.CANDIDATE_PRESET_ID,
    )
    assert len(jobs) == 2
    assert float(config.max_wallclock_seconds) == pytest.approx(6.0 * 60.0 * 60.0)
    assert bool(config.stop_on_error) is True
    assert (
        presets[run_mod.CANDIDATE_PRESET_ID].force_stage3_entry_allocation_policy
        == "constant_local_depth"
    )
    assert int(presets[run_mod.CANDIDATE_PRESET_ID].force_stage3_init_keys_cap) == 288
