from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.run_manifest_setup import (
    build_commit_iteration_callback,
)
from tools.benchmarks.periodic_sub_trans.no_wli.commit_bridge_state import (
    extract_commit_bridge_state,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_progress import (
    commit_iteration_with_checkpoint,
    init_progress_state,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_pipeline_execution import (
    _resolve_commit_bridge_state,
)
from tools.benchmarks.periodic_sub_trans.no_wli.resume_handoff_artifacts import (
    write_resume_handoff_artifacts,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runner_bridges import (
    commit_iteration_outputs_bridge,
)


pytestmark = pytest.mark.tier_a


def _artifact_payload() -> dict[str, object]:
    return {
        "tier": "fixture_fixture_001_p9_c3_l1000",
        "profile_id": "profile",
        "mode": "adaptive_fixture_v1",
        "oracle_mode": "off",
        "oracle_consulted_in_decisions": False,
        "direction": "ltr",
        "order": "col_then_sub",
        "alphabet_size": 3,
        "text_id": 0,
        "key_seed": 211,
        "offset_hint": 0,
        "offset_used": 0,
        "period": 2,
        "columns": 1,
        "length": 6,
        "status": "unsolved",
        "stop_reason": "done",
        "outcome_code": "unsolved",
        "best_stage": "stage3_full_refine",
        "best_match_ratio": 0.5,
        "best_score": 3.0,
        "oracle_scores": {},
        "score_minus_oracle": {},
        "solve_threshold": 0.9,
        "ciphertext_idx": [0, 0, 0, 0, 0, 0],
        "target_plaintext_idx": [0, 1, 2, 0, 1, 2],
        "final_best_key_idx": [0, 1, 2, 0, 1, 2, 0],
        "final_best_plaintext_idx": [0, 1, 2, 0, 1, 1],
        "stage2_topk": [
            {
                "rank": 1,
                "score_stage2": 3.0,
                "score_judge": 3.1,
                "match_ratio": 0.5,
                "key_idx": [0, 1, 2, 0, 1, 2, 0],
                "plaintext_idx": [0, 1, 2, 0, 1, 1],
            },
            {
                "rank": 2,
                "score_stage2": 2.6,
                "score_judge": 2.7,
                "match_ratio": 0.4,
                "key_idx": [1, 0, 2, 0, 1, 2, 1],
                "plaintext_idx": [1, 0, 2, 0, 1, 2],
            },
        ],
        "stage2_topk_has_best_match": 1,
        "stage2_diagnostics": {},
        "stage3_topk": [
            {
                "rank": 1,
                "source": "phaseB_topk",
                "end_hash": "h1",
                "key_idx": [0, 1, 2, 0, 1, 2, 0],
                "plaintext_idx": [0, 1, 2, 0, 1, 1],
                "score_judge": 4.0,
            }
        ],
        "stage3_diagnostics": {
            "phaseC_final_winner_lane": "anchor",
            "phaseC_final_winner_source": "stage3_best_phaseB",
            "phaseC_start_summaries": [
                {
                    "start_idx": 1,
                    "lane": "anchor",
                    "source": "stage3_best_phaseB",
                    "source_rank": 1,
                    "candidate_hash": "h1",
                    "init_match": 0.5,
                    "final_match": 0.5,
                    "init_score": 4.0,
                    "final_score": 4.0,
                    "rescue_applied": 0,
                }
            ],
        },
        "stage35_archive": [],
        "stage35_seed_rows": [],
        "oracle_scores": {"stage3": 0.0},
    }


def _run_config() -> dict[str, object]:
    return {
        "stage1": {"scout": {"promote_top": 2}},
        "stage2": {"scorer": {}, "judge_pool": {"entry_band_by_stage3_judge": False}},
        "stage3": {
            "init_keys": 4,
            "dynamic_bands": [],
            "solver": {},
            "scorer": {"span_hamming_char_pct_min": 0.0},
            "search_scorer": {},
            "judge_scorer": {},
            "period_scaling": {"init_keys_cap": 0},
            "c1_focus": {},
            "word_ngram_report": {"decision_influence": False},
            "span_basin_judge": {
                "k": 0,
                "require_span_active": True,
                "dedupe_by_end_hash": True,
                "tie_eps": 0.0,
                "tie_max_seeds": 0,
            },
            "two_phase": {
                "enabled": True,
                "continue_after_solve": False,
                "phase_a": {"steps": 8},
                "phase_b": {"steps": 16},
                "phase_b_top_n": 2,
                "gate_delta_floor": 0.0,
                "gate_end_gain_floor": 0.0,
                "phase_c": {
                    "enabled": True,
                    "cfg": {"steps": 4},
                    "start_keys": 2,
                    "seed_offset": 0,
                    "word_ngram_tiebreak": False,
                },
                "stage35": {"enabled": False, "cfg": {}},
            },
        },
        "threshold": 0.9,
        "oracle_decision_paths_enabled": False,
        "artifacts": {
            "stage3_topk_enabled": True,
            "stage3_topk": 5,
            "resume_handoffs_enabled": True,
        },
        "scan_controls": {
            "tier_time_cap_seconds": 0.0,
            "stage3_gate_low_match": 0.0,
            "stage3_gate_high_match": 1.0,
        },
        "stage3_phase_experiments": {
            "phaseA": "resume_test",
            "phaseB": "resume_test",
        },
    }


def test_write_resume_handoff_artifacts_saves_stage2_and_stage35_sources(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    final_dir = run_dir / "final_instances"
    final_dir.mkdir(parents=True)
    artifact_path = final_dir / "fixture_fixture_001_p9_c3_l1000__text0__seed211.json"
    run_config_path = run_dir / "run_config.json"
    run_config_path.write_text(json.dumps(_run_config()), encoding="utf-8")

    def _write_json(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    manifest = write_resume_handoff_artifacts(
        run_dir=run_dir,
        root=tmp_path,
        artifact_path=artifact_path,
        artifact_payload=_artifact_payload(),
        run_config_path=run_config_path,
        write_json_fn=_write_json,
    )

    bundle_dir = run_dir / "resume_handoffs" / artifact_path.stem
    assert int(manifest["stage2_to_stage3"]["saved"]) == 1
    assert int(manifest["stage3_to_stage35"]["saved"]) == 1
    assert (bundle_dir / "manifest.json").exists()
    assert (bundle_dir / "stage2_resume.json").exists()
    assert (bundle_dir / "stage3_prep.json").exists()
    assert (bundle_dir / "stage35_seed_archive.json").exists()

    stage2_resume = json.loads((bundle_dir / "stage2_resume.json").read_text(encoding="utf-8"))
    stage35_seed_archive = json.loads(
        (bundle_dir / "stage35_seed_archive.json").read_text(encoding="utf-8")
    )
    assert int(stage2_resume["stage2_promoted_from_topk_count"]) == 2
    assert int(len(stage35_seed_archive["seed_rows"])) >= 1


def test_write_resume_handoff_artifacts_prefers_live_stage3_handoff_bundle(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    final_dir = run_dir / "final_instances"
    final_dir.mkdir(parents=True)
    artifact_path = final_dir / "fixture_fixture_001_p9_c3_l1000__text0__seed211.json"
    run_config_path = run_dir / "run_config.json"
    run_config_path.write_text(json.dumps(_run_config()), encoding="utf-8")

    def _write_json(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    live_stage2_resume = dict(
        best2_key=[9, 9, 9],
        best2_pt=[1, 2, 3],
        best2_score=7.5,
        best2_match=0.75,
        best2_preview="LIVE",
        stage2_promoted=[
            {
                "key": [9, 9, 9],
                "plaintext": [1, 2, 3],
                "score": 7.5,
                "match": 0.75,
            }
        ],
        stage2_entry_score=7.5,
        stage2_entry_score_judge=7.7,
        stage2_topk_row_count=3,
        stage2_promote_top_cfg=5,
        stage2_promoted_from_topk_count=1,
    )
    live_stage3_prep = dict(
        init3=[[9, 9, 9]],
        promoted_keys=[[9, 9, 9]],
        stage3_promoted_keys_count=1,
        stage3_phaseB_top_n=3,
    )

    manifest = write_resume_handoff_artifacts(
        run_dir=run_dir,
        root=tmp_path,
        artifact_path=artifact_path,
        artifact_payload=_artifact_payload(),
        run_config_path=run_config_path,
        write_json_fn=_write_json,
        live_stage2_resume=live_stage2_resume,
        live_stage3_prep=live_stage3_prep,
    )

    bundle_dir = run_dir / "resume_handoffs" / artifact_path.stem
    stage2_resume = json.loads((bundle_dir / "stage2_resume.json").read_text(encoding="utf-8"))
    stage3_prep = json.loads((bundle_dir / "stage3_prep.json").read_text(encoding="utf-8"))

    assert int(manifest["stage2_to_stage3"]["saved"]) == 1
    assert str(manifest["stage2_to_stage3"]["source"]) == "live_stage3_pipeline"
    assert stage2_resume["best2_key"] == [9, 9, 9]
    assert float(stage2_resume["best2_score"]) == pytest.approx(7.5)
    assert stage3_prep["init3"] == [[9, 9, 9]]


def test_commit_callback_threads_live_handoff_state_into_resume_bundle(
    tmp_path: Path,
) -> None:
    root = tmp_path
    run_dir = root / "run"
    final_dir = run_dir / "final_instances"
    final_dir.mkdir(parents=True)
    hist_path = run_dir / "history.csv"
    audit_csv = run_dir / "audit.csv"
    audit_jsonl = run_dir / "audit.jsonl"
    run_config_path = run_dir / "run_config.json"
    run_config_path.write_text(json.dumps(_run_config()), encoding="utf-8")

    def _write_json(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    def _append_csv_row(path: Path, row: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    runner_state = dict(
        base=type("_Base", (), {"_format_seconds": staticmethod(lambda seconds: f"{seconds:.1f}s")})(),
        write_json=_write_json,
        _build_summary=lambda tiers, instances: {
            "total_instances": int(len(list(instances))),
            "tiers": [str(getattr(t, "name", "")) for t in list(tiers)],
        },
        write_pipeline_snapshot_files=lambda **kwargs: None,
        _append_csv_row=_append_csv_row,
        _append_iteration_audit_row=lambda **kwargs: str(kwargs.get("prev_chain_hash", "")),
        _hash_payload=lambda payload: "hash",
        _sha256_file=lambda path: "sha256",
        _format_seconds=lambda seconds: f"{float(seconds):.1f}s",
        SAVE_RESUME_HANDOFFS=True,
    )
    live_bridge_state = dict(
        stage2_resume_live=dict(
            best2_key=[9, 9, 9],
            best2_pt=[1, 2, 3],
            best2_score=7.5,
            best2_match=0.75,
            best2_preview="LIVE",
            stage2_promoted=[
                {
                    "key": [9, 9, 9],
                    "plaintext": [1, 2, 3],
                    "score": 7.5,
                    "match": 0.75,
                }
            ],
            stage2_entry_score=7.5,
            stage2_entry_score_judge=7.7,
            stage2_topk_row_count=3,
            stage2_promote_top_cfg=5,
            stage2_promoted_from_topk_count=1,
        ),
        stage3_prep_live=dict(
            init3=[[9, 9, 9]],
            promoted_keys=[[9, 9, 9]],
            stage3_promoted_keys_count=1,
            stage3_phaseB_top_n=3,
        ),
    )

    commit_iteration_outputs_fn = lambda **kwargs: commit_iteration_outputs_bridge(
        state=_resolve_commit_bridge_state(
            runner_state=runner_state,
            bridge_state=kwargs.pop("bridge_state", None),
        ),
        **kwargs,
    )
    progress = init_progress_state(total=1, t0_all=0.0, audit_prev_chain_hash="")
    run_manifest: dict[str, object] = {}
    commit_callback = build_commit_iteration_callback(
        progress=progress,
        run_manifest=run_manifest,
        get_oracle_consulted_in_decisions_fn=lambda: False,
        commit_iteration_with_checkpoint_fn=commit_iteration_with_checkpoint,
        commit_iteration_outputs_fn=commit_iteration_outputs_fn,
        update_run_manifest_progress_fn=lambda **kwargs: kwargs["run_manifest"].update(
            done_units=int(kwargs["done_units"]),
            history_rows_written=int(kwargs["history_rows_written"]),
        ),
        run_dir=run_dir,
        final_dir=final_dir,
        root=root,
        hist_path=hist_path,
        tiers=[],
        instances=[],
        stages=[],
        heartbeat_seconds=9999.0,
        audit_enabled=False,
        audit_csv=audit_csv,
        audit_jsonl=audit_jsonl,
        run_manifest_path=run_dir / "run_manifest.json",
        write_json_fn=_write_json,
    )

    artifact_payload = _artifact_payload()
    inst_row = {
        "tier": str(artifact_payload["tier"]),
        "text_id": int(artifact_payload["text_id"]),
        "key_seed": int(artifact_payload["key_seed"]),
        "period": int(artifact_payload["period"]),
        "columns": int(artifact_payload["columns"]),
        "length": int(artifact_payload["length"]),
        "status": str(artifact_payload["status"]),
        "outcome_code": str(artifact_payload["outcome_code"]),
        "solve_threshold": float(artifact_payload["solve_threshold"]),
        "best_match_ratio": float(artifact_payload["best_match_ratio"]),
        "best_stage": str(artifact_payload["best_stage"]),
        "stage1_sub_key_match": 0.0,
        "stage2_match_ratio": 0.5,
        "stage3_match_ratio": 0.5,
        "total_seconds": 1.0,
        "total_evals": 10,
        "stop_reason": str(artifact_payload["stop_reason"]),
        "preview_best_latin": "LIVE",
    }

    commit_callback(
        inst_row=inst_row,
        artifact_payload=artifact_payload,
        status_key="unsolved",
        bridge_state=live_bridge_state,
    )

    bundle_dir = (
        run_dir
        / "resume_handoffs"
        / "fixture_fixture_001_p9_c3_l1000__text0__seed211"
    )
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    stage2_resume = json.loads((bundle_dir / "stage2_resume.json").read_text(encoding="utf-8"))

    assert str(manifest["stage2_to_stage3"]["source"]) == "live_stage3_pipeline"
    assert stage2_resume["best2_key"] == [9, 9, 9]
    assert float(stage2_resume["best2_score"]) == pytest.approx(7.5)


def test_resolve_commit_bridge_state_overlays_sparse_iteration_state() -> None:
    runner_state = {
        "write_json": lambda path, payload: None,
        "_build_summary": lambda tiers, instances: {},
        "write_pipeline_snapshot_files": lambda **kwargs: None,
        "_append_csv_row": lambda path, row: None,
        "_append_iteration_audit_row": lambda **kwargs: "",
        "_hash_payload": lambda payload: "hash",
        "_sha256_file": lambda path: "sha256",
        "_format_seconds": lambda seconds: f"{float(seconds):.1f}s",
        "SAVE_RESUME_HANDOFFS": True,
        "base": object(),
        "keep": 1,
    }
    bridge_state = {
        "stage2_resume_live": {"best2_key": [9, 9, 9]},
        "stage3_prep_live": {"init3": [[9, 9, 9]]},
    }

    merged = _resolve_commit_bridge_state(
        runner_state=runner_state,
        bridge_state=bridge_state,
    )

    assert merged["write_json"] is runner_state["write_json"]
    assert merged["base"] is runner_state["base"]
    assert merged["stage2_resume_live"] == {"best2_key": [9, 9, 9]}
    assert merged["stage3_prep_live"] == {"init3": [[9, 9, 9]]}
    assert merged["keep"] == 1


def test_resolve_commit_bridge_state_rejects_unexpected_override_keys() -> None:
    with pytest.raises(KeyError, match="unexpected commit bridge_state keys"):
        _resolve_commit_bridge_state(
            runner_state={
                "write_json": object(),
                "_build_summary": lambda tiers, instances: {},
                "write_pipeline_snapshot_files": lambda **kwargs: None,
                "_append_csv_row": lambda path, row: None,
                "_append_iteration_audit_row": lambda **kwargs: "",
                "_hash_payload": lambda payload: "hash",
                "_sha256_file": lambda path: "sha256",
                "_format_seconds": lambda seconds: f"{float(seconds):.1f}s",
                "SAVE_RESUME_HANDOFFS": True,
            },
            bridge_state={"write_json": "shadow"},
        )


def test_resolve_commit_bridge_state_rejects_missing_runner_services() -> None:
    with pytest.raises(KeyError, match="missing commit runner services"):
        _resolve_commit_bridge_state(
            runner_state={
                "write_json": lambda path, payload: None,
            },
            bridge_state=None,
        )


def test_resolve_commit_bridge_state_rejects_non_callable_runner_services() -> None:
    runner_state = {
        "write_json": lambda path, payload: None,
        "_build_summary": lambda tiers, instances: {},
        "write_pipeline_snapshot_files": lambda **kwargs: None,
        "_append_csv_row": lambda path, row: None,
        "_append_iteration_audit_row": lambda **kwargs: "",
        "_hash_payload": lambda payload: "hash",
        "_sha256_file": "not-callable",
        "_format_seconds": lambda seconds: f"{float(seconds):.1f}s",
        "SAVE_RESUME_HANDOFFS": True,
    }

    with pytest.raises(TypeError, match="non-callable commit runner services"):
        _resolve_commit_bridge_state(
            runner_state=runner_state,
            bridge_state=None,
        )


def test_resolve_commit_bridge_state_rejects_missing_runner_values() -> None:
    runner_state = {
        "write_json": lambda path, payload: None,
        "_build_summary": lambda tiers, instances: {},
        "write_pipeline_snapshot_files": lambda **kwargs: None,
        "_append_csv_row": lambda path, row: None,
        "_append_iteration_audit_row": lambda **kwargs: "",
        "_hash_payload": lambda payload: "hash",
        "_sha256_file": lambda path: "sha256",
        "_format_seconds": lambda seconds: f"{float(seconds):.1f}s",
    }

    with pytest.raises(KeyError, match="missing commit runner values"):
        _resolve_commit_bridge_state(
            runner_state=runner_state,
            bridge_state=None,
        )


def test_extract_commit_bridge_state_keeps_only_live_handoff_payloads() -> None:
    bridge_state = extract_commit_bridge_state(
        iteration_state={
            "stage2_resume_live": {"best2_key": [9, 9, 9]},
            "stage3_prep_live": {"init3": [[9, 9, 9]]},
            "write_json": object(),
            "base": object(),
            "best3_match": 0.5,
        }
    )

    assert bridge_state == {
        "stage2_resume_live": {"best2_key": [9, 9, 9]},
        "stage3_prep_live": {"init3": [[9, 9, 9]]},
    }


def test_commit_iteration_outputs_bridge_uses_runner_format_seconds_service(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def _fake_commit_iteration_outputs_external(**kwargs):
        captured["formatted_short"] = kwargs["format_seconds_fn"](12.5)
        captured["formatted_long"] = kwargs["format_seconds_fn"](3723.4)
        return {
            "done": int(kwargs["done"]) + 1,
            "last_hb": float(kwargs["last_hb"]),
            "best_global": dict(kwargs["best_global"]),
            "history_rows_written": int(kwargs["history_rows_written"]),
            "audit_rows_written": int(kwargs["audit_rows_written"]),
            "audit_prev_chain_hash": str(kwargs["audit_prev_chain_hash"]),
        }

    monkeypatch.setattr(
        "tools.benchmarks.periodic_sub_trans.no_wli.runner_bridges._commit_iteration_outputs_external",
        _fake_commit_iteration_outputs_external,
    )

    out = commit_iteration_outputs_bridge(
        state={
            "write_json": lambda path, payload: None,
            "_build_summary": lambda tiers, instances: {},
            "write_pipeline_snapshot_files": lambda **kwargs: None,
            "_append_csv_row": lambda path, row: None,
            "_append_iteration_audit_row": lambda **kwargs: "chain",
            "_hash_payload": lambda payload: "hash",
            "_sha256_file": lambda path: "sha256",
            "_format_seconds": lambda seconds: f"FMT:{float(seconds):.1f}",
            "SAVE_RESUME_HANDOFFS": False,
        },
        run_dir=tmp_path / "run",
        final_dir=tmp_path / "run" / "final_instances",
        root=tmp_path,
        hist_path=tmp_path / "run" / "history.csv",
        tiers=[],
        instances=[],
        stages=[],
        inst_row={
            "tier": "fixture_fixture_001_p9_c3_l1000",
            "text_id": 0,
            "key_seed": 211,
            "period": 9,
            "columns": 3,
            "length": 1000,
            "status": "unsolved",
            "outcome_code": "unsolved",
            "solve_threshold": 0.9,
            "best_match_ratio": 0.5,
            "best_stage": "stage3_full_refine",
            "stage1_sub_key_match": 0.0,
            "stage2_match_ratio": 0.5,
            "stage3_match_ratio": 0.5,
            "total_seconds": 12.5,
            "total_evals": 10,
            "stop_reason": "done",
            "preview_best_latin": "",
        },
        artifact_payload=_artifact_payload(),
        done=0,
        total=1,
        t0_all=0.0,
        last_hb=0.0,
        heartbeat_seconds=9999.0,
        best_global={
            "match": float("-inf"),
            "tier": "",
            "text_id": -1,
            "key_seed": -1,
            "stage": "",
            "preview": "",
        },
        history_rows_written=0,
        audit_rows_written=0,
        audit_enabled=False,
        audit_csv=tmp_path / "run" / "audit.csv",
        audit_jsonl=tmp_path / "run" / "audit.jsonl",
        audit_prev_chain_hash="",
    )

    assert captured["formatted_short"] == "FMT:12.5"
    assert captured["formatted_long"] == "FMT:3723.4"
    assert int(out["done"]) == 1
