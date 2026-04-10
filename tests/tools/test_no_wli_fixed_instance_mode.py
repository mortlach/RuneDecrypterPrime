from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.types import Device, Direction
from tools.benchmarks.periodic_sub_trans.common import (
    bench_solve_periodic_columnar_kaeding as base,
)
from tools.benchmarks.periodic_sub_trans.no_wli import iteration_runtime as runtime_mod
from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as artifact_resume_mod
from tools.benchmarks.periodic_sub_trans.no_wli import run_pipeline_execution as pipeline_exec_mod
from tools.benchmarks.periodic_sub_trans.no_wli.export_fixed_instance_fixtures import (
    OUTPUT_DIR,
    SOURCE_ARTIFACT_REL_PATHS,
    _build_true_key_idx,
    build_fixed_instance_spec_from_artifact,
)
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_matrix_flow import (
    IterationMatrixConfig,
    IterationMatrixFns,
    run_iteration_matrix,
)
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_identity import (
    build_proven_solved_key,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_summary import (
    load_proven_solved_index,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_completion import (
    finalize_run_outputs,
)
from tools.benchmarks.periodic_sub_trans.no_wli.resume_handoff_artifacts import (
    write_resume_handoff_artifacts,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage_iteration_commit import (
    commit_iteration_outputs,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage_iteration_payload import (
    build_iteration_payloads,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_config_builder import build_run_config
from tools.benchmarks.periodic_sub_trans.no_wli.run_mode_apply import apply_run_mode_overrides
from tools.benchmarks.periodic_sub_trans.no_wli.runner_state_defaults import (
    initialize_runtime_state,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixed_instance_io import (
    load_fixed_cipher_panel_spec,
    load_fixed_instance_spec,
    load_fixed_instance_specs,
    load_fixed_instance_spec_map,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixed_instance_models import (
    FIXED_CIPHER_INSTANCE_SCHEMA_VERSION,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
PANEL_PATH = REPO_ROOT / "tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1.json"
CANARY_PANEL_PATH = REPO_ROOT / "tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_canary_v1.json"
FIXTURE_DIR = REPO_ROOT / "tools/benchmarks/periodic_sub_trans/no_wli/fixed_instances"


@dataclass(frozen=True)
class _Tier:
    name: str
    period: int
    columns: int
    length: int


def _build_cipher(*, period: int, columns: int, alphabet_size: int, direction: str, order: str) -> PeriodicColumnarCipher:
    cfg = CipherConfig(
        name="periodic_columnar",
        ciphertext=[],
        period=int(period),
        columns=int(columns),
        alphabet_size=int(alphabet_size),
        key_length=int(period) * int(alphabet_size) + int(columns),
        order=str(order),
        encoding_dir=Direction(str(direction)),
        wli_data=[],
        device=Device.CPU,
    )
    return PeriodicColumnarCipher(cfg)


def _make_runtime_state() -> dict[str, object]:
    state: dict[str, object] = {
        "SCORER_IMPL": "numpy",
        "ORACLE_ASSIST_SELECTION": False,
    }
    initialize_runtime_state(
        state=state,
        default_scorer_stage1={},
        default_scorer_stage2={},
        default_scorer_full={},
        default_solver_stage1={},
        default_solver_stage2={},
        default_solver_stage3={},
        default_stage3_entry_allocation_policy="legacy_fixed_budget",
        default_stage3_entry_mutations_per_promoted=4,
        default_stage3_phaseb_family_preservation_policy="off",
        default_stage3_phaseb_family_view_id="space_map_v1",
        default_stage3_phaseb_family_reserved_slots=0,
        default_stage3_phasec_start_policy="phaseb_topk",
        default_stage35_baseline_selector="legacy",
        default_stage3_dynamic_bands=[],
        default_stage3_phasea_cfg={},
        default_stage3_phaseb_cfg={},
        default_tiers=[("tier_1", 9, 3, 1000)],
        tier_cls=_Tier,
    )
    state.update(
        {
            "PROFILE": "test_profile",
            "ORDER": "col_then_sub",
            "ALPHABET_SIZE": 29,
            "SCORER_STAGE1_LABEL": "s1",
            "SCORER_STAGE2_LABEL": "s2",
            "SCORER_STAGE3_LABEL": "s3",
            "SCAN_TIER_TIME_CAP_SECONDS": 3600.0,
            "SCAN_STAGE2_CONTINUE_TO_GATE": False,
            "SCAN_STAGE2_CONTINUE_CAP_SECONDS": 0.0,
            "SCAN_STAGE3_GATE_LOW_MATCH": 0.0,
            "SCAN_STAGE3_GATE_HIGH_MATCH": 1.0,
            "SCAN_STAGE3_MIN_STAGE2_MATCH": 0.0,
            "STAGE2_PROMOTE_BY_STAGE3_JUDGE": False,
            "STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE": False,
            "STAGE2_JUDGE_POLICY": "search_only",
            "WORD_NGRAM_REPORT_ENABLED": False,
            "WORD_NGRAM_REPORT_SQLITE_PATH": "",
            "WORD_NGRAM_REPORT_ALPHA": 0.5,
            "WORD_NGRAM_REPORT_MISS_LOGP": -12.0,
            "WORD_NGRAM_REPORT_MIN_POSITIONS": 3,
            "WORD_NGRAM_REPORT_PREFIX_TOTAL_THRESHOLDS": [5, 10],
            "WORD_NGRAM_REPORT_DECISION_INFLUENCE": False,
            "STAGE3_SPAN_AUX_ROLE": "off",
            "STAGE3_SPAN_AUX_SCOPE": "none",
            "STAGE3_SPAN_AUX_PROFILE": "off",
            "STAGE3_SPAN_AUX_BUDGET_MS": 0.0,
            "STAGE3_SPAN_AUX_TWO_PASS": False,
            "STAGE3_SPAN_AUX_FULL_TOP_M": 0,
            "SPAN_DECISION_ROLE_ENABLED": False,
            "SPAN_REPS_PER_BASIN": 1,
            "SPAN_SELECTION_TOP_K": 1,
            "SPAN_P90_CALL_MS": None,
        }
    )
    return state


def _build_runtime_kwargs(
    *,
    pt_idx: np.ndarray,
    key_seed: int,
    direction: Direction = Direction.LTR,
    period: int = 9,
    columns: int = 3,
    alphabet_size: int = 29,
    order: str = "col_then_sub",
    instance_input_mode: str = "generated",
    fixed_instance_spec: object | None = None,
    search_seed: int | None = None,
) -> dict[str, object]:
    return dict(
        tier_period=int(period),
        tier_columns=int(columns),
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        key_seed=int(key_seed),
        alphabet_size=int(alphabet_size),
        order=str(order),
        direction=direction,
        scorer_stage1_base=dict(
            objective="pct.logp.win10",
            include_char=True,
            use_word_breaks=False,
            char_weights={4: 1.0},
            wli_weights={},
            impl="numpy",
        ),
        scorer_stage2_base=dict(
            objective="avg.logp.win20",
            include_char=True,
            use_word_breaks=False,
            char_weights={4: 1.0},
            wli_weights={},
            impl="numpy",
        ),
        scorer_impl="numpy",
        pipeline_run_mode="fixed_seed",
        stage3_two_phase_enabled=False,
        scoring_experiment_profile="off",
        span_assets_dir=REPO_ROOT / "assets/scoring/span_hamming_nose_assets_v1",
        stage2_judge_policy_value="search_only",
        stage2_exact_max_columns=columns,
        stage2_exact_two_pass=False,
        stage2_pass1_primary_char_weights={4: 1.0},
        stage2_pass1_fallback_char_weights={},
        canonical_run_mode_fn=lambda mode: str(mode or "fixed_seed"),
        is_adaptive_focus_mode_fn=lambda _mode: False,
        stage3_search_cfg_fn=lambda *, direction: dict(
            objective="avg.logp.win20",
            include_char=True,
            use_word_breaks=False,
            char_weights={4: 1.0},
            wli_weights={},
            impl="numpy",
            encoding_dir=direction,
        ),
        build_stage3_experiment_cfg_fn=lambda **kwargs: dict(
            objective="avg.logp.win20",
            include_char=True,
            use_word_breaks=False,
            char_weights={4: 1.0},
            wli_weights={},
            impl="numpy",
            encoding_dir=kwargs["direction"],
        ),
        build_word_ngram_report_cfg_fn=lambda **_kwargs: None,
        guard_no_ecdf_usage_fn=lambda **_kwargs: None,
        instance_input_mode=str(instance_input_mode),
        fixed_instance_spec=fixed_instance_spec,
        search_seed=(int(search_seed) if search_seed is not None else None),
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _resume_run_config() -> dict[str, object]:
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


def _fixed_mode_matrix_config() -> IterationMatrixConfig:
    return IterationMatrixConfig(
        stage1_label="A_char1",
        stage2_label="M_char12",
        stage3_label="B_char34",
        stage3_continue_after_solve=False,
        stage3_phaseb_top_n=8,
        stage3_phaseb_gate_delta_floor=0.01,
        stage3_phaseb_gate_end_gain_floor=0.01,
        stage3_c1_focus_enabled=False,
        stage3_span_char_pct_min_override=None,
        scoring_experiment_c_char_pct_min=0.35,
        oracle_stage3_floor_guard_eps=1e-4,
        stage3_two_phase_enabled=False,
        stage3_phasea_cfg_default={},
        stage3_phaseb_cfg_default={},
        solver_stage3_default_cfg={},
        stage3_span_basin_judge_k=8,
        tier_heartbeat_seconds=30.0,
        solve_match_threshold=0.95,
        stall_delta=1e-6,
        stall_stage_limit=2,
        scan_stage3_gate_low_match=0.15,
        scan_stage3_gate_high_match=0.22,
        oracle_mode="off",
        oracle_decision_paths_enabled=False,
        oracle_assist_selection_effective=False,
        stage3_span_aux_role="off",
        stage3_span_aux_scope="basin_rep",
        stage3_span_aux_profile="lite",
        stage3_span_aux_budget_ms=0.0,
        stage3_span_aux_two_pass=False,
        stage3_span_aux_full_top_m=0,
        span_decision_role_enabled=False,
        span_reps_per_basin=1,
        span_selection_top_k=0,
        span_p90_call_ms=None,
        stage3_phasec_start_policy="source_order",
        stage35_enabled=False,
        stage35_baseline_selector="legacy",
        stage35_cfg={},
        require_batch_scoring=True,
    )


def _build_fixed_mode_matrix_fns(
    *,
    observed_pre_states: list[dict[str, object]],
) -> IterationMatrixFns:
    def _run_pre(**kwargs):
        state = kwargs["state"]
        observed_pre_states.append(
            {
                "instance_input_mode": str(state.get("instance_input_mode", "")),
                "instance_fixture_id": str(state.get("instance_fixture_id", "")),
                "instance_source_key_seed": int(state.get("instance_source_key_seed", 0)),
                "search_seed": int(state.get("search_seed", 0)),
                "key_seed": int(state["key_seed"]),
                "pt_idx": tuple(int(x) for x in np.asarray(state["pt_idx"], dtype=np.uint8).tolist()),
                "fixed_instance_fixture_id": str(
                    getattr(state.get("fixed_instance_spec"), "instance_fixture_id", "")
                ),
            }
        )
        return {"continue_iteration": True}

    return IterationMatrixFns(
        slice_word_aligned_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("fixed mode must not slice plaintext on the fly")
        ),
        get_oracle_consulted_in_decisions_fn=lambda: False,
        handle_autoskip_proven_iteration_fn=lambda **_: None,
        run_iteration_pre_stage3_fn=_run_pre,
        run_stage3_iteration_flow_fn=lambda **_: {},
        finalize_iteration_post_stage3_fn=lambda **_: None,
        build_iteration_payloads_fn=lambda **_: ({}, {}),
        derive_outcome_code_fn=lambda **_: "ok",
        commit_iteration_with_checkpoint_fn=lambda **_: None,
        build_iteration_runtime_fn=lambda **_: {},
        evaluate_oracle_precheck_fn=lambda **_: {},
        handle_oracle_floor_guard_if_triggered_fn=lambda **_: False,
        run_stage12_pipeline_fn=lambda **_: {},
        scorer_objective_summary_fn=lambda *_: "",
        oracle_score_for_stage_fn=lambda **_: 0.0,
        weights_text_fn=lambda *_: "",
        mark_oracle_decision_use_fn=lambda: None,
        print_stage_preview_fn=lambda **_: None,
        build_oracle_floor_guard_result_fn=lambda **_: {},
        run_stage1_substitution_fn=lambda **_: {},
        run_stage2_search_fn=lambda **_: {},
        finalize_stage2_archive_fn=lambda **_: {},
        evaluate_stage3_entry_policy_fn=lambda **_: {},
        prepare_stage3_refine_inputs_fn=lambda **_: {},
        summarize_stage3_span_fn=lambda **_: {},
        fmt_finite_float_fn=lambda *_: "",
        build_stage2_diagnostics_fn=lambda **_: {},
        build_stage3_diagnostics_fn=lambda **_: {},
        finalize_iteration_and_commit_fn=lambda **_: {},
        safe_preview_latin_fn=lambda *_: "",
        stage_engine_trace_emit_fn=lambda **_: None,
    )


def test_export_fixed_instance_config_targets_first_panel_seeds() -> None:
    seeds = [int(Path(path).stem.split("__seed")[-1]) for path in SOURCE_ARTIFACT_REL_PATHS]
    assert seeds == [611, 1111, 1411, 1511]
    assert OUTPUT_DIR == "tools/benchmarks/periodic_sub_trans/no_wli/fixed_instances"


def test_initialize_runtime_state_sets_fixed_instance_defaults() -> None:
    state = _make_runtime_state()
    assert state["INSTANCE_INPUT_MODE"] == "generated"
    assert state["INSTANCE_FIXTURE_IDS"] == []
    assert state["SEARCH_SEEDS"] == []


def test_apply_run_mode_overrides_accepts_fixed_instance_fields() -> None:
    state = _make_runtime_state()
    apply_run_mode_overrides(
        state=state,
        overrides={
            "INSTANCE_INPUT_MODE": "fixed_ciphertext",
            "INSTANCE_FIXTURE_IDS": [
                "fixture_001__p9_c3_l1000__text0__seed611",
                "fixture_001__p9_c3_l1000__text0__seed1111",
            ],
            "SEARCH_SEEDS": [7001, 7002],
            "TEXT_OFFSETS": [5],
            "KEY_SEEDS": [611],
        },
        build_tier_fn=_Tier,
    )
    assert state["INSTANCE_INPUT_MODE"] == "fixed_ciphertext"
    assert state["INSTANCE_FIXTURE_IDS"] == [
        "fixture_001__p9_c3_l1000__text0__seed611",
        "fixture_001__p9_c3_l1000__text0__seed1111",
    ]
    assert state["SEARCH_SEEDS"] == [7001, 7002]
    assert state["TEXT_OFFSETS"] == [5]
    assert state["KEY_SEEDS"] == [611]


def test_build_run_config_serializes_generated_mode_honestly() -> None:
    state = _make_runtime_state()
    run_config = build_run_config(
        state=state,
        mode_canonical="candidate",
        mode_raw="candidate",
        mode_intent="test",
        stage3_can_skip=False,
        scoring_experiment_meta={"profile": "off"},
        root=REPO_ROOT,
        direction=Direction.LTR,
        autoskip_effective=True,
        proven_known=0,
        oracle_mode="benchmark_only",
        oracle_decision_paths_enabled=False,
        oracle_assist_selection_effective=False,
        is_adaptive_focus_mode_fn=lambda _mode: False,
        scorer_cfg_for_output_fn=lambda cfg, **_: dict(cfg),
        stage3_search_cfg_fn=lambda **_: {"objective": "avg.logp.win20"},
        scoring_meta_for_output_fn=lambda meta, **_: dict(meta),
        build_no_wli_order_dispatch_payload_fn=lambda **_: {"order": "col_then_sub"},
    )
    assert run_config["instance_input_mode"] == "generated"
    assert run_config["instance_fixture_ids"] == []
    assert run_config["search_seeds"] == []
    assert run_config["generated_key_seeds"] == [111]
    assert run_config["text_offsets"] == [0]
    assert "key_seeds" not in run_config


def test_build_run_config_serializes_fixed_mode_honestly() -> None:
    state = _make_runtime_state()
    state["INSTANCE_INPUT_MODE"] = "fixed_ciphertext"
    state["INSTANCE_FIXTURE_IDS"] = [
        "fixture_001__p9_c3_l1000__text0__seed611",
        "fixture_001__p9_c3_l1000__text0__seed1111",
    ]
    state["SEARCH_SEEDS"] = [7001, 7002]
    state["KEY_SEEDS"] = [111, 211]
    run_config = build_run_config(
        state=state,
        mode_canonical="candidate",
        mode_raw="candidate",
        mode_intent="test",
        stage3_can_skip=False,
        scoring_experiment_meta={"profile": "off"},
        root=REPO_ROOT,
        direction=Direction.LTR,
        autoskip_effective=True,
        proven_known=0,
        oracle_mode="benchmark_only",
        oracle_decision_paths_enabled=False,
        oracle_assist_selection_effective=False,
        is_adaptive_focus_mode_fn=lambda _mode: False,
        scorer_cfg_for_output_fn=lambda cfg, **_: dict(cfg),
        stage3_search_cfg_fn=lambda **_: {"objective": "avg.logp.win20"},
        scoring_meta_for_output_fn=lambda meta, **_: dict(meta),
        build_no_wli_order_dispatch_payload_fn=lambda **_: {"order": "col_then_sub"},
    )
    assert run_config["instance_input_mode"] == "fixed_ciphertext"
    assert run_config["instance_fixture_ids"] == [
        "fixture_001__p9_c3_l1000__text0__seed611",
        "fixture_001__p9_c3_l1000__text0__seed1111",
    ]
    assert run_config["search_seeds"] == [7001, 7002]
    assert run_config["generated_key_seeds"] == []
    assert run_config["text_offsets"] == [0]
    assert "key_seeds" not in run_config


def test_build_iteration_runtime_generated_mode_roundtrip_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_mod, "build_scorer", lambda *args, **kwargs: object())
    pt_idx = np.asarray([1, 2, 3, 4, 0, 1], dtype=np.uint8)
    out = runtime_mod.build_iteration_runtime(
        **_build_runtime_kwargs(
            pt_idx=pt_idx,
            key_seed=77,
            period=3,
            columns=2,
            alphabet_size=5,
        )
    )
    calc_ct = np.asarray(
        out["full_cipher"].encrypt_single(
            plaintext=np.asarray(pt_idx, dtype=np.uint8),
            key=np.asarray(out["key_true"], dtype=np.int16),
        ),
        dtype=np.uint8,
    ).reshape(-1)
    assert out["instance_input_mode"] == "generated"
    assert out["instance_fixture_id"] == ""
    assert int(out["instance_source_key_seed"]) == 77
    assert int(out["search_seed"]) == 77
    assert np.array_equal(calc_ct, np.asarray(out["ct_idx"], dtype=np.uint8))


def test_build_iteration_runtime_fixed_mode_uses_stored_ciphertext_key_and_oracle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_mod, "build_scorer", lambda *args, **kwargs: object())
    spec = load_fixed_instance_spec(
        FIXTURE_DIR / "fixture_001__p9_c3_l1000__text0__seed611.json"
    )
    pt_idx = np.asarray(spec.target_plaintext_idx, dtype=np.uint8)
    out = runtime_mod.build_iteration_runtime(
        **_build_runtime_kwargs(
            pt_idx=pt_idx,
            key_seed=7001,
            period=spec.period,
            columns=spec.columns,
            alphabet_size=spec.alphabet_size,
            order=spec.order,
            direction=Direction(spec.direction),
            instance_input_mode="fixed_ciphertext",
            fixed_instance_spec=spec,
            search_seed=7001,
        )
    )
    roundtrip_plaintext = np.asarray(
        out["full_cipher"].decrypt_single(
            ciphertext=np.asarray(out["ct_idx"], dtype=np.uint8),
            key=np.asarray(out["key_true"], dtype=np.int16),
        ),
        dtype=np.uint8,
    ).reshape(-1)
    assert out["instance_input_mode"] == "fixed_ciphertext"
    assert out["instance_fixture_id"] == spec.instance_fixture_id
    assert int(out["instance_source_key_seed"]) == int(spec.source_key_seed)
    assert int(out["search_seed"]) == 7001
    assert tuple(int(x) for x in np.asarray(out["key_true"], dtype=np.int16).tolist()) == spec.true_key_idx
    assert tuple(int(x) for x in np.asarray(out["ct_idx"], dtype=np.uint8).tolist()) == spec.ciphertext_idx
    assert tuple(int(x) for x in np.asarray(out["pt_idx"], dtype=np.uint8).tolist()) == spec.target_plaintext_idx
    assert out["wli"] == [[int(a), int(b)] for a, b in spec.target_wli]
    assert np.array_equal(roundtrip_plaintext, pt_idx)
    expected_oracle = np.asarray(
        out["sub_cipher"].decrypt_single(
            ciphertext=np.asarray(out["ct_idx"], dtype=np.uint8),
            key=np.asarray(out["true_sub"], dtype=np.int16),
        ),
        dtype=np.uint8,
    ).reshape(-1)
    assert np.array_equal(
        expected_oracle,
        np.asarray(out["pt_stage1_oracle"], dtype=np.uint8),
    )


def test_build_iteration_runtime_fixed_mode_rejects_mismatched_runtime_plaintext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_mod, "build_scorer", lambda *args, **kwargs: object())
    spec = load_fixed_instance_spec(
        FIXTURE_DIR / "fixture_001__p9_c3_l1000__text0__seed611.json"
    )
    with pytest.raises(
        ValueError,
        match="Fixed instance target_plaintext_idx does not match runtime pt_idx",
    ):
        runtime_mod.build_iteration_runtime(
            **_build_runtime_kwargs(
                pt_idx=np.asarray([0] * spec.length, dtype=np.uint8),
                key_seed=7001,
                period=spec.period,
                columns=spec.columns,
                alphabet_size=spec.alphabet_size,
                order=spec.order,
                direction=Direction(spec.direction),
                instance_input_mode="fixed_ciphertext",
                fixed_instance_spec=spec,
                search_seed=7001,
            )
        )


def test_build_iteration_runtime_fixed_mode_validates_mapping_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_mod, "build_scorer", lambda *args, **kwargs: object())
    spec = load_fixed_instance_spec(
        FIXTURE_DIR / "fixture_001__p9_c3_l1000__text0__seed611.json"
    )
    bad_mapping = dict(spec.__dict__)
    bad_mapping["true_key_idx"] = tuple(spec.true_key_idx[:-1])
    with pytest.raises(ValueError, match="true_key_idx length must be"):
        runtime_mod.build_iteration_runtime(
            **_build_runtime_kwargs(
                pt_idx=np.asarray(spec.target_plaintext_idx, dtype=np.uint8),
                key_seed=7001,
                period=spec.period,
                columns=spec.columns,
                alphabet_size=spec.alphabet_size,
                order=spec.order,
                direction=Direction(spec.direction),
                instance_input_mode="fixed_ciphertext",
                fixed_instance_spec=bad_mapping,
                search_seed=7001,
            )
        )


def test_load_fixed_instance_specs_deduplicates_fixture_paths() -> None:
    fixture_path = FIXTURE_DIR / "fixture_001__p9_c3_l1000__text0__seed611.json"
    specs = load_fixed_instance_specs(
        fixture_paths=[fixture_path, fixture_path],
    )
    assert [spec.instance_fixture_id for spec in specs] == [
        "fixture_001__p9_c3_l1000__text0__seed611"
    ]


def test_build_fixed_instance_spec_from_artifact_recomputes_true_key_and_recovers_target_wli(
    tmp_path: Path,
) -> None:
    period = 3
    columns = 2
    alphabet_size = 5
    source_key_seed = 77
    target_plaintext_idx = (1, 2, 3, 4, 0, 1)
    true_key_idx = _build_true_key_idx(
        source_key_seed=source_key_seed,
        period=period,
        columns=columns,
        alphabet_size=alphabet_size,
    )
    cipher = _build_cipher(
        period=period,
        columns=columns,
        alphabet_size=alphabet_size,
        direction="ltr",
        order="col_then_sub",
    )
    ciphertext_idx = (
        np.asarray(
            cipher.encrypt_single(
                plaintext=np.asarray(target_plaintext_idx, dtype=np.uint8),
                key=np.asarray(true_key_idx, dtype=np.int16),
            ),
            dtype=np.uint8,
        )
        .reshape(-1)
        .astype(int)
        .tolist()
    )
    artifact_path = tmp_path / "fixture_fixture_001_p3_c2_l6__text0__seed77.json"
    artifact_path.write_text(
        json.dumps(
            {
                "key_seed": source_key_seed,
                "text_id": 0,
                "offset_used": 5,
                "period": period,
                "columns": columns,
                "length": len(target_plaintext_idx),
                "alphabet_size": alphabet_size,
                "direction": "ltr",
                "order": "col_then_sub",
                "ciphertext_idx": ciphertext_idx,
                "target_plaintext_idx": list(target_plaintext_idx),
            }
        ),
        encoding="utf-8",
    )

    def _fake_encode(_direction: Direction) -> tuple[np.ndarray, np.ndarray]:
        return (
            np.asarray([9, 8, 7, 6, 5, 4, 3, 2], dtype=np.uint8),
            np.asarray([[0, 2], [1, 2], [0, 2], [1, 2], [0, 2], [1, 2], [0, 2], [1, 2]], dtype=np.uint8),
        )

    def _fake_slice(*_args, **_kwargs) -> tuple[np.ndarray, list[list[int]], int]:
        return (
            np.asarray(target_plaintext_idx, dtype=np.uint8),
            [[0, 2], [1, 2], [0, 2], [1, 2], [0, 2], [1, 2]],
            5,
        )

    spec = build_fixed_instance_spec_from_artifact(
        artifact_path,
        encode_long_plaintext_fn=_fake_encode,
        slice_word_aligned_fn=_fake_slice,
    )

    assert spec.fixture_schema_version == FIXED_CIPHER_INSTANCE_SCHEMA_VERSION
    assert spec.instance_fixture_id == "fixture_001__p3_c2_l6__text0__seed77"
    assert spec.source_fixture_id == "fixture_001"
    assert spec.source_key_seed == 77
    assert spec.ciphertext_idx == tuple(int(x) for x in ciphertext_idx)
    assert spec.target_plaintext_idx == target_plaintext_idx
    assert spec.target_wli == ((0, 2), (1, 2), (0, 2), (1, 2), (0, 2), (1, 2))
    assert spec.true_key_idx == true_key_idx


def test_load_fixed_instance_spec_validates_lengths_and_true_key_size(tmp_path: Path) -> None:
    bad_fixture = tmp_path / "bad_fixture.json"
    bad_fixture.write_text(
        json.dumps(
            {
                "fixture_schema_version": FIXED_CIPHER_INSTANCE_SCHEMA_VERSION,
                "instance_fixture_id": "fixture_001__p9_c3_l10__text0__seed611",
                "source_artifact_rel_path": "output/example.json",
                "source_run_id": "run_1",
                "source_fixture_id": "fixture_001",
                "text_id": 0,
                "source_key_seed": 611,
                "offset_used": 5,
                "period": 9,
                "columns": 3,
                "length": 10,
                "alphabet_size": 29,
                "direction": "ltr",
                "order": "col_then_sub",
                "ciphertext_idx": [0] * 10,
                "target_plaintext_idx": [0] * 10,
                "target_wli": [[0, 1]] * 10,
                "true_key_idx": [0] * 10,
                "notes": [],
            }
        ),
        encoding="utf-8",
    )
    try:
        load_fixed_instance_spec(bad_fixture)
    except ValueError as exc:
        assert "true_key_idx length" in str(exc)
    else:
        raise AssertionError("Expected invalid true_key_idx length to raise")


def test_load_fixed_instance_spec_map_rejects_duplicate_instance_ids(tmp_path: Path) -> None:
    fixture_payload = {
        "fixture_schema_version": FIXED_CIPHER_INSTANCE_SCHEMA_VERSION,
        "instance_fixture_id": "fixture_001__p9_c3_l10__text0__seed611",
        "source_artifact_rel_path": "output/example.json",
        "source_run_id": "run_1",
        "source_fixture_id": "fixture_001",
        "text_id": 0,
        "source_key_seed": 611,
        "offset_used": 5,
        "period": 1,
        "columns": 1,
        "length": 2,
        "alphabet_size": 2,
        "direction": "ltr",
        "order": "col_then_sub",
        "ciphertext_idx": [0, 1],
        "target_plaintext_idx": [0, 1],
        "target_wli": [[0, 1], [0, 1]],
        "true_key_idx": [0, 1, 0],
        "notes": [],
    }
    path_a = tmp_path / "a.json"
    path_b = tmp_path / "b.json"
    path_a.write_text(json.dumps(fixture_payload), encoding="utf-8")
    path_b.write_text(json.dumps(fixture_payload), encoding="utf-8")
    try:
        load_fixed_instance_spec_map(fixture_paths=[path_a, path_b])
    except ValueError as exc:
        assert "Duplicate instance_fixture_id" in str(exc)
    else:
        raise AssertionError("Expected duplicate instance_fixture_id to raise")


def test_load_fixed_panel_manifest_and_exported_fixtures_for_v1_panel() -> None:
    panel = load_fixed_cipher_panel_spec(PANEL_PATH)
    assert panel.panel_id == "p9_c3_solver_panel_v1"
    assert panel.instance_fixture_ids == (
        "fixture_001__p9_c3_l1000__text0__seed611",
        "fixture_001__p9_c3_l1000__text0__seed1111",
        "fixture_001__p9_c3_l1000__text0__seed1411",
        "fixture_001__p9_c3_l1000__text0__seed1511",
    )
    assert panel.search_seeds == (7001, 7002, 7003, 7004, 7005)
    for instance_fixture_id in panel.instance_fixture_ids:
        fixture_path = FIXTURE_DIR / f"{instance_fixture_id}.json"
        spec = load_fixed_instance_spec(fixture_path)
        assert spec.instance_fixture_id == instance_fixture_id
        assert spec.source_key_seed in {611, 1111, 1411, 1511}
        assert spec.length == 1000
        assert spec.period == 9
        assert spec.columns == 3


def test_exported_v1_panel_fixtures_reencrypt_and_reconstruct_target_wli() -> None:
    panel = load_fixed_cipher_panel_spec(PANEL_PATH)
    for instance_fixture_id in panel.instance_fixture_ids:
        spec = load_fixed_instance_spec(FIXTURE_DIR / f"{instance_fixture_id}.json")
        cipher = _build_cipher(
            period=spec.period,
            columns=spec.columns,
            alphabet_size=spec.alphabet_size,
            direction=spec.direction,
            order=spec.order,
        )
        ciphertext_idx = tuple(
            int(x)
            for x in np.asarray(
                cipher.encrypt_single(
                    plaintext=np.asarray(spec.target_plaintext_idx, dtype=np.uint8),
                    key=np.asarray(spec.true_key_idx, dtype=np.int16),
                ),
                dtype=np.uint8,
            ).reshape(-1).astype(int).tolist()
        )
        assert ciphertext_idx == spec.ciphertext_idx

        pt_base, wli_base = base._encode_long_plaintext(Direction(spec.direction))
        recovered_pt, recovered_wli, recovered_offset = base._slice_word_aligned(
            pt_base,
            wli_base,
            length=spec.length,
            offset_hint=spec.offset_used,
        )
        assert tuple(int(x) for x in recovered_pt.astype(int).tolist()) == spec.target_plaintext_idx
        assert tuple((int(a), int(b)) for a, b in recovered_wli) == spec.target_wli
        assert int(recovered_offset) == spec.offset_used


def test_load_fixed_panel_manifest_and_exported_fixtures_for_canary_panel() -> None:
    panel = load_fixed_cipher_panel_spec(CANARY_PANEL_PATH)
    assert panel.panel_id == "p9_c3_solver_panel_canary_v1"
    assert panel.instance_fixture_ids == (
        "fixture_001__p9_c3_l1000__text0__seed611",
    )
    assert panel.search_seeds == (7001,)
    spec = load_fixed_instance_spec(FIXTURE_DIR / f"{panel.instance_fixture_ids[0]}.json")
    assert spec.instance_fixture_id == panel.instance_fixture_ids[0]
    assert spec.source_key_seed == 611


def test_run_iteration_matrix_fixed_mode_iterates_fixture_ids_and_search_seeds() -> None:
    specs = [
        load_fixed_instance_spec(
            FIXTURE_DIR / "fixture_001__p9_c3_l1000__text0__seed611.json"
        ),
        load_fixed_instance_spec(
            FIXTURE_DIR / "fixture_001__p9_c3_l1000__text0__seed1111.json"
        ),
    ]
    observed_pre_states: list[dict[str, object]] = []
    run_iteration_matrix(
        run_id="fixed_mode_test",
        tiers=[SimpleNamespace(name="fixture_001_p9_c3_l1000", period=9, columns=3, length=1000)],
        text_offsets=[],
        key_seeds=[],
        pt_base=[],
        wli_base=[],
        direction=SimpleNamespace(value="ltr"),
        span_assets_dir=None,
        scoring_experiment_meta={"profile": "off"},
        autoskip_effective=False,
        proven_index={},
        instances=[],
        stages=[],
        stage3_runtime_call_ctx=SimpleNamespace(),
        config=_fixed_mode_matrix_config(),
        fns=_build_fixed_mode_matrix_fns(observed_pre_states=observed_pre_states),
        instance_input_mode="fixed_ciphertext",
        fixed_instance_specs=specs,
        search_seeds=[7001, 7002],
    )
    assert len(observed_pre_states) == 4
    expected_fixture_ids = {
        "fixture_001__p9_c3_l1000__text0__seed611",
        "fixture_001__p9_c3_l1000__text0__seed1111",
    }
    expected_pairs = {
        (fixture_id, search_seed)
        for fixture_id in expected_fixture_ids
        for search_seed in {7001, 7002}
    }
    observed_pairs = {
        (str(row["instance_fixture_id"]), int(row["search_seed"]))
        for row in observed_pre_states
    }
    assert observed_pairs == expected_pairs
    for row in observed_pre_states:
        assert row["instance_input_mode"] == "fixed_ciphertext"
        assert row["key_seed"] == row["search_seed"]
        assert row["instance_fixture_id"] == row["fixed_instance_fixture_id"]
        if row["instance_fixture_id"] == "fixture_001__p9_c3_l1000__text0__seed611":
            assert int(row["instance_source_key_seed"]) == 611
        if row["instance_fixture_id"] == "fixture_001__p9_c3_l1000__text0__seed1111":
            assert int(row["instance_source_key_seed"]) == 1111


def test_build_iteration_payloads_fixed_mode_includes_identity_fields() -> None:
    inst_row, artifact_payload = build_iteration_payloads(
        tier_name="fixture_fixture_001_p9_c3_l1000",
        period=9,
        columns=3,
        length=1000,
        text_id=0,
        key_seed=7001,
        instance_input_mode="fixed_ciphertext",
        instance_fixture_id="fixture_001__p9_c3_l1000__text0__seed611",
        instance_source_key_seed=611,
        search_seed=7001,
        offset_hint=5,
        offset_used=5,
        status="unsolved",
        stop_reason="done",
        solve_threshold=0.9,
        best_stage="stage3_full_refine",
        best_match_ratio=0.5,
        stage1_sub_key_match=0.1,
        stage2_match_ratio=0.4,
        stage3_match_ratio=0.5,
        stage2_gap_to_oracle=0.0,
        stage3_band="mid",
        basin_judge_span_calls_total=0,
        basin_judge_span_calls_active=0,
        basin_judge_span_calls_rejected_or_gated=0,
        basin_judge_span_seconds_total=0.0,
        basin_judge_unique_end_hash=0,
        oracle_mode="off",
        oracle_consulted_in_decisions=False,
        total_seconds=1.0,
        total_evals=10,
        preview_best_latin="PREVIEW",
        outcome_code="unsolved",
        profile_id="profile",
        mode="candidate",
        direction="ltr",
        order="col_then_sub",
        alphabet_size=29,
        best_score=1.0,
        oracle_scores={},
        score_minus_oracle={},
        ciphertext_idx=[0, 1, 2],
        target_plaintext_idx=[0, 1, 2],
        final_best_key_idx=[1, 2, 3],
        final_best_plaintext_idx=[0, 1, 2],
        stage2_topk=[],
        stage2_topk_has_best_match=False,
        stage2_diagnostics={},
        stage3_topk=[],
        stage3_diagnostics={},
    )
    assert inst_row["instance_input_mode"] == "fixed_ciphertext"
    assert inst_row["instance_fixture_id"] == "fixture_001__p9_c3_l1000__text0__seed611"
    assert int(inst_row["instance_source_key_seed"]) == 611
    assert int(inst_row["search_seed"]) == 7001
    assert artifact_payload["instance_input_mode"] == "fixed_ciphertext"
    assert artifact_payload["instance_fixture_id"] == "fixture_001__p9_c3_l1000__text0__seed611"
    assert int(artifact_payload["instance_source_key_seed"]) == 611
    assert int(artifact_payload["search_seed"]) == 7001


def test_commit_iteration_outputs_fixed_mode_uses_instance_fixture_and_search_seed(
    tmp_path: Path,
) -> None:
    root = tmp_path
    run_dir = root / "output" / "run"
    final_dir = run_dir / "final_instances"
    hist_path = root / "history.csv"
    hist_rows: list[dict[str, object]] = []
    inst_row, artifact_payload = build_iteration_payloads(
        tier_name="fixture_fixture_001_p9_c3_l1000",
        period=9,
        columns=3,
        length=1000,
        text_id=0,
        key_seed=7001,
        instance_input_mode="fixed_ciphertext",
        instance_fixture_id="fixture_001__p9_c3_l1000__text0__seed611",
        instance_source_key_seed=611,
        search_seed=7001,
        offset_hint=5,
        offset_used=5,
        status="unsolved",
        stop_reason="done",
        solve_threshold=0.9,
        best_stage="stage3_full_refine",
        best_match_ratio=0.5,
        stage1_sub_key_match=0.1,
        stage2_match_ratio=0.4,
        stage3_match_ratio=0.5,
        stage2_gap_to_oracle=0.0,
        stage3_band="mid",
        basin_judge_span_calls_total=0,
        basin_judge_span_calls_active=0,
        basin_judge_span_calls_rejected_or_gated=0,
        basin_judge_span_seconds_total=0.0,
        basin_judge_unique_end_hash=0,
        oracle_mode="off",
        oracle_consulted_in_decisions=False,
        total_seconds=1.0,
        total_evals=10,
        preview_best_latin="PREVIEW",
        outcome_code="unsolved",
        profile_id="profile",
        mode="candidate",
        direction="ltr",
        order="col_then_sub",
        alphabet_size=29,
        best_score=1.0,
        oracle_scores={},
        score_minus_oracle={},
        ciphertext_idx=[0, 1, 2],
        target_plaintext_idx=[0, 1, 2],
        final_best_key_idx=[1, 2, 3],
        final_best_plaintext_idx=[0, 1, 2],
        stage2_topk=[],
        stage2_topk_has_best_match=False,
        stage2_diagnostics={},
        stage3_topk=[],
        stage3_diagnostics={},
    )
    commit_iteration_outputs(
        run_dir=run_dir,
        final_dir=final_dir,
        root=root,
        hist_path=hist_path,
        tiers=[],
        instances=[],
        stages=[],
        inst_row=inst_row,
        artifact_payload=artifact_payload,
        done=0,
        total=1,
        t0_all=0.0,
        last_hb=0.0,
        heartbeat_seconds=9999.0,
        best_global=dict(
            match=float("-inf"),
            tier="",
            text_id=-1,
            key_seed=-1,
            stage="",
            preview="",
        ),
        history_rows_written=0,
        audit_rows_written=0,
        audit_enabled=False,
        audit_csv=root / "audit.csv",
        audit_jsonl=root / "audit.jsonl",
        audit_prev_chain_hash="",
        write_json_fn=_write_json,
        build_summary_fn=lambda _tiers, _instances: {"count": len(_instances)},
        write_pipeline_snapshot_files_fn=lambda **kwargs: None,
        append_csv_row_fn=lambda _path, row: hist_rows.append(dict(row)),
        append_iteration_audit_row_fn=lambda **kwargs: str(kwargs["prev_chain_hash"]),
        hash_payload_fn=lambda payload: json.dumps(payload, sort_keys=True),
        sha256_file_fn=lambda _path: "sha256",
        format_seconds_fn=lambda seconds: f"{seconds:.1f}s",
    )
    artifact_path = (
        final_dir
        / "fixture_001__p9_c3_l1000__text0__seed611__search7001.json"
    )
    assert artifact_path.exists()
    assert len(hist_rows) == 1
    assert hist_rows[0]["fixture_id"] == "fixture_001__p9_c3_l1000__text0__seed611"
    assert hist_rows[0]["instance_input_mode"] == "fixed_ciphertext"
    assert int(hist_rows[0]["search_seed"]) == 7001
    assert int(hist_rows[0]["instance_source_key_seed"]) == 611


def test_load_proven_solved_index_keeps_generated_and_fixed_identity_keys_distinct(
    tmp_path: Path,
) -> None:
    hist_path = tmp_path / "history.csv"
    fieldnames = [
        "timestamp_utc",
        "run_id",
        "status",
        "fixture_id",
        "text_id",
        "key_seed",
        "instance_input_mode",
        "instance_fixture_id",
        "instance_source_key_seed",
        "search_seed",
        "best_match_ratio",
        "best_stage",
        "total_seconds",
        "total_evals",
    ]
    with hist_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            dict(
                timestamp_utc="2026-04-08T00:00:00Z",
                run_id="generated_run",
                status="solved",
                fixture_id="fixture_fixture_001_p9_c3_l1000",
                text_id=0,
                key_seed=7001,
                instance_input_mode="generated",
                instance_fixture_id="",
                instance_source_key_seed=7001,
                search_seed=7001,
                best_match_ratio=1.0,
                best_stage="stage2_search",
                total_seconds="1.0",
                total_evals="10",
            )
        )
        writer.writerow(
            dict(
                timestamp_utc="2026-04-08T00:01:00Z",
                run_id="fixed_run",
                status="solved",
                fixture_id="fixture_001__p9_c3_l1000__text0__seed611",
                text_id=0,
                key_seed=7001,
                instance_input_mode="fixed_ciphertext",
                instance_fixture_id="fixture_001__p9_c3_l1000__text0__seed611",
                instance_source_key_seed=611,
                search_seed=7001,
                best_match_ratio=1.0,
                best_stage="stage35_substitution_only",
                total_seconds="2.0",
                total_evals="20",
            )
        )
    out = load_proven_solved_index(hist_path, min_match=0.9)
    generated_key = build_proven_solved_key(
        tier_name="fixture_fixture_001_p9_c3_l1000",
        text_id=0,
        key_seed=7001,
        instance_input_mode="generated",
    )
    fixed_key = build_proven_solved_key(
        tier_name="fixture_fixture_001_p9_c3_l1000",
        text_id=0,
        key_seed=7001,
        instance_input_mode="fixed_ciphertext",
        instance_fixture_id="fixture_001__p9_c3_l1000__text0__seed611",
        search_seed=7001,
    )
    assert generated_key in out
    assert fixed_key in out
    assert generated_key != fixed_key
    assert out[generated_key]["run_id"] == "generated_run"
    assert out[fixed_key]["run_id"] == "fixed_run"


def test_run_iteration_matrix_fixed_mode_autoskip_uses_instance_fixture_id_and_search_seed() -> None:
    spec = load_fixed_instance_spec(
        FIXTURE_DIR / "fixture_001__p9_c3_l1000__text0__seed611.json"
    )
    skipped: list[tuple[str, int, int]] = []

    def _skip_handler(**kwargs):
        skipped.append(
            (
                str(kwargs["instance_fixture_id"]),
                int(kwargs["instance_source_key_seed"]),
                int(kwargs["search_seed"]),
            )
        )

    fns = _build_fixed_mode_matrix_fns(observed_pre_states=[])
    fns = IterationMatrixFns(
        **{
            **fns.__dict__,
            "handle_autoskip_proven_iteration_fn": _skip_handler,
            "run_iteration_pre_stage3_fn": lambda **_: (_ for _ in ()).throw(
                AssertionError("autoskip should have short-circuited fixed iteration")
            ),
        }
    )
    proven_index = {
        build_proven_solved_key(
            tier_name="fixture_001_p9_c3_l1000",
            text_id=0,
            key_seed=7001,
            instance_input_mode="fixed_ciphertext",
            instance_fixture_id=spec.instance_fixture_id,
            search_seed=7001,
        ): {"run_id": "fixed_prev", "timestamp_utc": "2026-04-08T00:00:00Z", "best_match_ratio": 1.0},
    }
    run_iteration_matrix(
        tiers=[SimpleNamespace(name="fixture_001_p9_c3_l1000", period=9, columns=3, length=1000)],
        text_offsets=[],
        key_seeds=[],
        pt_base=[],
        wli_base=[],
        direction=SimpleNamespace(value="ltr"),
        span_assets_dir=None,
        scoring_experiment_meta={"profile": "off"},
        autoskip_effective=True,
        proven_index=proven_index,
        instances=[],
        stages=[],
        stage3_runtime_call_ctx=SimpleNamespace(),
        config=_fixed_mode_matrix_config(),
        fns=fns,
        instance_input_mode="fixed_ciphertext",
        fixed_instance_specs=[spec],
        search_seeds=[7001],
    )
    assert skipped == [(spec.instance_fixture_id, 611, 7001)]


def test_run_iteration_matrix_fixed_mode_rejects_tier_mismatch_loudly() -> None:
    spec = load_fixed_instance_spec(
        FIXTURE_DIR / "fixture_001__p9_c3_l1000__text0__seed611.json"
    )
    with pytest.raises(
        ValueError,
        match="No fixed instance specs matched tier",
    ):
        run_iteration_matrix(
            tiers=[SimpleNamespace(name="fixture_001_p7_c1_l1000", period=7, columns=1, length=1000)],
            text_offsets=[],
            key_seeds=[],
            pt_base=[],
            wli_base=[],
            direction=SimpleNamespace(value="ltr"),
            span_assets_dir=None,
            scoring_experiment_meta={"profile": "off"},
            autoskip_effective=False,
            proven_index={},
            instances=[],
            stages=[],
            stage3_runtime_call_ctx=SimpleNamespace(),
            config=_fixed_mode_matrix_config(),
            fns=_build_fixed_mode_matrix_fns(observed_pre_states=[]),
            instance_input_mode="fixed_ciphertext",
            fixed_instance_specs=[spec],
            search_seeds=[7001],
        )


def test_finalize_run_outputs_fixed_mode_reads_best_artifact_by_instance_fixture_and_search_seed(
    tmp_path: Path,
) -> None:
    root = tmp_path
    run_dir = root / "output" / "run"
    final_dir = run_dir / "final_instances"
    best_dir = run_dir / "best"
    hist_path = root / "history.csv"
    run_manifest_path = run_dir / "run_manifest.json"
    hist_path.write_text("", encoding="utf-8")
    best_row = {
        "tier": "fixture_fixture_001_p9_c3_l1000",
        "text_id": 0,
        "key_seed": 7001,
        "instance_input_mode": "fixed_ciphertext",
        "instance_fixture_id": "fixture_001__p9_c3_l1000__text0__seed611",
        "instance_source_key_seed": 611,
        "search_seed": 7001,
        "best_match_ratio": 0.761,
        "preview_best_latin": "PREVIEW TEXT",
        "truth_key_hamming_total": 17,
    }
    _write_json(
        final_dir / "fixture_001__p9_c3_l1000__text0__seed611__search7001.json",
        {
            "best_match_ratio": 0.761,
            "instance_input_mode": "fixed_ciphertext",
            "instance_fixture_id": "fixture_001__p9_c3_l1000__text0__seed611",
            "instance_source_key_seed": 611,
            "search_seed": 7001,
            "stage3_diagnostics": {"phaseC_start_summaries": [{"start_idx": 1}]},
            "truth_diagnostics": {"available": True, "key_hamming_total": 17},
            "target_key_idx": [1, 2, 3],
            "stage3_topk": [{"rank": 1, "match_ratio": 0.761}],
        },
    )

    def _write_snapshots(*, run_dir: Path, instances, stages, summary) -> None:
        _write_json(run_dir / "summary.json", summary)
        _write_json(run_dir / "instances.json", list(instances))
        _write_json(run_dir / "stages.json", list(stages))

    finalize_run_outputs(
        run_dir=run_dir,
        final_dir=final_dir,
        best_dir=best_dir,
        root=root,
        hist_path=hist_path,
        t0_all=0.0,
        oracle_consulted_in_decisions=False,
        total=1,
        done=1,
        status_counts={"solved": 0, "stalled": 0, "unsolved": 1, "skipped_proven": 0},
        history_rows_written=1,
        audit_rows_written=0,
        audit_prev_chain_hash="",
        tiers=[],
        instances=[best_row],
        stages=[],
        run_manifest={},
        run_manifest_path=run_manifest_path,
        write_json_fn=_write_json,
        write_pipeline_snapshot_files_fn=_write_snapshots,
        build_summary_fn=lambda _tiers, _instances: {"count": len(_instances)},
        sha256_file_fn=lambda _path: "sha256",
        format_seconds_fn=lambda seconds: f"{seconds:.1f}s",
    )
    best_instance = json.loads(
        (best_dir / "best_instance.json").read_text(encoding="utf-8")
    )
    assert best_instance["instance_input_mode"] == "fixed_ciphertext"
    assert best_instance["instance_fixture_id"] == "fixture_001__p9_c3_l1000__text0__seed611"
    assert int(best_instance["search_seed"]) == 7001
    assert best_instance["target_key_idx"] == [1, 2, 3]


def test_write_resume_handoff_artifacts_keeps_fixed_identity_fields(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    final_dir = run_dir / "final_instances"
    final_dir.mkdir(parents=True)
    artifact_path = final_dir / "fixture_001__p9_c3_l1000__text0__seed611__search7001.json"
    run_config_path = run_dir / "run_config.json"
    run_config_path.write_text(json.dumps(_resume_run_config()), encoding="utf-8")
    artifact_payload = {
        "tier": "fixture_fixture_001_p9_c3_l1000",
        "profile_id": "profile",
        "mode": "candidate",
        "oracle_mode": "off",
        "oracle_consulted_in_decisions": False,
        "direction": "ltr",
        "order": "col_then_sub",
        "alphabet_size": 29,
        "text_id": 0,
        "key_seed": 7001,
        "instance_input_mode": "fixed_ciphertext",
        "instance_fixture_id": "fixture_001__p9_c3_l1000__text0__seed611",
        "instance_source_key_seed": 611,
        "search_seed": 7001,
        "offset_hint": 5,
        "offset_used": 5,
        "period": 9,
        "columns": 3,
        "length": 1000,
        "status": "unsolved",
        "stop_reason": "done",
        "outcome_code": "unsolved",
        "best_stage": "stage3_full_refine",
        "best_match_ratio": 0.5,
        "best_score": 3.0,
        "oracle_scores": {"stage3": 0.0},
        "score_minus_oracle": {},
        "solve_threshold": 0.9,
        "ciphertext_idx": [0, 0, 0],
        "target_plaintext_idx": [0, 1, 2],
        "final_best_key_idx": [0, 1, 2],
        "final_best_plaintext_idx": [0, 1, 2],
        "stage2_topk": [
            {
                "rank": 1,
                "score_stage2": 3.0,
                "score_judge": 3.1,
                "match_ratio": 0.5,
                "key_idx": [0, 1, 2],
                "plaintext_idx": [0, 1, 2],
            }
        ],
        "stage2_topk_has_best_match": 1,
        "stage2_diagnostics": {},
        "stage3_topk": [],
        "stage3_diagnostics": {"phaseC_start_summaries": []},
        "stage35_archive": [],
        "stage35_seed_rows": [],
    }
    write_resume_handoff_artifacts(
        run_dir=run_dir,
        root=tmp_path,
        artifact_path=artifact_path,
        artifact_payload=artifact_payload,
        run_config_path=run_config_path,
        write_json_fn=_write_json,
    )
    summary_path = run_dir / "resume_handoffs" / artifact_path.stem / "manifest.json"
    assert summary_path.exists()


def test_artifact_resume_write_resume_bundle_keeps_fixed_identity_fields(
    tmp_path: Path,
) -> None:
    payload = {
        "mode": "selected_stage3_to_stage35",
        "instance_input_mode": "fixed_ciphertext",
        "instance_fixture_id": "fixture_001__p9_c3_l1000__text0__seed611",
        "instance_source_key_seed": 611,
        "search_seed": 7001,
        "selector": "legacy",
        "fixture_id": "demo_fixture",
        "fixture_label": "demo",
        "selected_candidate_hash": "abc",
        "selected_candidate_source": "phaseB_topk",
        "selected_candidate_lane": "anchor",
        "selected_candidate_final_score": 1.0,
        "selected_candidate_final_match": 0.5,
        "replay_material_complete": 1,
        "stage35_partial_state_relpath": "output/demo/state.json",
        "stage35_progress_jsonl_relpath": "output/demo/progress.jsonl",
        "stage35": {"archive_rows": [], "seed_rows_scored": []},
    }
    artifact_resume_mod.write_resume_bundle(payload, output_dir=tmp_path)
    selected_summary = json.loads(
        (tmp_path / "selected_trial_row_summary.json").read_text(encoding="utf-8")
    )
    assert selected_summary["instance_input_mode"] == "fixed_ciphertext"
    assert selected_summary["instance_fixture_id"] == "fixture_001__p9_c3_l1000__text0__seed611"
    assert int(selected_summary["instance_source_key_seed"]) == 611
    assert int(selected_summary["search_seed"]) == 7001


def test_artifact_resume_identity_fields_require_fixed_mode_identity_contract() -> None:
    with pytest.raises(ValueError, match="fixed_ciphertext artifact missing search_seed"):
        artifact_resume_mod._artifact_identity_fields(
            {
                "key_seed": 7001,
                "instance_input_mode": "fixed_ciphertext",
                "instance_fixture_id": "fixture_001__p9_c3_l1000__text0__seed611",
                "instance_source_key_seed": 611,
            }
        )


def test_artifact_resume_write_resume_bundle_rejects_incomplete_fixed_identity(
    tmp_path: Path,
) -> None:
    payload = {
        "mode": "selected_stage3_to_stage35",
        "instance_input_mode": "fixed_ciphertext",
        "instance_fixture_id": "fixture_001__p9_c3_l1000__text0__seed611",
        "instance_source_key_seed": 611,
        "selector": "legacy",
        "fixture_id": "demo_fixture",
        "fixture_label": "demo",
        "selected_candidate_hash": "abc",
        "selected_candidate_source": "phaseB_topk",
        "selected_candidate_lane": "anchor",
        "selected_candidate_final_score": 1.0,
        "selected_candidate_final_match": 0.5,
        "replay_material_complete": 1,
        "stage35_partial_state_relpath": "output/demo/state.json",
        "stage35_progress_jsonl_relpath": "output/demo/progress.jsonl",
        "stage35": {"archive_rows": [], "seed_rows_scored": []},
    }
    with pytest.raises(ValueError, match="fixed_ciphertext artifact missing search_seed"):
        artifact_resume_mod.write_resume_bundle(payload, output_dir=tmp_path)


def test_execute_pipeline_from_startup_fixed_mode_loads_specs_and_search_seeds(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        pipeline_exec_mod,
        "initialize_run_state",
        lambda **_kwargs: {
            "stages": [],
            "instances": [],
            "total": 1,
            "t0_all": 0.0,
            "progress": {
                "done": 0,
                "history_rows_written": 0,
                "audit_rows_written": 0,
                "audit_prev_chain_hash": "",
                "status_counts": {"solved": 0},
            },
            "run_manifest_path": tmp_path / "run_manifest.json",
            "run_manifest": {},
        },
    )
    monkeypatch.setattr(
        pipeline_exec_mod,
        "write_stage_engine_contract_artifacts",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        pipeline_exec_mod,
        "build_commit_iteration_callback",
        lambda **_kwargs: object(),
    )
    monkeypatch.setattr(
        pipeline_exec_mod,
        "build_iteration_wiring",
        lambda **_kwargs: {
            "stage3_runtime_call_ctx": SimpleNamespace(),
            "iteration_config": object(),
            "iteration_fns": object(),
        },
    )
    monkeypatch.setattr(
        pipeline_exec_mod,
        "run_iteration_matrix",
        lambda **kwargs: captured.setdefault("run_kwargs", kwargs),
    )
    monkeypatch.setattr(
        pipeline_exec_mod,
        "finalize_run_outputs",
        lambda **_kwargs: None,
    )
    state = _make_runtime_state()
    state.update(
        {
            "INSTANCE_INPUT_MODE": "fixed_ciphertext",
            "INSTANCE_FIXTURE_IDS": ["fixture_001__p9_c3_l1000__text0__seed611"],
            "SEARCH_SEEDS": [7001],
            "KEY_SEEDS": [],
            "TIERS": [SimpleNamespace(name="fixture_fixture_001_p9_c3_l1000", period=9, columns=3, length=1000)],
            "ORDER": "col_then_sub",
            "PROFILE": "profile",
            "PIPELINE_RUN_MODE": "candidate",
            "AUDIT_HASH_CHAIN_ENABLED": False,
            "AUDIT_HASH_CHAIN_SEED": "",
            "write_json": _write_json,
            "_git_short": lambda: "deadbee",
            "_git_commit": lambda: "deadbeef",
            "_git_dirty": lambda: False,
            "_commit_iteration_outputs_bridge_external": lambda **_kwargs: None,
            "_scoring_meta_for_output": lambda meta, **_kwargs: dict(meta),
            "_canonical_run_mode": lambda mode: str(mode),
            "_build_summary": lambda _tiers, _instances: {"count": len(_instances)},
            "_scorer_objective_summary": lambda *_args: "",
            "_oracle_score_for_stage": lambda **_kwargs: 0.0,
            "_weights_text": lambda *_args: "",
            "_fmt_finite_float": lambda *_args: "",
            "_print_stage_preview": lambda **_kwargs: None,
            "_sha256_file": lambda _path: "sha256",
            "write_pipeline_snapshot_files": lambda **_kwargs: None,
            "base": SimpleNamespace(
                _format_seconds=lambda seconds: f"{seconds:.1f}s",
                _slice_word_aligned=lambda *args, **kwargs: [],
                _safe_preview_latin=lambda *_args, **_kwargs: "",
            ),
        }
    )
    startup = {
        "direction": SimpleNamespace(value="ltr"),
        "pt_base": [],
        "wli_base": [],
        "root": REPO_ROOT,
        "run_dir": tmp_path / "run",
        "best_dir": tmp_path / "run" / "best",
        "final_dir": tmp_path / "run" / "final_instances",
        "audit_csv": tmp_path / "run" / "audit.csv",
        "audit_jsonl": tmp_path / "run" / "audit.jsonl",
        "audit_prev_chain_hash": "",
        "hist": tmp_path / "history.csv",
        "autoskip_effective": False,
        "proven_index": {},
        "oracle_mode": "off",
        "oracle_decision_paths_enabled": False,
        "oracle_assist_selection_effective": False,
        "oracle_consulted_in_decisions": False,
        "scoring_experiment_meta": {"profile": "off"},
        "run_config_path": tmp_path / "run" / "run_config.json",
        "non_scoring_lock_hash": "n",
        "scoring_lock_hash": "s",
        "run_config_hash": "r",
        "span_assets_dir": None,
        "span_combined_calibration_hash": "",
        "span_ecdf_audit_hash": "",
        "span_assets_rel_path": "",
    }
    pipeline_exec_mod.execute_pipeline_from_startup(state=state, startup=startup)
    run_kwargs = captured["run_kwargs"]
    assert run_kwargs["instance_input_mode"] == "fixed_ciphertext"
    assert run_kwargs["search_seeds"] == [7001]
    fixed_specs = run_kwargs["fixed_instance_specs"]
    assert len(fixed_specs) == 1
    assert fixed_specs[0].instance_fixture_id == "fixture_001__p9_c3_l1000__text0__seed611"
