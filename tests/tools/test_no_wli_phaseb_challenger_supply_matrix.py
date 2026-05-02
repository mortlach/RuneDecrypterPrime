from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli import fixture_matrix_api as fixture_api
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_phaseb_challenger_supply_matrix_v1 as extract_mod,
    run_phaseb_challenger_supply_matrix_v1 as run_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixed_instance_io import (
    load_fixed_cipher_panel_spec,
    load_fixed_instance_spec_map,
)


pytestmark = pytest.mark.tier_a


def test_supply_matrix_driver_materializes_expected_primary_trio_slice() -> None:
    config = run_mod.build_matrix_mainflow_config()
    repo_root = Path.cwd()
    panel = load_fixed_cipher_panel_spec(repo_root / run_mod.PRIMARY_TRIO_PANEL_PATH)
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

    assert str(panel.panel_id) == "p9_c3_solver_panel_primary_trio_search7002_7004_v1"
    assert tuple(int(x) for x in panel.search_seeds) == (7002, 7004)
    assert tuple(str(x) for x in config.stage3_tuning_preset_ids) == (
        "phaseb_supply_selected24_saved16_stage3only_v1",
        "phaseb_supply_selected24_saved64_stage3only_v1",
        "phaseb_supply_selected48_saved96_stage3only_v1",
    )
    assert len(jobs) == 18
    assert int(presets["phaseb_supply_selected24_saved16_stage3only_v1"].force_stage3_phaseb_top_n) == 24
    assert int(presets["phaseb_supply_selected24_saved16_stage3only_v1"].force_stage3_topk_limit) == 16
    assert int(presets["phaseb_supply_selected24_saved64_stage3only_v1"].force_stage3_topk_limit) == 64
    assert int(presets["phaseb_supply_selected48_saved96_stage3only_v1"].force_stage3_phaseb_top_n) == 48
    assert int(presets["phaseb_supply_selected48_saved96_stage3only_v1"].force_stage3_topk_limit) == 96
    assert bool(presets["phaseb_supply_selected48_saved96_stage3only_v1"].force_stage35_enabled) is False


def test_supply_metrics_detect_spare_phaseb_topk_challengers() -> None:
    best_instance = {
        "stage3_diagnostics": {
            "phaseB_downstream_selected_count": 32,
            "phaseB_selected_unique_end_hash": 30,
            "phaseB_topk_saved_count": 12,
            "phaseB_topk_saved_unique_end_hash": 9,
            "phaseC_start_summaries": [
                {
                    "candidate_hash": "anchor_hash",
                    "source": "stage3_best_phaseA",
                    "became_global_best": 0,
                },
                {
                    "candidate_hash": "selected_a",
                    "source": "phaseB_topk",
                    "became_global_best": 1,
                },
                {
                    "candidate_hash": "selected_b",
                    "source": "phaseA_selected",
                    "became_global_best": 0,
                },
            ],
            "phaseC_candidate_pool_rows": [
                {
                    "candidate_hash": "selected_a",
                    "source": "phaseB_topk",
                    "selected_by_phasec_start": 1,
                },
                {
                    "candidate_hash": "challenger_1",
                    "source": "phaseB_topk",
                    "selected_by_phasec_start": 0,
                },
                {
                    "candidate_hash": "selected_b",
                    "source": "phaseB_topk",
                    "selected_by_phasec_start": 0,
                },
                {
                    "candidate_hash": "phasea_row",
                    "source": "phaseA_selected",
                    "selected_by_phasec_start": 0,
                },
            ],
            "phaseC_final_winner_source": "phaseB_topk",
            "phaseC_final_winner_lane": "challenger",
        }
    }

    metrics = extract_mod._supply_metrics(best_instance)

    assert int(metrics["phaseb_downstream_selected_count"]) == 32
    assert int(metrics["phaseb_topk_saved_count"]) == 12
    assert int(metrics["non_anchor_selected_phaseb_topk_count"]) == 1
    assert int(metrics["non_selected_phaseb_topk_challenger_count"]) == 2
    assert int(metrics["non_selected_phaseb_topk_unique_challenger_count"]) == 2
    assert int(metrics["non_selected_phaseb_topk_duplicate_of_selected_count"]) == 1
    assert list(metrics["non_selected_phaseb_topk_challenger_hashes"]) == [
        "challenger_1",
        "selected_b",
    ]
    assert int(metrics["non_selected_phaseb_topk_true_spare_unique_challenger_count"]) == 1
    assert list(metrics["non_selected_phaseb_topk_true_spare_hashes"]) == [
        "challenger_1",
    ]
    assert int(metrics["quota_engageable"]) == 1
    assert int(metrics["replacement_engageable"]) == 1
    assert str(metrics["phasec_winner_candidate_hash"]) == "selected_a"
    assert str(metrics["phasec_winner_source"]) == "phaseB_topk"
    assert str(metrics["phasec_winner_lane"]) == "challenger"


def test_supply_metrics_do_not_treat_selected_duplicates_as_true_spares() -> None:
    best_instance = {
        "stage3_diagnostics": {
            "phaseC_start_summaries": [
                {"candidate_hash": "anchor_hash", "source": "stage3_best_phaseA"},
                {"candidate_hash": "selected_a", "source": "phaseB_topk"},
                {"candidate_hash": "selected_b", "source": "phaseA_selected"},
            ],
            "phaseC_candidate_pool_rows": [
                {
                    "candidate_hash": "selected_a",
                    "source": "phaseB_topk",
                    "selected_by_phasec_start": 0,
                },
                {
                    "candidate_hash": "selected_b",
                    "source": "phaseB_topk",
                    "selected_by_phasec_start": 0,
                },
            ],
        }
    }

    metrics = extract_mod._supply_metrics(best_instance)

    assert int(metrics["non_selected_phaseb_topk_unique_challenger_count"]) == 2
    assert int(metrics["non_selected_phaseb_topk_duplicate_of_selected_count"]) == 2
    assert int(metrics["non_selected_phaseb_topk_true_spare_unique_challenger_count"]) == 0
    assert list(metrics["non_selected_phaseb_topk_true_spare_hashes"]) == []
    assert int(metrics["quota_engageable"]) == 0
    assert int(metrics["replacement_engageable"]) == 0


def test_run_manifest_window_filters_out_of_study_runs(tmp_path: Path) -> None:
    run_dir = tmp_path / "fake_run"
    run_dir.mkdir()

    window_start = datetime(2026, 4, 19, 1, 0, 0, tzinfo=timezone.utc)
    window_end = datetime(2026, 4, 19, 3, 0, 0, tzinfo=timezone.utc)

    inside_manifest = {"completed_utc": "2026-04-19T02:00:00+00:00"}
    outside_manifest = {"completed_utc": "2026-04-19T05:00:00+00:00"}

    assert (
        extract_mod._run_manifest_within_window(
            inside_manifest,
            run_dir=run_dir,
            window_start=window_start,
            window_end=window_end,
        )
        is True
    )
    assert (
        extract_mod._run_manifest_within_window(
            outside_manifest,
            run_dir=run_dir,
            window_start=window_start,
            window_end=window_end,
        )
        is False
    )


def test_runtime_window_ignores_inactive_stub_run_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_state_path = tmp_path / "output" / "stub_run_state.json"
    run_state_path.parent.mkdir(parents=True, exist_ok=True)
    run_state_path.write_text(
        """
{
  "started_utc": "2026-04-19T15:37:52.201832+00:00",
  "updated_utc": "2026-04-19T15:37:52.201832+00:00",
  "completed_jobs": 0,
  "remaining_jobs": 18,
  "stopped_early": 0
}
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(extract_mod, "REPO_ROOT", tmp_path)

    window = extract_mod._runtime_window(
        {
            "run_state_path": "output/stub_run_state.json",
            "job_count": 18,
        }
    )

    assert window == (None, None)


def test_supply_recommendation_refines_when_spares_are_narrow() -> None:
    recommendation = extract_mod.build_recommendation(
        [
            {
                "preset_id": "phaseb_supply_selected24_saved64_stage3only_v1",
                "config_label": "selected24_saved64",
                "cases_with_spare_challengers_ge_1": 1,
                "cases_with_spare_challengers_ge_2": 0,
                "cases_with_quota_engageable": 1,
                "mean_non_selected_phaseb_topk_true_spare_unique_challenger_delta": 0.5,
                "mean_phaseb_topk_saved_unique_end_hash_delta": 1.0,
                "mean_best_match_delta_vs_retained": 0.0,
            }
        ],
        missing_job_count=0,
        expected_job_count=1,
    )

    assert recommendation["recommendation"] == "refine"


def test_supply_recommendation_is_incomplete_when_jobs_are_missing() -> None:
    recommendation = extract_mod.build_recommendation(
        [
            {
                "preset_id": "phaseb_supply_selected24_saved16_stage3only_v1",
                "config_label": "selected24_saved16",
                "cases_with_spare_challengers_ge_1": 0,
                "cases_with_spare_challengers_ge_2": 0,
                "cases_with_quota_engageable": 0,
                "mean_non_selected_phaseb_topk_true_spare_unique_challenger_delta": 0.0,
                "mean_phaseb_topk_saved_unique_end_hash_delta": 0.0,
                "mean_best_match_delta_vs_retained": -0.1,
            }
        ],
        missing_job_count=17,
        expected_job_count=18,
    )

    assert recommendation["recommendation"] == "incomplete"
