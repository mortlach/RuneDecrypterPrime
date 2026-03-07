from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict


def stage3_char4_pct_baseline_cfg(*, scorer_impl: str) -> Dict[str, Any]:
    return dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=False,
        char_weights={4: 1.0},
        wli_weights={},
        impl=scorer_impl,
    )


def stage3_char4_avg_fulltext_search_cfg(
    *,
    scorer_stage2_cfg: Dict[str, Any],
    scorer_stage3_impl_avg_fulltext: str,
    direction: Any,
) -> Dict[str, Any]:
    obj = str(scorer_stage2_cfg.get("objective", "avg.logp.win20"))
    if not obj.startswith("avg."):
        obj = "avg.logp.win20"
    return dict(
        objective=str(obj),
        include_char=True,
        use_word_breaks=False,
        char_weights={4: 1.0},
        wli_weights={},
        avg_window_policy="full_text",
        impl=scorer_stage3_impl_avg_fulltext,
        encoding_dir=direction,
        span_hamming_enabled=False,
        span_hamming_mode="off",
        span_hamming_weight=0.0,
    )


def build_stage3_experiment_cfg(
    *,
    profile_name: str,
    direction: Any,
    span_assets_dir: Path | None,
    char_pct_min_override: float | None,
    disable_char_pct_gate: bool,
    scoring_experiment_span_coverage_min: float,
    scoring_experiment_span_quality_min: float,
    scoring_experiment_c_char_pct_min: float,
    baseline_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    p = str(profile_name or "").strip().lower()
    cfg = dict(baseline_cfg, encoding_dir=direction)
    if p in {"", "off", "none", "a_baseline"}:
        cfg.update(
            span_hamming_mode="off",
            span_hamming_enabled=False,
            span_hamming_weight=0.0,
        )
        return cfg
    if p not in {"b_min", "c_min_late"}:
        raise ValueError(f"Unsupported stage3 experiment profile={profile_name!r}")
    if span_assets_dir is None:
        raise FileNotFoundError("span assets dir is required for stage3 span experiment")
    calib_fp = span_assets_dir / "combined_calibration.json"
    ecdf_root = span_assets_dir / "ecdf" / "span_x"
    if not calib_fp.exists():
        raise FileNotFoundError(
            f"Missing combined_calibration.json for stage3 span experiment: {calib_fp}"
        )
    if not ecdf_root.exists():
        raise FileNotFoundError(
            f"Missing span ECDF root for stage3 span experiment: {ecdf_root}"
        )
    cfg.update(
        span_hamming_enabled=True,
        span_hamming_mode="calibrated",
        span_hamming_assets_dir=str(span_assets_dir),
        span_hamming_combine_mode="min",
        span_hamming_weight_span=1.0,
        span_hamming_weight_char=1.0,
        span_hamming_coverage_min=float(scoring_experiment_span_coverage_min),
        span_hamming_quality_min=float(scoring_experiment_span_quality_min),
        span_hamming_gate_fail_policy=("char_only" if p == "c_min_late" else "score_floor"),
    )
    if p == "c_min_late":
        if bool(disable_char_pct_gate):
            cfg["span_hamming_gate_fail_policy"] = "score_floor"
            return cfg
        gate = (
            float(char_pct_min_override)
            if char_pct_min_override is not None
            else float(scoring_experiment_c_char_pct_min)
        )
        cfg["span_hamming_char_pct_min"] = float(gate)
    return cfg


def apply_scoring_experiment_profile(
    *,
    scoring_experiment_profile: str,
    profile_name: str,
    scorer_stage2_cfg: Dict[str, Any],
    scoring_experiment_span_assets_dir: Path | str | None,
    scoring_experiment_span_coverage_min: float,
    scoring_experiment_span_quality_min: float,
    scoring_experiment_c_char_pct_min: float,
    scoring_experiment_enforce_locks: bool,
    resolve_repo_path_fn: Callable[[Path | str | None], Path | None],
    hash_payload_fn: Callable[[Dict[str, Any]], str],
    build_non_scoring_lock_payload_fn: Callable[[], Dict[str, Any]],
    build_scoring_lock_payload_fn: Callable[[], Dict[str, Any]],
    to_repo_rel_path_fn: Callable[[Path | str | None, Path], str],
    repo_root: Path,
    stage3_char4_pct_baseline_cfg_fn: Callable[[], Dict[str, Any]],
) -> Dict[str, Any]:
    profile = str(scoring_experiment_profile).strip().lower()
    if profile in {"", "off", "none"}:
        return dict(
            profile="off",
            enabled=False,
            description="profile-native scoring",
            span_assets_dir="",
            non_scoring_hash_before="",
            non_scoring_hash_after="",
            scoring_hash="",
            updated_profile=str(profile_name),
            updated_stage3_label="B_char34",
            updated_stage3_cfg={},
        )

    pre_non_hash = hash_payload_fn(build_non_scoring_lock_payload_fn())
    stage3_cfg = stage3_char4_pct_baseline_cfg_fn()
    stage3_label = "B_char34"
    desc = ""
    span_assets_dir: Path | None = None

    if profile == "a_baseline":
        stage3_label = "B_char4_pct_baseline"
        stage3_cfg.update(
            span_hamming_mode="off",
            span_hamming_enabled=False,
            span_hamming_weight=0.0,
        )
        desc = "char4 pct baseline (no span calibrated channel)"
    elif profile in {"b_min", "c_min_late"}:
        stage3_label = (
            "B_char4_pct_span_min"
            if profile == "b_min"
            else "B_char4_pct_span_min_late"
        )
        span_assets_dir = resolve_repo_path_fn(scoring_experiment_span_assets_dir)
        if span_assets_dir is None:
            raise ValueError("SCORING_EXPERIMENT_SPAN_ASSETS_DIR cannot be None")
        calib_fp = span_assets_dir / "combined_calibration.json"
        ecdf_root = span_assets_dir / "ecdf" / "span_x"
        if not calib_fp.exists():
            raise FileNotFoundError(
                f"Missing combined_calibration.json for span experiment: {calib_fp}"
            )
        if not ecdf_root.exists():
            raise FileNotFoundError(
                f"Missing span ECDF root for span experiment: {ecdf_root}"
            )
        stage3_cfg.update(
            span_hamming_enabled=True,
            span_hamming_mode="calibrated",
            span_hamming_assets_dir=str(span_assets_dir),
            span_hamming_combine_mode="min",
            span_hamming_weight_span=1.0,
            span_hamming_weight_char=1.0,
            span_hamming_coverage_min=float(scoring_experiment_span_coverage_min),
            span_hamming_quality_min=float(scoring_experiment_span_quality_min),
            span_hamming_gate_fail_policy=(
                "char_only" if profile == "c_min_late" else "score_floor"
            ),
        )
        if profile == "c_min_late":
            stage3_cfg["span_hamming_char_pct_min"] = float(
                scoring_experiment_c_char_pct_min
            )
            desc = (
                "char4 pct + calibrated span (min combine, late activation by char pct)"
            )
        else:
            desc = "char4 pct + calibrated span (min combine)"
    else:
        raise ValueError(
            f"Unsupported SCORING_EXPERIMENT_PROFILE={scoring_experiment_profile!r}; "
            "expected off|a_baseline|b_min|c_min_late"
        )

    updated_profile = f"{str(profile_name)}__{profile}"
    post_non_hash = hash_payload_fn(build_non_scoring_lock_payload_fn())
    if bool(scoring_experiment_enforce_locks) and (pre_non_hash != post_non_hash):
        raise RuntimeError(
            "Scoring experiment changed non-scoring knobs; this violates locked A/B/C "
            f"setup (before={pre_non_hash} after={post_non_hash})"
        )

    return dict(
        profile=profile,
        enabled=True,
        description=desc,
        span_assets_dir=to_repo_rel_path_fn(span_assets_dir, repo_root),
        non_scoring_hash_before=pre_non_hash,
        non_scoring_hash_after=post_non_hash,
        scoring_hash=hash_payload_fn(build_scoring_lock_payload_fn()),
        updated_profile=updated_profile,
        updated_stage3_label=str(stage3_label),
        updated_stage3_cfg=dict(stage3_cfg),
    )
