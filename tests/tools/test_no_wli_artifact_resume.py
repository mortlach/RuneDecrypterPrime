from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli import (
    artifact_resume as resume_mod,
    replay_phasec_rescue_sweep as phasec_replay_mod,
)


def _toy_artifact() -> dict[str, object]:
    return {
        "tier": "fixture_fixture_001_p9_c3_l1000",
        "text_id": 0,
        "key_seed": 511,
        "period": 2,
        "columns": 1,
        "alphabet_size": 3,
        "length": 6,
        "order": "col_then_sub",
        "direction": "ltr",
        "ciphertext_idx": [0, 0, 0, 0, 0, 0],
        "target_plaintext_idx": [0, 1, 2, 0, 1, 2],
        "final_best_key_idx": [0, 1, 2, 0, 1, 2, 0],
        "final_best_plaintext_idx": [0, 1, 2, 1, 1, 2],
        "best_score": 4.0,
        "best_match_ratio": 4.0 / 6.0,
        "oracle_scores": {"stage3": 0.0},
        "stage2_topk": [
            {
                "rank": 2,
                "score_stage2": 2.5,
                "score_judge": 2.6,
                "match_ratio": 0.40,
                "key_idx": [1, 0, 2, 0, 1, 2, 1],
                "plaintext_idx": [1, 0, 2, 0, 1, 2],
            },
            {
                "rank": 1,
                "score_stage2": 3.0,
                "score_judge": 3.1,
                "match_ratio": 0.50,
                "key_idx": [0, 1, 2, 0, 1, 2, 0],
                "plaintext_idx": [0, 1, 2, 0, 1, 1],
            },
            {
                "rank": 3,
                "score_stage2": 2.0,
                "score_judge": 2.2,
                "match_ratio": 0.35,
                "key_idx": [2, 1, 0, 0, 1, 2, 2],
                "plaintext_idx": [2, 1, 0, 0, 1, 2],
            },
        ],
        "stage3_topk": [
            {
                "rank": 1,
                "source": "phaseB_topk",
                "end_hash": "h1",
                "key_idx": [0, 1, 2, 0, 1, 2, 0],
                "plaintext_idx": [0, 1, 2, 1, 1, 2],
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
                    "init_match": 4.0 / 6.0,
                    "final_match": 4.0 / 6.0,
                    "init_score": 4.0,
                    "final_score": 4.0,
                    "rescue_applied": 0,
                }
            ],
        },
    }


def _toy_run_config() -> dict[str, object]:
    return {
        "threshold": 0.9,
        "stall_delta": 0.0,
        "stall_stage_limit": 1,
        "oracle_decision_paths_enabled": False,
        "oracle_assist_selection_effective": False,
        "stage3_can_skip": False,
        "stage1": {
            "scout": {
                "promote_top": 2,
            }
        },
        "stage2": {
            "scorer": {},
            "judge_pool": {
                "entry_band_by_stage3_judge": False,
            },
        },
        "stage3": {
            "init_keys": 4,
            "dynamic_bands": [],
            "solver": {},
            "scorer": {
                "span_hamming_char_pct_min": 0.0,
            },
            "search_scorer": {},
            "judge_scorer": {},
            "period_scaling": {
                "init_keys_cap": 0,
            },
            "c1_focus": {},
            "word_ngram_report": {
                "decision_influence": False,
            },
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
            },
            "stage35": {
                "enabled": False,
                "cfg": dict(resume_mod.DEFAULT_STAGE35_SOLVER_CFG),
            },
        },
        "artifacts": {
            "stage3_topk_enabled": True,
            "stage3_topk": 8,
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


def _toy_case(tmp_path: Path) -> phasec_replay_mod.ArtifactCase:
    return phasec_replay_mod.ArtifactCase(
        artifact_path=tmp_path / "run" / "final_instances" / "toy.json",
        run_dir=tmp_path / "run",
        run_config_path=tmp_path / "run" / "run_config.json",
        artifact=_toy_artifact(),
        run_config=_toy_run_config(),
    )


def test_reconstruct_stage2_resume_inputs_uses_saved_stage2_topk() -> None:
    out = resume_mod.reconstruct_stage2_resume_inputs(
        _toy_artifact(),
        _toy_run_config(),
    )

    assert out.stage2_topk_row_count == 3
    assert out.stage2_promote_top_cfg == 2
    assert out.stage2_promoted_from_topk_count == 2
    assert out.best2_key == [0, 1, 2, 0, 1, 2, 0]
    assert out.best2_pt == [0, 1, 2, 0, 1, 1]
    assert out.best2_score == 3.0
    assert out.stage2_entry_score_judge == 3.1


def test_prepare_stage3_resume_inputs_builds_nonempty_init3(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_prepare_stage3_refine_inputs(**kwargs):
        captured.update(kwargs)
        return {"init3": [[9, 8, 7]], "seed_count": len(kwargs["stage2_promoted"])}

    monkeypatch.setattr(
        resume_mod,
        "prepare_stage3_refine_inputs",
        _fake_prepare_stage3_refine_inputs,
    )

    out = resume_mod.prepare_stage3_resume_inputs(
        _toy_artifact(),
        _toy_run_config(),
    )

    assert out["stage3_prep"]["init3"] == [[9, 8, 7]]
    assert out["stage3_prep"]["seed_count"] == 2
    assert captured["stage3_phaseb_top_n"] == 2
    assert len(captured["stage2_promoted"]) == 2
    assert captured["best2_key"] == [0, 1, 2, 0, 1, 2, 0]


def test_output_root_is_repo_anchored() -> None:
    expected = (
        resume_mod.REPO_ROOT
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
        / "artifact_resume"
    )
    assert resume_mod.OUTPUT_ROOT == expected
    assert resume_mod.OUTPUT_ROOT.is_absolute()


def test_run_stage35_resume_from_artifact_reuses_saved_late_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    case = _toy_case(tmp_path)
    captured: dict[str, object] = {}

    monkeypatch.setattr(resume_mod.phasec_replay_mod, "_build_cipher", lambda artifact: "cipher")
    monkeypatch.setattr(
        resume_mod.phasec_replay_mod,
        "_build_stage3_scorer_runtime",
        lambda artifact, run_config, scorer_key: f"scorer:{scorer_key}",
    )

    def _fake_run_stage35_live_followup(**kwargs):
        captured.update(kwargs)
        return {
            "best_plaintext_idx": [0, 1, 2, 0, 1, 2],
            "best_score": 6.0,
            "archive_rows": [
                {
                    "key_idx": [0, 1, 2, 0, 1, 2, 0],
                    "plaintext_idx": [0, 1, 2, 0, 1, 2],
                    "score": 6.0,
                }
            ],
            "seed_rows_scored": [{"seed_source": "final_best"}],
        }

    monkeypatch.setattr(
        resume_mod,
        "run_stage35_live_followup",
        _fake_run_stage35_live_followup,
    )

    out = resume_mod.run_stage35_resume_from_artifact(
        case,
        stage35_cfg_override={"beam_width": 9},
    )

    assert out["mode"] == "stage3_to_stage35"
    assert out["resume_best_match_ratio"] == 1.0
    assert out["resume_best_score"] == 6.0
    assert out["stage35_cfg"]["beam_width"] == 9
    assert captured["baseline_key"] == [0, 1, 2, 0, 1, 2, 0]
    assert len(captured["stage3_topk_rows"]) == 1
    assert len(captured["phasec_start_summaries"]) == 1


def test_run_stage3_resume_from_artifact_calls_stage3_flow_with_reconstructed_handoff(
    monkeypatch,
    tmp_path: Path,
) -> None:
    case = _toy_case(tmp_path)
    prepare_captured: dict[str, object] = {}
    flow_captured: dict[str, object] = {}

    def _fake_prepare_stage3_refine_inputs(**kwargs):
        prepare_captured.update(kwargs)
        return {"init3": [[1, 2, 3]], "resume_marker": "ok"}

    monkeypatch.setattr(
        resume_mod,
        "prepare_stage3_refine_inputs",
        _fake_prepare_stage3_refine_inputs,
    )
    monkeypatch.setattr(resume_mod.phasec_replay_mod, "_build_cipher", lambda artifact: "cipher")
    monkeypatch.setattr(
        resume_mod.phasec_replay_mod,
        "_build_stage3_scorer_runtime",
        lambda artifact, run_config, scorer_key: f"scorer:{scorer_key}",
    )
    monkeypatch.setattr(
        resume_mod.phasec_replay_mod,
        "_build_stage3_word_ngram_report_runtime",
        lambda artifact, run_config: "word_ngram",
    )
    monkeypatch.setattr(
        resume_mod,
        "_build_stage3_runtime_call_context",
        lambda artifact, run_config, output_dir: "stage3_ctx",
    )

    def _fake_run_stage3_iteration_flow(**kwargs):
        flow_captured.update(kwargs)
        return {
            "stop_reason": "complete",
            "ev3": 17,
            "best3_match": 0.5,
            "best3_score": 3.5,
            "best3_key": [0, 1, 2, 0, 1, 2, 0],
            "pt3": np.asarray([0, 1, 2, 0, 1, 1], dtype=np.uint8),
            "stage35_selected": 0,
        }

    monkeypatch.setattr(
        resume_mod.stage3_flow_mod,
        "run_stage3_iteration_flow",
        _fake_run_stage3_iteration_flow,
    )

    out = resume_mod.run_stage3_resume_from_artifact(
        case,
        output_dir=tmp_path / "resume_output",
        enable_stage35=False,
    )

    state = dict(flow_captured["state"])
    assert flow_captured["stage3_runtime_call_ctx"] == "stage3_ctx"
    assert state["best2_key"] == [0, 1, 2, 0, 1, 2, 0]
    assert len(state["stage2_promoted"]) == 2
    assert state["STAGE35_ENABLED"] is False
    assert prepare_captured["stage3_phaseb_top_n"] == 2
    assert len(prepare_captured["stage2_promoted"]) == 2
    assert out["mode"] == "stage2_to_stage3"
    assert out["resume_best_stage"] == "stage3_full_refine"
    assert out["resume_best_match_ratio"] == 0.5
    assert out["resume_best_score"] == 3.5


def test_run_stage3_resume_from_artifact_applies_run_config_override(
    monkeypatch,
    tmp_path: Path,
) -> None:
    case = _toy_case(tmp_path)
    prepare_captured: dict[str, object] = {}
    runtime_cfg_captured: dict[str, object] = {}

    def _fake_prepare_stage3_refine_inputs(**kwargs):
        prepare_captured.update(kwargs)
        return {"init3": [[1, 2, 3]], "resume_marker": "ok"}

    monkeypatch.setattr(
        resume_mod,
        "prepare_stage3_refine_inputs",
        _fake_prepare_stage3_refine_inputs,
    )
    monkeypatch.setattr(resume_mod.phasec_replay_mod, "_build_cipher", lambda artifact: "cipher")
    monkeypatch.setattr(
        resume_mod.phasec_replay_mod,
        "_build_stage3_scorer_runtime",
        lambda artifact, run_config, scorer_key: f"scorer:{scorer_key}",
    )
    monkeypatch.setattr(
        resume_mod.phasec_replay_mod,
        "_build_stage3_word_ngram_report_runtime",
        lambda artifact, run_config: "word_ngram",
    )

    def _fake_build_stage3_runtime_call_context(artifact, run_config, output_dir):
        runtime_cfg_captured.update(run_config)
        return "stage3_ctx"

    monkeypatch.setattr(
        resume_mod,
        "_build_stage3_runtime_call_context",
        _fake_build_stage3_runtime_call_context,
    )
    monkeypatch.setattr(
        resume_mod.stage3_flow_mod,
        "run_stage3_iteration_flow",
        lambda **kwargs: {
            "stop_reason": "complete",
            "ev3": 1,
            "best3_match": 0.4,
            "best3_score": 2.0,
            "best3_key": [0, 1, 2, 0, 1, 2, 0],
            "pt3": np.asarray([0, 1, 2, 0, 1, 1], dtype=np.uint8),
            "stage35_selected": 0,
        },
    )

    out = resume_mod.run_stage3_resume_from_artifact(
        case,
        output_dir=tmp_path / "resume_output",
        run_config_override={
            "stage3": {
                "init_keys": 9,
                "two_phase": {
                    "phase_b_top_n": 5,
                    "phase_c": {
                        "word_ngram_tiebreak": True,
                    },
                },
            }
        },
        enable_stage35=False,
    )

    assert prepare_captured["stage3_initial_keys"] == 9
    assert prepare_captured["stage3_phaseb_top_n"] == 5
    assert dict(runtime_cfg_captured["stage3"])["init_keys"] == 9
    assert (
        dict(dict(runtime_cfg_captured["stage3"])["two_phase"])["phase_c"][
            "word_ngram_tiebreak"
        ]
        is True
    )
    assert out["run_config_override"] == {
        "stage3": {
            "init_keys": 9,
            "two_phase": {
                "phase_b_top_n": 5,
                "phase_c": {
                    "word_ngram_tiebreak": True,
                },
            },
        }
    }


def test_run_stage3_resume_from_artifact_resolves_repo_relative_scorer_cfgs_before_stage3_flow(
    monkeypatch,
    tmp_path: Path,
) -> None:
    case = _toy_case(tmp_path)
    fake_repo_root = tmp_path
    expected_assets = fake_repo_root / "assets" / "scoring" / "span_hamming_nose_assets_v1"
    flow_captured: dict[str, object] = {}

    monkeypatch.setattr(resume_mod, "REPO_ROOT", fake_repo_root)
    monkeypatch.setattr(resume_mod.phasec_replay_mod, "REPO_ROOT", fake_repo_root)
    monkeypatch.setattr(
        resume_mod,
        "prepare_stage3_refine_inputs",
        lambda **kwargs: {"init3": [[1, 2, 3]], "resume_marker": "ok"},
    )
    monkeypatch.setattr(resume_mod.phasec_replay_mod, "_build_cipher", lambda artifact: "cipher")
    monkeypatch.setattr(
        resume_mod.phasec_replay_mod,
        "_build_stage3_scorer_runtime",
        lambda artifact, run_config, scorer_key: f"scorer:{scorer_key}",
    )
    monkeypatch.setattr(
        resume_mod.phasec_replay_mod,
        "_build_stage3_word_ngram_report_runtime",
        lambda artifact, run_config: "word_ngram",
    )
    monkeypatch.setattr(
        resume_mod,
        "_build_stage3_runtime_call_context",
        lambda artifact, run_config, output_dir: "stage3_ctx",
    )

    def _fake_run_stage3_iteration_flow(**kwargs):
        flow_captured.update(dict(kwargs["state"]))
        return {
            "stop_reason": "complete",
            "ev3": 1,
            "best3_match": 0.4,
            "best3_score": 2.0,
            "best3_key": [0, 1, 2, 0, 1, 2, 0],
            "pt3": np.asarray([0, 1, 2, 0, 1, 1], dtype=np.uint8),
            "stage35_selected": 0,
        }

    monkeypatch.setattr(
        resume_mod.stage3_flow_mod,
        "run_stage3_iteration_flow",
        _fake_run_stage3_iteration_flow,
    )

    resume_mod.run_stage3_resume_from_artifact(
        case,
        output_dir=tmp_path / "resume_output",
        run_config_override={
            "stage3": {
                "scorer": {
                    "span_hamming_assets_dir": "assets/scoring/span_hamming_nose_assets_v1",
                },
                "search_scorer": {
                    "span_hamming_assets_dir": "assets/scoring/span_hamming_nose_assets_v1",
                },
            }
        },
        enable_stage35=False,
    )

    assert str(flow_captured["scorer_full"]["span_hamming_assets_dir"]) == str(expected_assets)
    assert (
        str(flow_captured["scorer_stage3_phaseA"]["span_hamming_assets_dir"])
        == str(expected_assets)
    )
    assert (
        str(flow_captured["scorer_stage3_phaseB"]["span_hamming_assets_dir"])
        == str(expected_assets)
    )


def test_run_stage35_resume_from_artifact_applies_run_config_override(
    monkeypatch,
    tmp_path: Path,
) -> None:
    case = _toy_case(tmp_path)
    captured_cfg: dict[str, object] = {}

    monkeypatch.setattr(resume_mod.phasec_replay_mod, "_build_cipher", lambda artifact: "cipher")

    def _fake_build_stage3_scorer_runtime(artifact, run_config, scorer_key):
        captured_cfg[scorer_key] = run_config
        return f"scorer:{scorer_key}"

    monkeypatch.setattr(
        resume_mod.phasec_replay_mod,
        "_build_stage3_scorer_runtime",
        _fake_build_stage3_scorer_runtime,
    )
    monkeypatch.setattr(
        resume_mod,
        "run_stage35_live_followup",
        lambda **kwargs: {
            "best_plaintext_idx": [0, 1, 2, 0, 1, 2],
            "best_score": 5.0,
            "archive_rows": [],
            "seed_rows_scored": [],
        },
    )

    out = resume_mod.run_stage35_resume_from_artifact(
        case,
        run_config_override={
            "stage3": {
                "stage35": {
                    "cfg": {
                        "beam_width": 7,
                    }
                }
            }
        },
    )

    assert dict(dict(captured_cfg["scorer"])["stage3"])["stage35"]["cfg"]["beam_width"] == 7
    assert out["stage35_cfg"]["beam_width"] == 7
    assert out["run_config_override"] == {
        "stage3": {
            "stage35": {
                "cfg": {
                    "beam_width": 7,
                }
            }
        }
    }


def test_run_stage3_resume_from_artifact_prefers_saved_live_bundle(
    monkeypatch,
    tmp_path: Path,
) -> None:
    case = _toy_case(tmp_path)
    bundle_dir = case.run_dir / "resume_handoffs" / case.artifact_path.stem
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (case.run_dir / "run_config.json").parent.mkdir(parents=True, exist_ok=True)

    saved_stage2_resume = {
        "best2_key": [9, 9, 9],
        "best2_pt": [1, 2, 3],
        "best2_score": 7.5,
        "best2_match": 0.75,
        "best2_preview": "saved_live",
        "stage2_promoted": [
            {
                "key": [9, 9, 9],
                "plaintext": [1, 2, 3],
                "score": 7.5,
                "match": 0.75,
            }
        ],
        "stage2_entry_score": 7.5,
        "stage2_entry_score_judge": 7.6,
        "stage2_topk_row_count": 3,
        "stage2_promote_top_cfg": 5,
        "stage2_promoted_from_topk_count": 1,
    }
    saved_stage3_prep = {"init3": [[9, 9, 9]], "resume_marker": "saved_live_bundle"}
    (bundle_dir / "stage2_resume.json").write_text(
        json.dumps(saved_stage2_resume),
        encoding="utf-8",
    )
    (bundle_dir / "stage3_prep.json").write_text(
        json.dumps(saved_stage3_prep),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        resume_mod,
        "prepare_stage3_refine_inputs",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not rebuild prep")),
    )
    monkeypatch.setattr(resume_mod.phasec_replay_mod, "_build_cipher", lambda artifact: "cipher")
    monkeypatch.setattr(
        resume_mod.phasec_replay_mod,
        "_build_stage3_scorer_runtime",
        lambda artifact, run_config, scorer_key: f"scorer:{scorer_key}",
    )
    monkeypatch.setattr(
        resume_mod.phasec_replay_mod,
        "_build_stage3_word_ngram_report_runtime",
        lambda artifact, run_config: "word_ngram",
    )
    monkeypatch.setattr(
        resume_mod,
        "_build_stage3_runtime_call_context",
        lambda artifact, run_config, output_dir: "stage3_ctx",
    )

    state_captured: dict[str, object] = {}

    def _fake_run_stage3_iteration_flow(**kwargs):
        state_captured.update(dict(kwargs["state"]))
        return {
            "stop_reason": "complete",
            "ev3": 1,
            "best3_match": 0.4,
            "best3_score": 2.0,
            "best3_key": [0, 1, 2, 0, 1, 2, 0],
            "pt3": np.asarray([0, 1, 2, 0, 1, 1], dtype=np.uint8),
            "stage35_selected": 0,
        }

    monkeypatch.setattr(
        resume_mod.stage3_flow_mod,
        "run_stage3_iteration_flow",
        _fake_run_stage3_iteration_flow,
    )

    out = resume_mod.run_stage3_resume_from_artifact(
        case,
        output_dir=tmp_path / "resume_output",
        enable_stage35=False,
    )

    assert state_captured["best2_key"] == [9, 9, 9]
    assert len(list(state_captured["stage2_promoted"])) == 1
    assert out["resume_source"] == "saved_live_bundle"
    assert str(out["bundle_dir_relpath"]).replace("\\", "/").endswith(
        "resume_handoffs/toy"
    )
    assert out["stage3_prep"]["resume_marker"] == "saved_live_bundle"


def test_build_stage3_scorer_runtime_resolves_repo_relative_span_assets_dir(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    fake_repo_root = tmp_path
    expected_assets = fake_repo_root / "assets" / "scoring" / "span_hamming_nose_assets_v1"

    monkeypatch.setattr(phasec_replay_mod, "REPO_ROOT", fake_repo_root)

    def _fake_build_scorer(cipher_cfg, scoring_cfg):
        captured["cipher_cfg"] = cipher_cfg
        captured["scoring_cfg"] = scoring_cfg
        return "scorer_runtime"

    monkeypatch.setattr(phasec_replay_mod, "build_scorer", _fake_build_scorer)

    artifact = {
        "period": 9,
        "columns": 3,
        "alphabet_size": 29,
        "order": "col_then_sub",
        "direction": "ltr",
    }
    run_config = {
        "stage3": {
            "scorer": {
                "objective": "pct.logp.win10",
                "impl": "torch",
                "include_char": True,
                "use_word_breaks": False,
                "char_weights": {"4": 1.0},
                "wli_weights": {},
                "span_hamming_enabled": True,
                "span_hamming_mode": "calibrated",
                "span_hamming_assets_dir": "assets/scoring/span_hamming_nose_assets_v1",
            }
        }
    }

    out = phasec_replay_mod._build_stage3_scorer_runtime(
        artifact=artifact,
        run_config=run_config,
        scorer_key="scorer",
    )

    assert out == "scorer_runtime"
    assert str(captured["scoring_cfg"].span_hamming_assets_dir) == str(expected_assets)


def test_build_stage3_word_ngram_report_runtime_resolves_repo_relative_paths(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    fake_repo_root = tmp_path
    expected_assets = fake_repo_root / "assets" / "scoring" / "span_hamming_nose_assets_v1"
    expected_sqlite = fake_repo_root / "output" / "word_ngrams" / "asset.sqlite"

    monkeypatch.setattr(phasec_replay_mod, "REPO_ROOT", fake_repo_root)

    def _fake_build_scorer(cipher_cfg, scoring_cfg):
        captured["cipher_cfg"] = cipher_cfg
        captured["scoring_cfg"] = scoring_cfg
        return "word_ngram_runtime"

    monkeypatch.setattr(phasec_replay_mod, "build_scorer", _fake_build_scorer)

    artifact = {
        "period": 9,
        "columns": 3,
        "alphabet_size": 29,
        "order": "col_then_sub",
        "direction": "ltr",
    }
    run_config = {
        "stage3": {
            "judge_scorer": {
                "objective": "pct.logp.win10",
                "impl": "torch",
                "include_char": True,
                "use_word_breaks": False,
                "char_weights": {"4": 1.0},
                "wli_weights": {},
                "span_hamming_enabled": True,
                "span_hamming_mode": "calibrated",
                "span_hamming_assets_dir": "assets/scoring/span_hamming_nose_assets_v1",
            },
            "word_ngram_report": {
                "enabled": True,
                "sqlite_path": "output/word_ngrams/asset.sqlite",
                "alpha": 0.4,
                "miss_logp": -20.0,
                "min_positions": 6,
                "prefix_total_thresholds": [1, 10, 100],
            },
        }
    }

    out = phasec_replay_mod._build_stage3_word_ngram_report_runtime(
        artifact=artifact,
        run_config=run_config,
    )

    assert out == "word_ngram_runtime"
    assert str(captured["scoring_cfg"].span_hamming_assets_dir) == str(expected_assets)
    assert str(captured["scoring_cfg"].word_ngram_judge_sqlite_path) == str(expected_sqlite)
