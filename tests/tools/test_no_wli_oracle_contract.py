from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli import runner as no_wli_runner
from tools.benchmarks.periodic_sub_trans.no_wli.run_progress import checkpoint_manifest
from tools.benchmarks.periodic_sub_trans.no_wli.run_manifest import (
    build_initial_run_manifest,
    update_run_manifest_progress,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_band_policy import (
    resolve_stage3_gap_and_band,
)


pytestmark = pytest.mark.tier_a


def test_run_config_separates_oracle_enabled_and_consulted() -> None:
    cfg = no_wli_runner._build_run_config_external(
        state=no_wli_runner.__dict__,
        mode_canonical="adaptive_focus_v1",
        mode_raw="adaptive_focus_v1",
        mode_intent="focus",
        stage3_can_skip=False,
        scoring_experiment_meta={"profile": "off", "enabled": False},
        root=no_wli_runner._repo_root(),
        direction=no_wli_runner.Direction.LTR,
        autoskip_effective=False,
        proven_known=0,
        oracle_mode="benchmark_only",
        oracle_decision_paths_enabled=True,
        oracle_assist_selection_effective=False,
        is_adaptive_focus_mode_fn=no_wli_runner._is_adaptive_focus_mode,
        scorer_cfg_for_output_fn=no_wli_runner._scorer_cfg_for_output,
        stage3_search_cfg_fn=no_wli_runner._stage3_char4_avg_fulltext_search_cfg,
        scoring_meta_for_output_fn=no_wli_runner._scoring_meta_for_output,
        build_no_wli_order_dispatch_payload_fn=no_wli_runner._build_no_wli_order_dispatch_payload,
    )
    assert cfg["oracle_mode"] == "benchmark_only"
    assert cfg["oracle_decision_paths_enabled"] is True
    assert cfg["oracle_consulted_in_decisions"] is False


def test_run_manifest_preserves_oracle_enabled_when_consulted_flips() -> None:
    manifest = build_initial_run_manifest(
        run_dir=Path("output/tools/benchmarks/periodic_sub_trans/no_wli/example"),
        profile="pipeline_no_wli_v1",
        mode="adaptive_focus_v1",
        oracle_mode="benchmark_only",
        oracle_decision_paths_enabled=True,
        oracle_consulted_in_decisions=False,
        oracle_assist_selection_requested=True,
        oracle_assist_selection_effective=False,
        direction="ltr",
        order="col_then_sub",
        python_version="3.12.0",
        platform_name="test-platform",
        git_short="abc1234",
        git_commit="abc1234567890",
        git_dirty=False,
        scoring_experiment={"profile": "off"},
        non_scoring_lock_hash="n",
        scoring_lock_hash="s",
        run_config_hash="r",
        span_assets_dir="assets/scoring/span_hamming_nose_assets_v1",
        span_combined_calibration_hash="",
        span_ecdf_audit_hash="",
        run_config_rel_path="output/tools/benchmarks/periodic_sub_trans/no_wli/example/run_config.json",
        history_log_rel_path="tools/benchmarks/solve_proof/proven_solve_pipeline_no_wli_log.csv",
        final_instances_rel_path="output/tools/benchmarks/periodic_sub_trans/no_wli/example/final_instances",
        audit_csv_rel_path="output/tools/benchmarks/periodic_sub_trans/no_wli/example/iteration_audit_chain.csv",
        audit_jsonl_rel_path="output/tools/benchmarks/periodic_sub_trans/no_wli/example/iteration_audit_chain.jsonl",
        audit_enabled=True,
        audit_chain_seed="0" * 64,
        total_units=10,
    )
    assert manifest["oracle_decision_paths_enabled"] is True
    assert manifest["oracle_consulted_in_decisions"] is False

    update_run_manifest_progress(
        run_manifest=manifest,
        done_units=1,
        total_units=10,
        solved=0,
        stalled=0,
        unsolved=1,
        skipped_proven=0,
        history_rows_written=1,
        audit_rows_written=1,
        audit_last_chain_hash="1" * 64,
        oracle_consulted_in_decisions=True,
    )
    assert manifest["oracle_decision_paths_enabled"] is True
    assert manifest["oracle_consulted_in_decisions"] is True


def test_checkpoint_manifest_does_not_imply_consulted_from_enabled() -> None:
    recorded: dict[str, bool] = {}

    def _capture(**kwargs):
        recorded["oracle_consulted_in_decisions"] = bool(
            kwargs["oracle_consulted_in_decisions"]
        )
        return kwargs

    progress = dict(
        done=0,
        total=10,
        status_counts=dict(solved=0, stalled=0, unsolved=0, skipped_proven=0),
        history_rows_written=0,
        audit_rows_written=0,
        audit_prev_chain_hash="0" * 64,
    )
    run_manifest = dict(oracle_decision_paths_enabled=True, oracle_consulted_in_decisions=False)

    checkpoint_manifest(
        progress=progress,
        status_key="unsolved",
        run_manifest=run_manifest,
        oracle_consulted_in_decisions=False,
        update_run_manifest_progress_fn=_capture,
    )
    assert recorded["oracle_consulted_in_decisions"] is False


def test_checkpoint_manifest_rejects_unknown_status_key() -> None:
    progress = dict(
        done=0,
        total=10,
        status_counts=dict(solved=0, stalled=0, unsolved=0, skipped_proven=0),
        history_rows_written=0,
        audit_rows_written=0,
        audit_prev_chain_hash="0" * 64,
    )

    with pytest.raises(KeyError, match="unknown status_key: invalid_status"):
        checkpoint_manifest(
            progress=progress,
            status_key="invalid_status",
            run_manifest={},
            oracle_consulted_in_decisions=False,
            update_run_manifest_progress_fn=lambda **kwargs: kwargs,
        )


def test_stage3_band_policy_does_not_use_oracle_when_decision_paths_disabled() -> None:
    dynamic_bands = [
        {"name": "near", "max_gap": 0.02},
        {"name": "mid", "max_gap": 0.10},
        {"name": "far", "max_gap": 1e9},
    ]
    gap, band, used = resolve_stage3_gap_and_band(
        dynamic_bands=dynamic_bands,
        stage2_gate_score=0.80,
        oracle_stage3_score=0.90,
        oracle_decision_paths_enabled=False,
    )
    assert used is False
    assert str(band.get("name")) == "mid"
    assert gap != gap  # NaN


def test_stage3_band_policy_uses_oracle_only_when_decision_paths_enabled() -> None:
    dynamic_bands = [
        {"name": "near", "max_gap": 0.02},
        {"name": "mid", "max_gap": 0.10},
        {"name": "far", "max_gap": 1e9},
    ]
    gap, band, used = resolve_stage3_gap_and_band(
        dynamic_bands=dynamic_bands,
        stage2_gate_score=0.80,
        oracle_stage3_score=0.90,
        oracle_decision_paths_enabled=True,
    )
    assert used is True
    assert gap == pytest.approx(0.10)
    assert str(band.get("name")) == "mid"
