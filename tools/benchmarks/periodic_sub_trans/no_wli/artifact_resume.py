from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from rune_decrypter_prime.api import Direction

from tools.benchmarks.periodic_sub_trans.no_wli import (
    replay_phasec_rescue_sweep as phasec_replay_mod,
    stage3_iteration_flow as stage3_flow_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.path_hash_utils import sanitize_jsonable
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_identity import (
    normalize_instance_input_mode,
)
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_outcome import (
    resolve_iteration_outcome,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_rescue_checkpoint import (
    build_phasec_start_checkpoint_path,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_oracle_audit import append_jsonl_row
from tools.benchmarks.periodic_sub_trans.no_wli.run_summary import derive_outcome_code
from tools.benchmarks.periodic_sub_trans.no_wli.runner_utils import key_hash16, mutate_full_key
from tools.benchmarks.periodic_sub_trans.no_wli.scoring_policy import objective_space_key
from tools.benchmarks.periodic_sub_trans.no_wli.stage2_promotion import (
    build_stage3_promoted_keys,
    is_better_stage3_candidate_preserving_solve,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_band_policy import (
    resolve_stage3_gap_and_band,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_metrics import extract_kaeding_metrics
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_policy import (
    evaluate_stage3_entry_policy,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_progress import (
    fmt_finite_float,
    scorer_span_counter_summary,
    solution_span_counter_summary,
    span_counter_delta,
    stage3_progress_logging,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_runtime_calls import (
    Stage3RuntimeCallContext,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_seeding import (
    prepare_stage3_refine_inputs,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_span_summary import (
    summarize_stage3_span,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_topk import (
    append_stage3_topk_from_kaeding,
    append_stage3_topk_from_phasea,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_frontier_rows import (
    load_phasec_frontier_rows,
)
from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_selector_core import (
    normalize_stage35_baseline_selector,
    select_phasec_score_winner_row,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage35_substitution_solver import (
    DEFAULT_STAGE35_SOLVER_CFG,
    run_stage35_live_followup,
)


REPO_ROOT = phasec_replay_mod.REPO_ROOT
OUTPUT_ROOT = REPO_ROOT / "output" / "tools" / "benchmarks" / "periodic_sub_trans" / "no_wli" / "artifact_resume"

DEFAULT_TIER_HEARTBEAT_SECONDS = 60.0
DEFAULT_STAGE3_HEARTBEAT_SECONDS = 30.0
DEFAULT_STAGE3_HEARTBEAT_MIN_STEP = 50
DEFAULT_STAGE3_HEARTBEAT_MIN_ELAPSED_SECONDS = 5.0
DEFAULT_BATCH_EVAL_CHUNK_SIZE = 256
DEFAULT_REQUIRE_BATCH_SCORING = True


@dataclass(frozen=True)
class Stage2ResumeInputs:
    best2_key: list[int]
    best2_pt: list[int]
    best2_score: float
    best2_match: float
    best2_preview: str
    stage2_promoted: list[dict[str, Any]]
    stage2_entry_score: float
    stage2_entry_score_judge: float
    stage2_topk_row_count: int
    stage2_promote_top_cfg: int
    stage2_promoted_from_topk_count: int


def _coerce_stage2_resume_inputs(raw: Mapping[str, Any]) -> Stage2ResumeInputs:
    return Stage2ResumeInputs(
        best2_key=list(map(int, raw.get("best2_key", []) or [])),
        best2_pt=list(map(int, raw.get("best2_pt", []) or [])),
        best2_score=float(raw.get("best2_score", float("nan"))),
        best2_match=float(raw.get("best2_match", float("nan"))),
        best2_preview=str(raw.get("best2_preview", "") or ""),
        stage2_promoted=[dict(row) for row in list(raw.get("stage2_promoted", []) or [])],
        stage2_entry_score=float(raw.get("stage2_entry_score", float("nan"))),
        stage2_entry_score_judge=float(
            raw.get("stage2_entry_score_judge", float("nan"))
        ),
        stage2_topk_row_count=int(raw.get("stage2_topk_row_count", 0) or 0),
        stage2_promote_top_cfg=int(raw.get("stage2_promote_top_cfg", 0) or 0),
        stage2_promoted_from_topk_count=int(
            raw.get("stage2_promoted_from_topk_count", 0) or 0
        ),
    )


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _repo_rel(path: Path) -> str:
    return phasec_replay_mod._repo_rel(path)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _deep_merge_mapping(
    base: Mapping[str, Any],
    override: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = {str(k): v for k, v in dict(base).items()}
    for key, value in dict(override or {}).items():
        key_s = str(key)
        current = merged.get(key_s, None)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            merged[key_s] = _deep_merge_mapping(
                dict(current),
                dict(value),
            )
        else:
            merged[key_s] = value
    return merged


def _resolve_repo_path(path_like: Path | str | None) -> Path | None:
    if path_like is None:
        return None
    path = Path(path_like)
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


def _resolve_repo_relative_scorer_cfg(cfg: Mapping[str, Any] | None) -> dict[str, Any]:
    out = dict(cfg or {})
    for key in (
        "span_hamming_assets_dir",
        "word_ngram_judge_sqlite_path",
        "word_ngram_report_sqlite_path",
        "sqlite_path",
    ):
        resolved = _resolve_repo_path(out.get(key, None))
        if resolved is not None:
            out[key] = str(resolved)
    return out


def _jsonify(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return _repo_rel(value)
    return value


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_jsonify(sanitize_jsonable(dict(payload))), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _truth_match_ratio(
    plaintext_idx: Sequence[int] | np.ndarray,
    target_plaintext_idx: Sequence[int] | np.ndarray,
) -> float:
    lhs = np.asarray(plaintext_idx, dtype=np.uint8).reshape(-1)
    rhs = np.asarray(target_plaintext_idx, dtype=np.uint8).reshape(-1)
    if int(lhs.size) == 0 or int(rhs.size) == 0 or int(lhs.size) != int(rhs.size):
        return float("nan")
    return float(np.mean(lhs == rhs))


def _safe_preview_ascii(
    plaintext_idx: Sequence[int] | np.ndarray,
    _wli: Sequence[Sequence[int]],
    *,
    limit: int = 64,
) -> str:
    arr = np.asarray(plaintext_idx, dtype=np.uint8).reshape(-1)
    return "".join(chr(65 + int(v % 26)) for v in arr[: int(limit)])


def _int_keyed_map(raw: Mapping[str, Any] | None) -> dict[int, Any]:
    out: dict[int, Any] = {}
    for key, value in dict(raw or {}).items():
        try:
            out[int(key)] = value
        except Exception:
            continue
    return out


def _stage1_cfg(run_config: Mapping[str, Any]) -> dict[str, Any]:
    return dict((run_config.get("stage1") or {}) if isinstance(run_config, Mapping) else {})


def _stage2_cfg(run_config: Mapping[str, Any]) -> dict[str, Any]:
    return dict((run_config.get("stage2") or {}) if isinstance(run_config, Mapping) else {})


def _stage3_cfg(run_config: Mapping[str, Any]) -> dict[str, Any]:
    return dict((run_config.get("stage3") or {}) if isinstance(run_config, Mapping) else {})


def _artifacts_cfg(run_config: Mapping[str, Any]) -> dict[str, Any]:
    return dict((run_config.get("artifacts") or {}) if isinstance(run_config, Mapping) else {})


def _phase_experiments_cfg(run_config: Mapping[str, Any]) -> dict[str, Any]:
    return dict(
        (run_config.get("stage3_phase_experiments") or {})
        if isinstance(run_config, Mapping)
        else {}
    )


def _scan_controls_cfg(run_config: Mapping[str, Any]) -> dict[str, Any]:
    return dict(
        (run_config.get("scan_controls") or {})
        if isinstance(run_config, Mapping)
        else {}
    )


def _two_phase_cfg(run_config: Mapping[str, Any]) -> dict[str, Any]:
    return dict((_stage3_cfg(run_config).get("two_phase") or {}))


def _phasec_cfg(run_config: Mapping[str, Any]) -> dict[str, Any]:
    return dict((_two_phase_cfg(run_config).get("phase_c") or {}))


def _span_basin_cfg(run_config: Mapping[str, Any]) -> dict[str, Any]:
    return dict((_stage3_cfg(run_config).get("span_basin_judge") or {}))


def _period_scaling_cfg(run_config: Mapping[str, Any]) -> dict[str, Any]:
    return dict((_stage3_cfg(run_config).get("period_scaling") or {}))


def _c1_focus_cfg(run_config: Mapping[str, Any]) -> dict[str, Any]:
    return dict((_stage3_cfg(run_config).get("c1_focus") or {}))


def _stage35_cfg(run_config: Mapping[str, Any]) -> dict[str, Any]:
    return dict((_stage3_cfg(run_config).get("stage35") or {}))


def _direction_from_artifact(artifact: Mapping[str, Any]) -> Direction:
    return Direction(str(artifact.get("direction", "ltr") or "ltr"))


def _resume_bundle_dir(case: phasec_replay_mod.ArtifactCase) -> Path:
    return case.run_dir / "resume_handoffs" / str(case.artifact_path.stem)


def _phaseb_char_pct_min_dynamic(run_config: Mapping[str, Any]) -> float:
    scorer_cfg = dict((_stage3_cfg(run_config).get("scorer") or {}))
    return float(scorer_cfg.get("span_hamming_char_pct_min", float("nan")))


def _phaseb_char_pct_min_source(run_config: Mapping[str, Any]) -> str:
    experiments = _phase_experiments_cfg(run_config)
    policy = str(experiments.get("phaseB_char_pct_min_policy", "") or "")
    if policy:
        return policy
    return "stage3.scorer.span_hamming_char_pct_min"


def _artifact_identity_fields(artifact: Mapping[str, Any]) -> dict[str, Any]:
    key_seed = int(artifact.get("key_seed", 0) or 0)
    mode = normalize_instance_input_mode(
        str(artifact.get("instance_input_mode", "generated") or "generated")
    )
    instance_fixture_id = str(artifact.get("instance_fixture_id", "") or "").strip()
    instance_source_key_seed_raw = artifact.get("instance_source_key_seed", None)
    search_seed_raw = artifact.get("search_seed", None)
    if mode == "fixed_ciphertext":
        if not instance_fixture_id:
            raise ValueError(
                "fixed_ciphertext artifact missing instance_fixture_id"
            )
        if instance_source_key_seed_raw is None:
            raise ValueError(
                "fixed_ciphertext artifact missing instance_source_key_seed"
            )
        if search_seed_raw is None:
            raise ValueError(
                "fixed_ciphertext artifact missing search_seed"
            )
    return dict(
        instance_input_mode=str(mode),
        instance_fixture_id=str(instance_fixture_id),
        instance_source_key_seed=int(
            instance_source_key_seed_raw
            if instance_source_key_seed_raw is not None
            else key_seed
        ),
        search_seed=int(search_seed_raw if search_seed_raw is not None else key_seed),
    )


def load_artifact_case(*, artifact_path: Path | str) -> phasec_replay_mod.ArtifactCase:
    path = Path(artifact_path)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    run_dir = path.parents[1]
    run_config_path = run_dir / "run_config.json"
    if not run_config_path.exists():
        raise FileNotFoundError(f"Missing run config for artifact: {_repo_rel(path)}")
    return phasec_replay_mod.ArtifactCase(
        artifact_path=path,
        run_dir=run_dir,
        run_config_path=run_config_path,
        artifact=_load_json(path),
        run_config=_load_json(run_config_path),
    )


def reconstruct_stage2_resume_inputs(
    artifact: Mapping[str, Any],
    run_config: Mapping[str, Any],
) -> Stage2ResumeInputs:
    rows = sorted(
        [dict(row) for row in list(artifact.get("stage2_topk", []) or [])],
        key=lambda row: int(row.get("rank", 10**9) or 10**9),
    )
    if not rows:
        raise ValueError("Artifact does not contain saved stage2_topk rows")
    stage1_cfg = _stage1_cfg(run_config)
    scout_cfg = dict(stage1_cfg.get("scout") or {})
    promote_top_cfg = int(max(1, int(scout_cfg.get("promote_top", len(rows)) or len(rows))))

    promoted_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(rows[: int(promote_top_cfg)], start=1):
        key_idx = list(map(int, row.get("key_idx", []) or []))
        plaintext_idx = list(map(int, row.get("plaintext_idx", []) or []))
        if not key_idx:
            continue
        promoted_rows.append(
            dict(
                key=list(key_idx),
                key_idx=list(key_idx),
                plaintext=list(plaintext_idx),
                plaintext_idx=list(plaintext_idx),
                pt=list(plaintext_idx),
                score=float(row.get("score_stage2", float("nan"))),
                judge_score=float(
                    row.get("score_judge", row.get("score_stage2", float("nan")))
                ),
                match=float(row.get("match_ratio", float("nan"))),
                rank=int(row.get("rank", idx) or idx),
                tag="saved_stage2_topk",
                source="stage2_topk_saved",
            )
        )
    if not promoted_rows:
        raise ValueError("Saved stage2_topk rows do not contain any usable keys")
    best_row = dict(promoted_rows[0])
    return Stage2ResumeInputs(
        best2_key=list(best_row["key"]),
        best2_pt=list(best_row.get("plaintext_idx", []) or []),
        best2_score=float(best_row.get("score", float("nan"))),
        best2_match=float(best_row.get("match", float("nan"))),
        best2_preview=str(
            _safe_preview_ascii(
                best_row.get("plaintext_idx", []),
                [],
            )
        ),
        stage2_promoted=[dict(row) for row in promoted_rows],
        stage2_entry_score=float(best_row.get("score", float("nan"))),
        stage2_entry_score_judge=float(best_row.get("judge_score", float("nan"))),
        stage2_topk_row_count=int(len(rows)),
        stage2_promote_top_cfg=int(promote_top_cfg),
        stage2_promoted_from_topk_count=int(len(promoted_rows)),
    )


def _build_stage3_prep_from_stage2_resume(
    *,
    resume: Stage2ResumeInputs,
    artifact: Mapping[str, Any],
    run_config: Mapping[str, Any],
) -> dict[str, Any]:
    stage2_cfg = _stage2_cfg(run_config)
    stage3_cfg = _stage3_cfg(run_config)
    stage3_entry_cfg = dict(stage3_cfg.get("entry") or {})
    judge_pool_cfg = dict(stage2_cfg.get("judge_pool") or {})
    two_phase_cfg = _two_phase_cfg(run_config)
    period_scaling_cfg = _period_scaling_cfg(run_config)
    c1_focus_cfg = _c1_focus_cfg(run_config)
    prep = prepare_stage3_refine_inputs(
        tier_period=int(artifact.get("period", 0) or 0),
        tier_columns=int(artifact.get("columns", 0) or 0),
        key_len=int(len(resume.best2_key)),
        key_seed=int(artifact.get("key_seed", 0) or 0),
        best2_key=resume.best2_key,
        best2_match=float(resume.best2_match),
        stage2_promoted=list(resume.stage2_promoted),
        stage2_entry_score=float(resume.stage2_entry_score),
        stage2_entry_score_judge=float(resume.stage2_entry_score_judge),
        scorer_stage2=dict(stage2_cfg.get("scorer") or {}),
        scorer_full=dict(stage3_cfg.get("scorer") or {}),
        stage3_dynamic_bands=list(stage3_cfg.get("dynamic_bands", []) or []),
        oracle_s3=float(
            (artifact.get("oracle_scores", {}) or {}).get("stage3", float("nan"))
        ),
        oracle_decision_paths_enabled=bool(
            run_config.get("oracle_decision_paths_enabled", False)
        ),
        stage2_entry_band_by_stage3_judge=bool(
            judge_pool_cfg.get("entry_band_by_stage3_judge", False)
        ),
        stage3_c1_focus_enabled_cfg=bool(c1_focus_cfg.get("enabled", False)),
        stage3_c1_init_keys=int(c1_focus_cfg.get("init_keys", 0) or 0),
        stage3_initial_keys=int(stage3_cfg.get("init_keys", 1) or 1),
        stage3_initial_keys_by_columns=_int_keyed_map(
            stage3_cfg.get("init_keys_by_columns", {})
        ),
        stage3_period_init_mult_by_period=_int_keyed_map(
            period_scaling_cfg.get("init_mult_by_period", {})
        ),
        stage3_period_step_mult_by_period=_int_keyed_map(
            period_scaling_cfg.get("step_mult_by_period", {})
        ),
        stage3_period_restart_bonus_by_period=_int_keyed_map(
            period_scaling_cfg.get("restart_bonus_by_period", {})
        ),
        stage3_init_keys_cap=int(period_scaling_cfg.get("init_keys_cap", 0) or 0),
        stage3_phasea_cfg=dict(two_phase_cfg.get("phase_a") or {}),
        stage3_phaseb_cfg=dict(two_phase_cfg.get("phase_b") or {}),
        stage3_phaseb_top_n=int(two_phase_cfg.get("phase_b_top_n", 1) or 1),
        stage3_phaseb_gate_delta_floor=float(
            two_phase_cfg.get("gate_delta_floor", 0.0) or 0.0
        ),
        stage3_phaseb_gate_end_gain_floor=float(
            two_phase_cfg.get("gate_end_gain_floor", 0.0) or 0.0
        ),
        stage3_c1_phasea_steps=int(c1_focus_cfg.get("phase_a_steps", 0) or 0),
        stage3_c1_phaseb_steps=int(c1_focus_cfg.get("phase_b_steps", 0) or 0),
        stage3_c1_phaseb_top_n=int(c1_focus_cfg.get("phase_b_top_n", 0) or 0),
        stage3_c1_phaseb_gate_delta_floor=float(
            c1_focus_cfg.get("gate_delta_floor", 0.0) or 0.0
        ),
        stage3_c1_phaseb_gate_end_gain_floor=float(
            c1_focus_cfg.get("gate_end_gain_floor", 0.0) or 0.0
        ),
        solver_stage3_cfg=dict(stage3_cfg.get("solver") or {}),
        stage3_entry_allocation_policy=str(
            stage3_entry_cfg.get("allocation_policy", "legacy_fixed_budget")
        ),
        stage3_entry_mutations_per_promoted=int(
            stage3_entry_cfg.get("mutations_per_promoted", 1) or 1
        ),
        build_stage3_promoted_keys_fn=build_stage3_promoted_keys,
        mutate_full_key_fn=lambda seed_key, period, columns, seed, n: mutate_full_key(
            seed_key,
            period=int(period),
            columns=int(columns),
            seed=int(seed),
            n=int(n),
            alphabet_size=int(artifact.get("alphabet_size", 0) or 0),
        ),
        objective_space_key_fn=objective_space_key,
        resolve_stage3_gap_and_band_fn=resolve_stage3_gap_and_band,
    )
    return dict(prep)


def prepare_stage3_resume_inputs(
    artifact: Mapping[str, Any],
    run_config: Mapping[str, Any],
) -> dict[str, Any]:
    resume = reconstruct_stage2_resume_inputs(artifact, run_config)
    prep = _build_stage3_prep_from_stage2_resume(
        resume=resume,
        artifact=artifact,
        run_config=run_config,
    )
    return dict(
        stage2_resume=resume,
        stage3_prep=dict(prep),
        resume_source="reconstructed_stage2_topk",
    )


def load_saved_stage3_resume_bundle(
    case: phasec_replay_mod.ArtifactCase,
) -> dict[str, Any] | None:
    bundle_dir = _resume_bundle_dir(case)
    stage2_resume_path = bundle_dir / "stage2_resume.json"
    if not stage2_resume_path.exists():
        return None
    stage2_resume_raw = _load_json(stage2_resume_path)
    stage2_resume = _coerce_stage2_resume_inputs(stage2_resume_raw)
    stage3_prep_path = bundle_dir / "stage3_prep.json"
    stage3_prep = (
        dict(_load_json(stage3_prep_path))
        if stage3_prep_path.exists()
        else None
    )
    return dict(
        bundle_dir=bundle_dir,
        stage2_resume=stage2_resume,
        stage3_prep=stage3_prep,
    )


def prepare_stage3_resume_inputs_from_case(
    case: phasec_replay_mod.ArtifactCase,
    run_config: Mapping[str, Any],
    *,
    prefer_saved_stage3_prep: bool,
) -> dict[str, Any]:
    saved_bundle = load_saved_stage3_resume_bundle(case)
    artifact = dict(case.artifact)
    if saved_bundle is None:
        return prepare_stage3_resume_inputs(artifact, run_config)
    resume = saved_bundle["stage2_resume"]
    saved_prep = dict(saved_bundle.get("stage3_prep", {}) or {})
    if bool(prefer_saved_stage3_prep) and bool(saved_prep):
        prep = dict(saved_prep)
        resume_source = "saved_live_bundle"
    else:
        prep = _build_stage3_prep_from_stage2_resume(
            resume=resume,
            artifact=artifact,
            run_config=run_config,
        )
        resume_source = "saved_live_stage2_resume_rebuilt_prep"
    return dict(
        stage2_resume=resume,
        stage3_prep=dict(prep),
        resume_source=str(resume_source),
        bundle_dir_relpath=_repo_rel(Path(saved_bundle["bundle_dir"])),
    )


def _build_stage3_runtime_call_context(
    artifact: Mapping[str, Any],
    run_config: Mapping[str, Any],
    *,
    output_dir: Path,
) -> Stage3RuntimeCallContext:
    artifacts_cfg = _artifacts_cfg(run_config)
    span_basin_cfg = _span_basin_cfg(run_config)
    phasec_cfg = _phasec_cfg(run_config)
    two_phase_cfg = _two_phase_cfg(run_config)
    phaseb_family_cfg = dict(two_phase_cfg.get("family_preservation") or {})
    if not phaseb_family_cfg:
        phaseb_family_cfg = dict((two_phase_cfg.get("phase_b_family_preservation") or {}))
    return Stage3RuntimeCallContext(
        order=str(artifact.get("order", "col_then_sub") or "col_then_sub"),
        alphabet_size=int(artifact.get("alphabet_size", 0) or 0),
        batch_eval_chunk_size=int(DEFAULT_BATCH_EVAL_CHUNK_SIZE),
        require_batch_scoring=bool(DEFAULT_REQUIRE_BATCH_SCORING),
        solve_match_threshold=float(run_config.get("threshold", 0.9) or 0.9),
        stage3_continue_after_solve=bool(
            two_phase_cfg.get("continue_after_solve", False)
        ),
        stage3_heartbeat_seconds=float(DEFAULT_STAGE3_HEARTBEAT_SECONDS),
        stage3_heartbeat_min_step=int(DEFAULT_STAGE3_HEARTBEAT_MIN_STEP),
        stage3_heartbeat_min_elapsed_seconds=float(
            DEFAULT_STAGE3_HEARTBEAT_MIN_ELAPSED_SECONDS
        ),
        stage3_span_basin_judge_require_span_active=bool(
            span_basin_cfg.get("require_span_active", True)
        ),
        stage3_span_basin_judge_dedupe_by_end_hash=bool(
            span_basin_cfg.get("dedupe_by_end_hash", True)
        ),
        stage3_span_basin_judge_tie_eps=float(span_basin_cfg.get("tie_eps", 0.0) or 0.0),
        stage3_span_basin_judge_tie_max_seeds=int(
            span_basin_cfg.get("tie_max_seeds", 0) or 0
        ),
        stage3_word_ngram_decision_influence=bool(
            dict((_stage3_cfg(run_config).get("word_ngram_report") or {})).get(
                "decision_influence",
                False,
            )
        ),
        stage3_phasec_enabled=bool(phasec_cfg.get("enabled", False)),
        stage3_phasec_cfg=dict(phasec_cfg.get("cfg") or {}),
        stage3_phasec_start_keys=int(phasec_cfg.get("start_keys", 0) or 0),
        stage3_phasec_seed_offset=int(phasec_cfg.get("seed_offset", 0) or 0),
        stage3_phasec_word_ngram_tiebreak=bool(
            phasec_cfg.get("word_ngram_tiebreak", False)
        ),
        stage3_phaseb_family_preservation_policy=str(
            phaseb_family_cfg.get("policy", "off") or "off"
        ).strip().lower(),
        stage3_phaseb_family_view_id=str(
            phaseb_family_cfg.get("family_view_id", "prefix_hamming_le_24")
            or "prefix_hamming_le_24"
        ).strip().lower(),
        stage3_phaseb_family_reserved_slots=int(
            phaseb_family_cfg.get("reserved_slots", 0) or 0
        ),
        stage3_phasec_start_policy=str(
            phasec_cfg.get("start_policy", "source_order") or "source_order"
        ).strip().lower(),
        extract_kaeding_metrics_fn=extract_kaeding_metrics,
        solution_span_counter_summary_fn=solution_span_counter_summary,
        stage3_progress_logging_fn=stage3_progress_logging,
        match_ratio_fn=_truth_match_ratio,
        key_hash_fn=key_hash16,
        append_stage3_topk_from_phasea_fn=lambda **kwargs: append_stage3_topk_from_phasea(
            payload=kwargs["payload"],
            rows=kwargs["rows"],
            save_enabled=bool(artifacts_cfg.get("stage3_topk_enabled", False)),
            save_limit=int(artifacts_cfg.get("stage3_topk", 0) or 0),
            key_len=int(kwargs["key_len"]),
        ),
        append_stage3_topk_from_kaeding_fn=lambda **kwargs: append_stage3_topk_from_kaeding(
            payload=kwargs["payload"],
            kaeding_obj=kwargs["kaeding_obj"],
            save_enabled=bool(artifacts_cfg.get("stage3_topk_enabled", False)),
            save_limit=int(artifacts_cfg.get("stage3_topk", 0) or 0),
            key_len=int(kwargs["key_len"]),
            full_cipher=kwargs["full_cipher"],
            ciphertext=np.asarray(kwargs["ciphertext"], dtype=np.uint8),
            scorer_full_runtime=kwargs["scorer_full_runtime"],
            batch_eval_chunk_size=int(DEFAULT_BATCH_EVAL_CHUNK_SIZE),
            require_batch_scoring=bool(DEFAULT_REQUIRE_BATCH_SCORING),
            match_ratio_fn=_truth_match_ratio,
            target_plaintext=np.asarray(kwargs["target_plaintext"], dtype=np.uint8),
            key_hash_fn=key_hash16,
        ),
        is_better_stage3_candidate_preserving_solve_fn=lambda cand_score, cand_match, best_score, best_match, *, score_first: is_better_stage3_candidate_preserving_solve(
            cand_score=float(cand_score),
            cand_match=float(cand_match),
            best_score=float(best_score),
            best_match=float(best_match),
            solve_threshold=float(run_config.get("threshold", 0.9) or 0.9),
            score_first=bool(score_first),
        ),
        scorer_span_counter_summary_fn=scorer_span_counter_summary,
        span_counter_delta_fn=span_counter_delta,
        fmt_finite_float_fn=fmt_finite_float,
        phasec_start_checkpoint_path=build_phasec_start_checkpoint_path(run_dir=output_dir),
        append_jsonl_row_fn=lambda path, row: append_jsonl_row(
            path=path,
            row=row,
            sanitize_jsonable_fn=sanitize_jsonable,
        ),
        log_prefix="[artifact_resume]",
    )


def run_stage35_resume_from_artifact(
    case: phasec_replay_mod.ArtifactCase,
    *,
    run_config_override: Mapping[str, Any] | None = None,
    stage35_cfg_override: Mapping[str, Any] | None = None,
    batch_eval_chunk_size: int | None = None,
) -> dict[str, Any]:
    artifact = dict(case.artifact)
    run_config = _deep_merge_mapping(dict(case.run_config), run_config_override)
    phasec_frontier_rows = load_phasec_frontier_rows(
        artifact_path=case.artifact_path,
        artifact=artifact,
    )
    stage35_cfg = dict(
        (_stage35_cfg(run_config).get("cfg") or DEFAULT_STAGE35_SOLVER_CFG)
    )
    if stage35_cfg_override is not None:
        stage35_cfg.update({str(k): v for k, v in dict(stage35_cfg_override).items()})

    out = run_stage35_live_followup(
        period=int(artifact.get("period", 0) or 0),
        columns=int(artifact.get("columns", 0) or 0),
        alphabet_size=int(artifact.get("alphabet_size", 0) or 0),
        ciphertext_idx=np.asarray(artifact.get("ciphertext_idx", []), dtype=np.uint8).reshape(-1),
        baseline_key=list(map(int, artifact.get("final_best_key_idx", []) or [])),
        baseline_plaintext_idx=list(
            map(int, artifact.get("final_best_plaintext_idx", []) or [])
        ),
        baseline_score=float(artifact.get("best_score", float("nan"))),
        stage3_topk_rows=list(artifact.get("stage3_topk", []) or []),
        phasec_start_summaries=list(phasec_frontier_rows),
        phasec_final_winner_lane=str(
            dict(artifact.get("stage3_diagnostics", {}) or {}).get(
                "phaseC_final_winner_lane",
                "",
            )
            or ""
        ),
        phasec_final_winner_source=str(
            dict(artifact.get("stage3_diagnostics", {}) or {}).get(
                "phaseC_final_winner_source",
                "",
            )
            or ""
        ),
        cipher=phasec_replay_mod._build_cipher(artifact),
        scorer_full=phasec_replay_mod._build_stage3_scorer_runtime(
            artifact=artifact,
            run_config=run_config,
            scorer_key="scorer",
        ),
        scorer_search=phasec_replay_mod._build_stage3_scorer_runtime(
            artifact=artifact,
            run_config=run_config,
            scorer_key="search_scorer",
        ),
        cfg=stage35_cfg,
        chunk_size=int(batch_eval_chunk_size or DEFAULT_BATCH_EVAL_CHUNK_SIZE),
        require_batch=bool(DEFAULT_REQUIRE_BATCH_SCORING),
    )
    resume_match = _truth_match_ratio(
        out.get("best_plaintext_idx", []) or [],
        artifact.get("target_plaintext_idx", []) or [],
    )
    return dict(
        mode="stage3_to_stage35",
        artifact_relpath=_repo_rel(case.artifact_path),
        run_config_relpath=_repo_rel(case.run_config_path),
        **_artifact_identity_fields(artifact),
        run_config_override=dict(run_config_override or {}),
        baseline_best_match_ratio=float(artifact.get("best_match_ratio", float("nan"))),
        resume_best_match_ratio=float(resume_match),
        resume_best_score=float(out.get("best_score", float("nan"))),
        stage35_cfg=dict(stage35_cfg),
        stage35=dict(out),
    )


def run_stage35_from_selected_trial_row(
    case: phasec_replay_mod.ArtifactCase,
    *,
    selected_row: Mapping[str, Any],
    stage35_cfg_override: Mapping[str, Any] | None = None,
    batch_eval_chunk_size: int | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    artifact = dict(case.artifact)
    run_config = dict(case.run_config)
    phasec_frontier_rows = load_phasec_frontier_rows(
        artifact_path=case.artifact_path,
        artifact=artifact,
    )
    stage35_cfg = dict(
        (_stage35_cfg(run_config).get("cfg") or DEFAULT_STAGE35_SOLVER_CFG)
    )
    if stage35_cfg_override is not None:
        stage35_cfg.update({str(k): v for k, v in dict(stage35_cfg_override).items()})

    baseline_key = list(map(int, selected_row.get("final_key_idx", []) or []))
    baseline_plaintext_idx = list(
        map(int, selected_row.get("final_plaintext_idx", []) or [])
    )
    if not baseline_key:
        raise ValueError("Selected trial row is missing final_key_idx")
    if not baseline_plaintext_idx:
        raise ValueError("Selected trial row is missing final_plaintext_idx")
    baseline_score = float(selected_row.get("final_score", float("nan")))
    baseline_truth_match = _truth_match_ratio(
        baseline_plaintext_idx,
        artifact.get("target_plaintext_idx", []) or [],
    )
    baseline_selector = normalize_stage35_baseline_selector(
        str(selected_row.get("selector", "") or "legacy")
    )
    phasec_score_winner_summary_row = select_phasec_score_winner_row(
        phasec_start_summaries=list(phasec_frontier_rows),
        best3_key=list(map(int, artifact.get("final_best_key_idx", []) or [])),
        phasec_final_winner_lane=str(
            dict(artifact.get("stage3_diagnostics", {}) or {}).get(
                "phaseC_final_winner_lane",
                "",
            )
            or ""
        ),
        phasec_final_winner_source=str(
            dict(artifact.get("stage3_diagnostics", {}) or {}).get(
                "phaseC_final_winner_source",
                "",
            )
            or ""
        ),
    )
    partial_state_path: Path | None = None
    progress_jsonl_path: Path | None = None
    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        partial_state_path = output_dir / "stage35_partial_state.json"
        progress_jsonl_path = output_dir / "stage35_progress.jsonl"

    out = run_stage35_live_followup(
        period=int(artifact.get("period", 0) or 0),
        columns=int(artifact.get("columns", 0) or 0),
        alphabet_size=int(artifact.get("alphabet_size", 0) or 0),
        ciphertext_idx=np.asarray(artifact.get("ciphertext_idx", []), dtype=np.uint8).reshape(-1),
        baseline_key=list(baseline_key),
        baseline_plaintext_idx=list(baseline_plaintext_idx),
        baseline_score=float(baseline_score),
        baseline_selector=str(baseline_selector),
        baseline_summary_row=dict(selected_row),
        phasec_score_winner_summary_row=dict(phasec_score_winner_summary_row),
        stage3_topk_rows=list(artifact.get("stage3_topk", []) or []),
        phasec_start_summaries=list(phasec_frontier_rows),
        phasec_final_winner_lane=str(
            dict(artifact.get("stage3_diagnostics", {}) or {}).get(
                "phaseC_final_winner_lane",
                "",
            )
            or ""
        ),
        phasec_final_winner_source=str(
            dict(artifact.get("stage3_diagnostics", {}) or {}).get(
                "phaseC_final_winner_source",
                "",
            )
            or ""
        ),
        cipher=phasec_replay_mod._build_cipher(artifact),
        scorer_full=phasec_replay_mod._build_stage3_scorer_runtime(
            artifact=artifact,
            run_config=run_config,
            scorer_key="scorer",
        ),
        scorer_search=phasec_replay_mod._build_stage3_scorer_runtime(
            artifact=artifact,
            run_config=run_config,
            scorer_key="search_scorer",
        ),
        cfg=stage35_cfg,
        chunk_size=int(batch_eval_chunk_size or DEFAULT_BATCH_EVAL_CHUNK_SIZE),
        require_batch=bool(DEFAULT_REQUIRE_BATCH_SCORING),
        partial_state_path=partial_state_path,
        progress_jsonl_path=progress_jsonl_path,
        append_jsonl_row_fn=lambda path, row: append_jsonl_row(
            path=path,
            row=row,
            sanitize_jsonable_fn=sanitize_jsonable,
        ),
    )
    partial_state_name = str(
        out.get("partial_state_path_name", "")
        or (partial_state_path.name if partial_state_path is not None else "")
    )
    progress_jsonl_name = str(
        out.get("progress_jsonl_path_name", "")
        or (progress_jsonl_path.name if progress_jsonl_path is not None else "")
    )
    resume_match = _truth_match_ratio(
        out.get("best_plaintext_idx", []) or [],
        artifact.get("target_plaintext_idx", []) or [],
    )
    return dict(
        mode="selected_stage3_to_stage35",
        artifact_relpath=_repo_rel(case.artifact_path),
        run_config_relpath=_repo_rel(case.run_config_path),
        **_artifact_identity_fields(artifact),
        selector=str(selected_row.get("selector", "") or ""),
        fixture_id=str(selected_row.get("fixture_id", "") or ""),
        fixture_label=str(selected_row.get("fixture_label", "") or ""),
        selected_candidate_hash=str(selected_row.get("candidate_hash", "") or ""),
        selected_candidate_source=str(selected_row.get("source", "") or ""),
        selected_candidate_lane=str(selected_row.get("lane", "") or ""),
        selected_candidate_final_score=float(baseline_score),
        selected_candidate_final_match=float(baseline_truth_match),
        replay_material_complete=int(
            selected_row.get("replay_material_complete", 0) or 0
        ),
        output_dir_relpath=(
            _repo_rel(output_dir) if output_dir is not None else ""
        ),
        stage35_partial_state_relpath=(
            _repo_rel(output_dir / partial_state_name)
            if output_dir is not None
            and partial_state_name
            else ""
        ),
        stage35_progress_jsonl_relpath=(
            _repo_rel(output_dir / progress_jsonl_name)
            if output_dir is not None
            and progress_jsonl_name
            else ""
        ),
        resume_best_match_ratio=float(resume_match),
        resume_best_score=float(out.get("best_score", float("nan"))),
        stage35_cfg=dict(stage35_cfg),
        stage35=dict(out),
    )


def run_stage3_resume_from_artifact(
    case: phasec_replay_mod.ArtifactCase,
    *,
    output_dir: Path,
    run_config_override: Mapping[str, Any] | None = None,
    enable_stage35: bool | None = None,
    stage35_cfg_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = dict(case.artifact)
    run_config = _deep_merge_mapping(dict(case.run_config), run_config_override)
    prep_payload = prepare_stage3_resume_inputs_from_case(
        case,
        run_config,
        prefer_saved_stage3_prep=not bool(dict(run_config_override or {})),
    )
    stage2_resume = prep_payload["stage2_resume"]
    stage3_prep = dict(prep_payload["stage3_prep"])
    stage3_cfg = _stage3_cfg(run_config)
    phase_experiments_cfg = _phase_experiments_cfg(run_config)
    two_phase_cfg = _two_phase_cfg(run_config)
    scan_controls_cfg = _scan_controls_cfg(run_config)
    stage35_cfg = dict(
        (_stage35_cfg(run_config).get("cfg") or DEFAULT_STAGE35_SOLVER_CFG)
    )
    if stage35_cfg_override is not None:
        stage35_cfg.update({str(k): v for k, v in dict(stage35_cfg_override).items()})
    effective_stage35_enabled = (
        bool(enable_stage35)
        if enable_stage35 is not None
        else bool((_stage35_cfg(run_config).get("enabled", False)))
    )

    target_plaintext_idx = np.asarray(
        artifact.get("target_plaintext_idx", []),
        dtype=np.uint8,
    ).reshape(-1)
    direction = _direction_from_artifact(artifact)
    full_cipher = phasec_replay_mod._build_cipher(artifact)
    scorer_full_runtime = phasec_replay_mod._build_stage3_scorer_runtime(
        artifact=artifact,
        run_config=run_config,
        scorer_key="scorer",
    )
    scorer_search_runtime = phasec_replay_mod._build_stage3_scorer_runtime(
        artifact=artifact,
        run_config=run_config,
        scorer_key="search_scorer",
    )
    scorer_judge_runtime = phasec_replay_mod._build_stage3_scorer_runtime(
        artifact=artifact,
        run_config=run_config,
        scorer_key="judge_scorer",
    )
    scorer_word_ngram_report_runtime = phasec_replay_mod._build_stage3_word_ngram_report_runtime(
        artifact=artifact,
        run_config=run_config,
    )

    tier = SimpleNamespace(
        name=str(artifact.get("tier", case.artifact_path.stem)),
        period=int(artifact.get("period", 0) or 0),
        columns=int(artifact.get("columns", 0) or 0),
        length=int(artifact.get("length", 0) or 0),
    )
    stage3_ctx = _build_stage3_runtime_call_context(
        artifact,
        run_config,
        output_dir=output_dir,
    )

    flow_start = time.time()
    flow = stage3_flow_mod.run_stage3_iteration_flow(
        state=dict(
            tier=tier,
            text_id=int(artifact.get("text_id", 0) or 0),
            key_seed=int(artifact.get("key_seed", 0) or 0),
            t0_i=float(flow_start),
            key_len=int(len(stage2_resume.best2_key)),
            best2_match=float(stage2_resume.best2_match),
            best2_key=list(stage2_resume.best2_key),
            stage2_promoted=[dict(row) for row in list(stage2_resume.stage2_promoted)],
            stage2_entry_score=float(stage2_resume.stage2_entry_score),
            stage2_entry_score_judge=float(stage2_resume.stage2_entry_score_judge),
            scorer_stage2=_resolve_repo_relative_scorer_cfg(
                (_stage2_cfg(run_config).get("scorer") or {})
            ),
            scorer_full=_resolve_repo_relative_scorer_cfg(
                (stage3_cfg.get("scorer") or {})
            ),
            oracle_s3=float(
                (artifact.get("oracle_scores", {}) or {}).get("stage3", float("nan"))
            ),
            oracle_decision_paths_enabled=bool(
                run_config.get("oracle_decision_paths_enabled", False)
            ),
            ct_idx=np.asarray(artifact.get("ciphertext_idx", []), dtype=np.uint8).reshape(-1),
            pt_idx=target_plaintext_idx,
            wli=[],
            direction=direction,
            scorer_stage3_phaseA=_resolve_repo_relative_scorer_cfg(
                stage3_cfg.get("search_scorer") or stage3_cfg.get("scorer") or {}
            ),
            scorer_stage3_phaseB=_resolve_repo_relative_scorer_cfg(
                stage3_cfg.get("scorer") or {}
            ),
            scorer_stage3_phaseA_runtime=scorer_search_runtime,
            scorer_stage3_search_runtime=scorer_search_runtime,
            scorer_basin_judge_runtime=scorer_judge_runtime,
            scorer_word_ngram_report_runtime=scorer_word_ngram_report_runtime,
            scorer_full_runtime=scorer_full_runtime,
            full_cipher=full_cipher,
            stage2_evals_total=int(stage2_resume.stage2_topk_row_count),
            stage2_continue_to_gate=False,
            stage2_continue_stop_reason="",
            stage3_phaseA_experiment=str(phase_experiments_cfg.get("phaseA", "resume")),
            stage3_phaseB_experiment=str(phase_experiments_cfg.get("phaseB", "resume")),
            stage3_phaseB_char_pct_min_dynamic=float(
                _phaseb_char_pct_min_dynamic(run_config)
            ),
            stage3_phaseB_char_pct_min_source=str(
                _phaseb_char_pct_min_source(run_config)
            ),
            oracle_assist_selection_effective=bool(
                run_config.get("oracle_assist_selection_effective", False)
            ),
            stages=[],
            STAGE35_ENABLED=bool(effective_stage35_enabled),
            STAGE35_CFG=dict(stage35_cfg),
        ),
        stage3_runtime_call_ctx=stage3_ctx,
        stage3_two_phase_enabled=bool(two_phase_cfg.get("enabled", False)),
        stage3_continue_after_solve=bool(two_phase_cfg.get("continue_after_solve", False)),
        stage3_phasea_cfg_default=dict(two_phase_cfg.get("phase_a") or {}),
        stage3_phaseb_cfg_default=dict(two_phase_cfg.get("phase_b") or {}),
        stage3_phaseb_top_n_default=int(two_phase_cfg.get("phase_b_top_n", 1) or 1),
        stage3_phaseb_gate_delta_floor_default=float(
            two_phase_cfg.get("gate_delta_floor", 0.0) or 0.0
        ),
        stage3_phaseb_gate_end_gain_floor_default=float(
            two_phase_cfg.get("gate_end_gain_floor", 0.0) or 0.0
        ),
        solver_stage3_default_cfg=dict(stage3_cfg.get("solver") or {}),
        stage3_span_basin_judge_k=int(
            _span_basin_cfg(run_config).get("k", 0) or 0
        ),
        tier_heartbeat_seconds=float(DEFAULT_TIER_HEARTBEAT_SECONDS),
        solve_match_threshold=float(run_config.get("threshold", 0.9) or 0.9),
        stall_delta=float(run_config.get("stall_delta", 0.0) or 0.0),
        stall_stage_limit=int(run_config.get("stall_stage_limit", 1) or 1),
        evaluate_stage3_entry_policy_fn=lambda **kwargs: evaluate_stage3_entry_policy(
            tier_name=str(kwargs["tier"].name),
            text_id=int(kwargs["text_id"]),
            key_seed=int(kwargs["key_seed"]),
            best2_match=float(kwargs["best2_match"]),
            solve_match_threshold=float(run_config.get("threshold", 0.9) or 0.9),
            scan_mode_active=bool(run_config.get("stage3_can_skip", False)),
            scan_time_cap_seconds=float(
                scan_controls_cfg.get("tier_time_cap_seconds", 0.0) or 0.0
            ),
            tier_elapsed_before_stage3=float(kwargs["tier_elapsed_before_stage3"]),
            scan_stage3_gate_low_match=float(
                scan_controls_cfg.get("stage3_gate_low_match", 0.0) or 0.0
            ),
            scan_stage3_gate_high_match=float(
                scan_controls_cfg.get("stage3_gate_high_match", 0.0) or 0.0
            ),
            stage2_continue_to_gate=bool(kwargs["stage2_continue_to_gate"]),
            stage2_continue_stop_reason=str(kwargs["stage2_continue_stop_reason"]),
            stages=kwargs["stages"],
            log_prefix="[artifact_resume]",
        ),
        prepare_stage3_refine_inputs_fn=lambda **_kwargs: dict(stage3_prep),
        summarize_stage3_span_fn=summarize_stage3_span,
        mark_oracle_decision_use_fn=lambda: None,
        print_stage_preview_fn=lambda **_kwargs: None,
        fmt_finite_float_fn=fmt_finite_float,
        log_prefix="[artifact_resume]",
    )

    dt_i = float(time.time() - float(flow_start))
    pt3 = np.asarray(flow.get("pt3", []), dtype=np.uint8).reshape(-1)
    if int(flow.get("stage35_selected", 0) or 0) == 1:
        resume_best_stage = "stage35_substitution_only"
        resume_best_match_ratio = _truth_match_ratio(
            flow.get("stage35_best_plaintext_idx", []) or [],
            target_plaintext_idx,
        )
        resume_best_score = float(flow.get("stage35_best_score", float("nan")))
    elif flow.get("best3_key") is not None and int(pt3.size) > 0:
        resume_best_stage = "stage3_full_refine"
        resume_best_match_ratio = float(flow.get("best3_match", float("nan")))
        resume_best_score = float(flow.get("best3_score", float("nan")))
    else:
        resume_best_stage = "no_stage3_candidate"
        resume_best_match_ratio = float("nan")
        resume_best_score = float("nan")

    outcome = dict(
        resolve_iteration_outcome(
            stop_reason=str(flow.get("stop_reason", "")),
            solve_match_threshold=float(run_config.get("threshold", 0.9) or 0.9),
            dt_i=float(dt_i),
            ev1=0,
            stage2_evals_total=int(stage2_resume.stage2_topk_row_count),
            ev3=int(flow.get("ev3", 0) or 0),
            best2_match=float(stage2_resume.best2_match),
            best2_score=float(stage2_resume.best2_score),
            best2_key=list(stage2_resume.best2_key),
            best2_pt=list(stage2_resume.best2_pt),
            best2_preview=str(stage2_resume.best2_preview),
            best3_match=float(flow.get("best3_match", float("nan"))),
            best3_score=float(flow.get("best3_score", float("nan"))),
            best3_key=flow.get("best3_key"),
            pt3=pt3,
            target_plaintext_idx=target_plaintext_idx,
            stage35_selected=bool(flow.get("stage35_selected", 0)),
            stage35_best_score=float(flow.get("stage35_best_score", float("nan"))),
            stage35_best_key=flow.get("stage35_best_key"),
            stage35_best_plaintext_idx=flow.get("stage35_best_plaintext_idx"),
            wli=[],
            stage1_best_score=float("nan"),
            oracle_s1=float("nan"),
            oracle_s2=float("nan"),
            oracle_s3=float(
                (artifact.get("oracle_scores", {}) or {}).get("stage3", float("nan"))
            ),
            derive_outcome_code_fn=derive_outcome_code,
            safe_preview_latin_fn=_safe_preview_ascii,
        )
    )
    return dict(
        mode="stage2_to_stage3",
        artifact_relpath=_repo_rel(case.artifact_path),
        run_config_relpath=_repo_rel(case.run_config_path),
        **_artifact_identity_fields(artifact),
        output_dir=_repo_rel(output_dir),
        run_config_override=dict(run_config_override or {}),
        resume_source=str(prep_payload.get("resume_source", "")),
        bundle_dir_relpath=str(prep_payload.get("bundle_dir_relpath", "") or ""),
        stage2_resume=dict(stage2_resume.__dict__),
        stage3_prep=dict(stage3_prep),
        stage3_flow=_jsonify(flow),
        outcome=_jsonify(outcome),
        stage35_enabled_effective=int(1 if bool(effective_stage35_enabled) else 0),
        stage35_cfg=dict(stage35_cfg),
        resume_best_stage=str(resume_best_stage),
        resume_best_match_ratio=float(resume_best_match_ratio),
        resume_best_score=float(resume_best_score),
    )


def make_resume_output_dir(
    case: phasec_replay_mod.ArtifactCase,
    *,
    mode: str,
) -> Path:
    stem = str(case.artifact_path.stem)
    label = f"{_utc_label()}_{str(mode)}_{str(case.run_dir.name)}_{stem}"
    return OUTPUT_ROOT / label


def write_resume_bundle(payload: Mapping[str, Any], *, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "summary.json", dict(payload))
    mode = str(payload.get("mode", "") or "")
    if mode == "stage2_to_stage3":
        _write_json(
            output_dir / "stage2_resume.json",
            dict(payload.get("stage2_resume", {}) or {}),
        )
        _write_json(
            output_dir / "stage3_prep.json",
            dict(payload.get("stage3_prep", {}) or {}),
        )
        _write_json(
            output_dir / "stage3_flow.json",
            dict(payload.get("stage3_flow", {}) or {}),
        )
        _write_json(
            output_dir / "outcome.json",
            dict(payload.get("outcome", {}) or {}),
        )
    elif mode in {"stage3_to_stage35", "selected_stage3_to_stage35"}:
        stage35_payload = dict(payload.get("stage35", {}) or {})
        _write_json(output_dir / "stage35_summary.json", stage35_payload)
        _write_json(
            output_dir / "stage35_archive.json",
            dict(archive_rows=list(stage35_payload.get("archive_rows", []) or [])),
        )
        _write_json(
            output_dir / "stage35_seed_rows.json",
            dict(seed_rows_scored=list(stage35_payload.get("seed_rows_scored", []) or [])),
        )
        if mode == "selected_stage3_to_stage35":
            identity_fields = _artifact_identity_fields(payload)
            _write_json(
                output_dir / "selected_trial_row_summary.json",
                dict(
                    **identity_fields,
                    selector=str(payload.get("selector", "") or ""),
                    fixture_id=str(payload.get("fixture_id", "") or ""),
                    fixture_label=str(payload.get("fixture_label", "") or ""),
                    selected_candidate_hash=str(
                        payload.get("selected_candidate_hash", "") or ""
                    ),
                    selected_candidate_source=str(
                        payload.get("selected_candidate_source", "") or ""
                    ),
                    selected_candidate_lane=str(
                        payload.get("selected_candidate_lane", "") or ""
                    ),
                    selected_candidate_final_score=float(
                        payload.get("selected_candidate_final_score", float("nan"))
                    ),
                    selected_candidate_final_match=float(
                        payload.get("selected_candidate_final_match", float("nan"))
                    ),
                    replay_material_complete=int(
                        payload.get("replay_material_complete", 0) or 0
                    ),
                    stage35_partial_state_relpath=str(
                        payload.get("stage35_partial_state_relpath", "") or ""
                    ),
                    stage35_progress_jsonl_relpath=str(
                        payload.get("stage35_progress_jsonl_relpath", "") or ""
                    ),
                ),
            )
