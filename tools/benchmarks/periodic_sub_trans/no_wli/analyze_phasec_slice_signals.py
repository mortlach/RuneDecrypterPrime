from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rune_decrypter_prime.api import Direction
from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Device
from tools.benchmarks.periodic_sub_trans.common.batch_eval import (
    decrypt_and_score_keys_chunked,
    score_plaintexts_chunked,
)
from tools.benchmarks.periodic_sub_trans.no_wli.build_output_catalog import (
    refresh_catalog_safely,
)


RUN_LABEL = "phasec_slice_signal_analysis_v1"
OUTPUT_ROOT = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "phasec_slice_signal_analysis"
)
FINAL_INSTANCE_GLOBS: tuple[str, ...] = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/*/final_instances/"
    "fixture_fixture_001_p9_c3_l1000__text0__seed511.json",
)
MAX_ARTIFACTS: int | None = None
TOPK_LIMIT_PER_ARTIFACT: int | None = None
ANALYSIS_BATCH_CHUNK_SIZE = 32
ANALYSIS_REQUIRE_BATCH_SCORING = True
ANALYSIS_PHASEC_SEED_OFFSET_FALLBACK = 1200003
ANALYSIS_RESCUE_SLIP_SWAPS_FALLBACK = 6


@dataclass(frozen=True)
class ArtifactCase:
    artifact_path: Path
    run_dir: Path
    run_config_path: Path
    artifact: dict[str, Any]
    run_config: dict[str, Any]


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except Exception:
        return str(path)


def _resolve_repo_path(path_like: Path | str | None) -> Path | None:
    if path_like is None:
        return None
    path = Path(path_like)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _jsonify(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    if isinstance(value, Path):
        return _repo_rel(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def discover_artifact_cases() -> list[ArtifactCase]:
    candidates: list[Path] = []
    for pattern in FINAL_INSTANCE_GLOBS:
        candidates.extend(REPO_ROOT.glob(pattern))
    existing = [path.resolve() for path in candidates if path.exists()]
    existing = sorted(set(existing), key=lambda path: path.parents[1].name)
    if MAX_ARTIFACTS is not None:
        existing = existing[-int(MAX_ARTIFACTS) :]
    out: list[ArtifactCase] = []
    for artifact_path in existing:
        run_dir = artifact_path.parents[1]
        run_config_path = run_dir / "run_config.json"
        if not run_config_path.exists():
            continue
        out.append(
            ArtifactCase(
                artifact_path=artifact_path,
                run_dir=run_dir,
                run_config_path=run_config_path,
                artifact=_load_json(artifact_path),
                run_config=_load_json(run_config_path),
            )
        )
    return out


def _build_cipher(artifact: Mapping[str, Any]) -> PeriodicColumnarCipher:
    direction = Direction(str(artifact.get("direction", "ltr")))
    cfg = CipherConfig(
        name="periodic_columnar",
        ciphertext=[],
        period=int(artifact["period"]),
        columns=int(artifact["columns"]),
        alphabet_size=int(artifact["alphabet_size"]),
        key_length=int(artifact["period"]) * int(artifact["alphabet_size"]) + int(artifact["columns"]),
        order=str(artifact["order"]),
        encoding_dir=direction,
        wli_data=[],
        device=Device.CPU,
    )
    return PeriodicColumnarCipher(cfg)


def _build_scorer_runtime(
    *,
    artifact: Mapping[str, Any],
    run_config: Mapping[str, Any],
) -> Any:
    stage3_cfg = dict(((run_config.get("stage3") or {}) if isinstance(run_config, Mapping) else {}))
    scorer_cfg = dict((stage3_cfg.get("scorer") or {}) if isinstance(stage3_cfg, Mapping) else {})
    span_assets_dir = _resolve_repo_path(
        scorer_cfg.get("span_hamming_assets_dir", None)
    )
    if span_assets_dir is not None:
        scorer_cfg["span_hamming_assets_dir"] = str(span_assets_dir)
    direction = Direction(str(artifact.get("direction", "ltr")))
    cfg_full = CipherConfig(
        name="periodic_columnar",
        ciphertext=[],
        period=int(artifact["period"]),
        columns=int(artifact["columns"]),
        alphabet_size=int(artifact["alphabet_size"]),
        key_length=int(artifact["period"]) * int(artifact["alphabet_size"]) + int(artifact["columns"]),
        order=str(artifact["order"]),
        encoding_dir=direction,
        wli_data=[],
        device=Device.CPU,
    )
    return build_scorer(cfg_full, ScoringConfig(**scorer_cfg))


def _phasec_cfg(run_config: Mapping[str, Any]) -> Mapping[str, Any]:
    stage3 = (run_config.get("stage3") or {}) if isinstance(run_config, Mapping) else {}
    two_phase = (stage3.get("two_phase") or {}) if isinstance(stage3, Mapping) else {}
    return (two_phase.get("phase_c") or {}) if isinstance(two_phase, Mapping) else {}


def _solver_seed(run_config: Mapping[str, Any]) -> int:
    stage3 = (run_config.get("stage3") or {}) if isinstance(run_config, Mapping) else {}
    solver = (stage3.get("solver") or {}) if isinstance(stage3, Mapping) else {}
    return int(solver.get("seed", 2026) or 2026)


def _phasec_seed(run_config: Mapping[str, Any]) -> int:
    phasec = _phasec_cfg(run_config)
    seed_offset = int(phasec.get("seed_offset", ANALYSIS_PHASEC_SEED_OFFSET_FALLBACK) or 0)
    return int(_solver_seed(run_config) + int(seed_offset))


def _phasec_rescue_slip_swaps(run_config: Mapping[str, Any]) -> int:
    phasec = _phasec_cfg(run_config)
    cfg = (phasec.get("cfg") or {}) if isinstance(phasec, Mapping) else {}
    return int(
        max(
            1,
            int(cfg.get("rescue_slip_swaps", ANALYSIS_RESCUE_SLIP_SWAPS_FALLBACK) or 0),
        )
    )


def _score_full_plaintext(
    *,
    scorer: Any,
    plaintext_idx: Sequence[int] | np.ndarray,
    chunk_size: int,
    require_batch: bool,
) -> float:
    scores, _stats = score_plaintexts_chunked(
        scorer=scorer,
        plaintexts=[np.asarray(plaintext_idx, dtype=np.uint8).reshape(-1)],
        wli=None,
        chunk_size=int(max(1, int(chunk_size))),
        require_batch=bool(require_batch),
    )
    _ = _stats
    return float(scores[0]) if int(scores.size) > 0 else float("nan")


def legacy_residue_proxy_signal(
    *,
    plaintext_idx: Sequence[int] | np.ndarray,
    period: int,
    scorer: Any,
    chunk_size: int = ANALYSIS_BATCH_CHUNK_SIZE,
    require_batch: bool = ANALYSIS_REQUIRE_BATCH_SCORING,
) -> dict[str, Any]:
    pt = np.asarray(plaintext_idx, dtype=np.uint8).reshape(-1)
    period_i = int(max(1, int(period)))
    rows: list[dict[str, Any]] = []
    for slice_idx in range(period_i):
        residue_pt = np.asarray(pt[int(slice_idx) :: int(period_i)], dtype=np.uint8).reshape(-1)
        score = _score_full_plaintext(
            scorer=scorer,
            plaintext_idx=residue_pt,
            chunk_size=int(chunk_size),
            require_batch=bool(require_batch),
        )
        score_per_char = (
            float(score) / float(max(1, int(residue_pt.size)))
            if np.isfinite(score)
            else float("nan")
        )
        rows.append(
            dict(
                slice_idx=int(slice_idx),
                residue_len=int(residue_pt.size),
                score=float(score),
                score_per_char=float(score_per_char),
            )
        )

    finite_rows = [
        row for row in rows if np.isfinite(float(row.get("score_per_char", float("nan"))))
    ]
    if finite_rows:
        finite_rows = sorted(
            finite_rows,
            key=lambda row: (
                float(row.get("score_per_char", float("inf"))),
                int(row.get("slice_idx", 0)),
            ),
        )
        chosen = dict(finite_rows[0])
        reason = "legacy_residue_score_per_char_min"
    else:
        chosen = dict(slice_idx=0, residue_len=0, score=float("nan"), score_per_char=float("nan"))
        reason = "fallback_no_finite_residue_score"
    return dict(
        target_slice=int(chosen.get("slice_idx", 0)),
        reason=str(reason),
        target_score=float(chosen.get("score", float("nan"))),
        target_score_per_char=float(chosen.get("score_per_char", float("nan"))),
        rows=[dict(row) for row in rows],
    )


def _apply_slice_slip(
    *,
    key_vals: Sequence[int],
    target_slice: int,
    swaps: int,
    rng_obj: np.random.Generator,
    alphabet_size: int,
) -> list[int]:
    out = list(map(int, key_vals))
    if int(alphabet_size) <= 1:
        return out
    phase_base = int(target_slice) * int(alphabet_size)
    for _ in range(max(0, int(swaps))):
        a = int(rng_obj.integers(0, int(alphabet_size)))
        b = int(rng_obj.integers(0, int(alphabet_size - 1)))
        if b >= a:
            b += 1
        i1 = int(phase_base + int(a))
        i2 = int(phase_base + int(b))
        out[i1], out[i2] = int(out[i2]), int(out[i1])
    return out


def slice_probe_signal(
    *,
    key_idx: Sequence[int] | np.ndarray,
    current_score: float,
    period: int,
    alphabet_size: int,
    scorer: Any,
    cipher: Any,
    ciphertext_idx: Sequence[int] | np.ndarray,
    phase_seed: int,
    start_idx: int,
    rescue_slip_swaps: int,
    chunk_size: int = ANALYSIS_BATCH_CHUNK_SIZE,
    require_batch: bool = ANALYSIS_REQUIRE_BATCH_SCORING,
) -> dict[str, Any]:
    current_key = list(map(int, np.asarray(key_idx).reshape(-1).tolist()))
    period_i = int(max(1, int(period)))
    alphabet_i = int(max(1, int(alphabet_size)))
    probe_keys: list[list[int]] = []
    probe_meta: list[dict[str, Any]] = []
    current_key_t = tuple(current_key)
    for slice_idx in range(period_i):
        probe_seed = int(phase_seed) + int(start_idx) * 10007 + int(slice_idx) * 313
        probe_rng = np.random.default_rng(int(probe_seed))
        cand = _apply_slice_slip(
            key_vals=current_key,
            target_slice=int(slice_idx),
            swaps=int(rescue_slip_swaps),
            rng_obj=probe_rng,
            alphabet_size=int(alphabet_i),
        )
        cand_t = tuple(map(int, cand))
        if cand_t == current_key_t:
            continue
        probe_keys.append(list(cand))
        probe_meta.append(dict(slice_idx=int(slice_idx)))

    if not probe_keys:
        return dict(
            target_slice=0,
            reason="fallback_no_probe_candidates",
            target_score=float("nan"),
            target_score_gain=float("nan"),
            probe_evals=0,
            rows=[],
        )

    probe_pts, probe_scores, _stats = decrypt_and_score_keys_chunked(
        cipher=cipher,
        ciphertext=np.asarray(ciphertext_idx, dtype=np.uint8).reshape(-1),
        keys=probe_keys,
        scorer=scorer,
        wli=None,
        chunk_size=int(max(1, min(int(chunk_size), len(probe_keys)))),
        require_batch=bool(require_batch),
    )
    _ = _stats
    best_idx = 0
    best_score = float("nan")
    best_gain = float("nan")
    rows: list[dict[str, Any]] = []
    for probe_idx, _cand_key in enumerate(probe_keys):
        cand_score = (
            float(probe_scores[probe_idx])
            if probe_idx < int(probe_scores.size)
            else float("nan")
        )
        score_gain = (
            float(cand_score - current_score)
            if np.isfinite(cand_score) and np.isfinite(current_score)
            else float("nan")
        )
        slice_idx = int(probe_meta[probe_idx].get("slice_idx", 0))
        rows.append(
            dict(
                slice_idx=int(slice_idx),
                score=float(cand_score),
                score_gain=float(score_gain),
            )
        )
        better = False
        if probe_idx == 0:
            better = True
        elif np.isfinite(score_gain) and np.isfinite(best_gain):
            if float(score_gain) > float(best_gain):
                better = True
            elif float(score_gain) == float(best_gain):
                if np.isfinite(cand_score) and np.isfinite(best_score):
                    if float(cand_score) > float(best_score):
                        better = True
                    elif float(cand_score) == float(best_score):
                        better = bool(slice_idx < int(probe_meta[best_idx]["slice_idx"]))
                else:
                    better = bool(slice_idx < int(probe_meta[best_idx]["slice_idx"]))
        elif np.isfinite(score_gain) and (not np.isfinite(best_gain)):
            better = True
        elif (not np.isfinite(score_gain)) and (not np.isfinite(best_gain)):
            better = bool(slice_idx < int(probe_meta[best_idx]["slice_idx"]))
        if better:
            best_idx = int(probe_idx)
            best_score = float(cand_score)
            best_gain = float(score_gain)

    return dict(
        target_slice=int(probe_meta[best_idx]["slice_idx"]),
        reason="slice_probe_best_score_gain",
        target_score=float(best_score),
        target_score_gain=float(best_gain),
        probe_evals=int(len(probe_keys)),
        rows=[dict(row) for row in rows],
        probe_plaintext=(
            np.asarray(probe_pts[best_idx], dtype=np.uint8).reshape(-1).tolist()
            if best_idx < int(probe_pts.shape[0])
            else []
        ),
    )


def analyze_stage3_topk_candidate_row(
    *,
    artifact_relpath: str,
    run_id: str,
    topk_row: Mapping[str, Any],
    truth_row: Mapping[str, Any],
    period: int,
    alphabet_size: int,
    scorer: Any,
    cipher: Any,
    ciphertext_idx: Sequence[int] | np.ndarray,
    phase_seed: int,
    rescue_slip_swaps: int,
    chunk_size: int = ANALYSIS_BATCH_CHUNK_SIZE,
    require_batch: bool = ANALYSIS_REQUIRE_BATCH_SCORING,
) -> dict[str, Any]:
    key_idx = list(map(int, topk_row.get("key_idx", [])))
    plaintext_idx = list(map(int, topk_row.get("plaintext_idx", [])))
    current_score = _score_full_plaintext(
        scorer=scorer,
        plaintext_idx=plaintext_idx,
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
    )
    legacy = legacy_residue_proxy_signal(
        plaintext_idx=plaintext_idx,
        period=int(period),
        scorer=scorer,
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
    )
    slice_probe = slice_probe_signal(
        key_idx=key_idx,
        current_score=float(current_score),
        period=int(period),
        alphabet_size=int(alphabet_size),
        scorer=scorer,
        cipher=cipher,
        ciphertext_idx=ciphertext_idx,
        phase_seed=int(phase_seed),
        start_idx=int(topk_row.get("rank", 0) or 0),
        rescue_slip_swaps=int(rescue_slip_swaps),
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
    )
    truth_worst_slice = truth_row.get("worst_substitution_slice", None)
    oracle_period_residue = truth_row.get("worst_plaintext_period_residue", None)
    legacy_target_slice = legacy.get("target_slice", None)
    slice_probe_target_slice = slice_probe.get("target_slice", None)
    legacy_hit = (
        int(legacy_target_slice) == int(truth_worst_slice)
        if legacy_target_slice is not None and truth_worst_slice is not None
        else False
    )
    oracle_hit = (
        int(oracle_period_residue) == int(truth_worst_slice)
        if oracle_period_residue is not None and truth_worst_slice is not None
        else False
    )
    slice_probe_hit = (
        int(slice_probe_target_slice) == int(truth_worst_slice)
        if slice_probe_target_slice is not None and truth_worst_slice is not None
        else False
    )
    return dict(
        artifact_relpath=str(artifact_relpath),
        run_id=str(run_id),
        rank=int(topk_row.get("rank", 0) or 0),
        source=str(topk_row.get("source", "") or ""),
        end_hash=str(topk_row.get("end_hash", "") or ""),
        match_ratio=float(topk_row.get("match_ratio", float("nan"))),
        score_judge_saved=float(topk_row.get("score_judge", float("nan"))),
        score_runtime=float(current_score),
        key_hamming_total=int(truth_row.get("key_hamming_total", 0) or 0),
        key_hamming_substitution=int(truth_row.get("key_hamming_substitution", 0) or 0),
        key_hamming_columns=int(truth_row.get("key_hamming_columns", 0) or 0),
        truth_worst_substitution_slice=(
            int(truth_worst_slice) if truth_worst_slice is not None else None
        ),
        truth_worst_plaintext_period_residue=(
            int(oracle_period_residue) if oracle_period_residue is not None else None
        ),
        legacy_residue_target_slice=(
            int(legacy_target_slice) if legacy_target_slice is not None else None
        ),
        legacy_residue_target_score_per_char=float(
            legacy.get("target_score_per_char", float("nan"))
        ),
        legacy_residue_hit_truth=int(1 if legacy_hit else 0),
        oracle_period_residue_hit_truth=int(1 if oracle_hit else 0),
        slice_probe_target_slice=(
            int(slice_probe_target_slice) if slice_probe_target_slice is not None else None
        ),
        slice_probe_target_score=float(slice_probe.get("target_score", float("nan"))),
        slice_probe_score_gain=float(slice_probe.get("target_score_gain", float("nan"))),
        slice_probe_probe_evals=int(slice_probe.get("probe_evals", 0) or 0),
        slice_probe_hit_truth=int(1 if slice_probe_hit else 0),
        slice_probe_better_than_legacy=int(
            1 if bool(slice_probe_hit) and (not bool(legacy_hit)) else 0
        ),
    )


def summarize_phasec_start_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    summary = dict(
        phasec_start_count=0,
        score_up_count=0,
        match_up_count=0,
        match_down_count=0,
        score_up_match_not_up_count=0,
        score_up_match_down_count=0,
        lexical_requests_positive_count=0,
        rescue_attempted_count=0,
        rescue_applied_count=0,
    )
    for row in rows:
        score_gain = float(row.get("score_gain", float("nan")))
        match_gain = float(row.get("match_gain", float("nan")))
        lexical_requests_delta = int(row.get("lexical_requests_delta", 0) or 0)
        rescue_attempted = int(row.get("rescue_attempted", 0) or 0)
        rescue_applied = int(row.get("rescue_applied", 0) or 0)
        score_up = bool(np.isfinite(score_gain) and float(score_gain) > 0.0)
        match_up = bool(np.isfinite(match_gain) and float(match_gain) > 0.0)
        match_down = bool(np.isfinite(match_gain) and float(match_gain) < 0.0)
        summary["phasec_start_count"] += 1
        summary["score_up_count"] += int(1 if score_up else 0)
        summary["match_up_count"] += int(1 if match_up else 0)
        summary["match_down_count"] += int(1 if match_down else 0)
        summary["score_up_match_not_up_count"] += int(1 if score_up and (not match_up) else 0)
        summary["score_up_match_down_count"] += int(1 if score_up and match_down else 0)
        summary["lexical_requests_positive_count"] += int(
            1 if int(lexical_requests_delta) > 0 else 0
        )
        summary["rescue_attempted_count"] += int(1 if int(rescue_attempted) > 0 else 0)
        summary["rescue_applied_count"] += int(1 if int(rescue_applied) > 0 else 0)
    return summary


def build_phasec_start_rows(
    *,
    artifact_relpath: str,
    run_id: str,
    best_match_ratio: float,
    start_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in start_rows:
        score_gain = float(row.get("score_gain", float("nan")))
        match_gain = float(row.get("match_gain", float("nan")))
        out.append(
            dict(
                artifact_relpath=str(artifact_relpath),
                run_id=str(run_id),
                best_match_ratio=float(best_match_ratio),
                start_idx=int(row.get("start_idx", 0) or 0),
                source=str(row.get("source", "") or ""),
                source_rank=int(row.get("source_rank", 0) or 0),
                init_match=float(row.get("init_match", float("nan"))),
                final_match=float(row.get("final_match", float("nan"))),
                match_gain=float(match_gain),
                init_score=float(row.get("init_score", float("nan"))),
                final_score=float(row.get("final_score", float("nan"))),
                score_gain=float(score_gain),
                lexical_requests_delta=int(row.get("lexical_requests_delta", 0) or 0),
                lexical_budget_skips_delta=int(
                    row.get("lexical_budget_skips_delta", 0) or 0
                ),
                lexical_threshold_skips_delta=int(
                    row.get("lexical_threshold_skips_delta", 0) or 0
                ),
                rescue_attempted=int(row.get("rescue_attempted", 0) or 0),
                rescue_applied=int(row.get("rescue_applied", 0) or 0),
                rescue_target_slice=row.get("rescue_target_slice", None),
                rescue_score_gain=row.get("rescue_score_gain", None),
                score_up=int(1 if np.isfinite(score_gain) and float(score_gain) > 0.0 else 0),
                match_up=int(1 if np.isfinite(match_gain) and float(match_gain) > 0.0 else 0),
                match_down=int(
                    1 if np.isfinite(match_gain) and float(match_gain) < 0.0 else 0
                ),
                score_up_match_not_up=int(
                    1
                    if np.isfinite(score_gain)
                    and float(score_gain) > 0.0
                    and not (np.isfinite(match_gain) and float(match_gain) > 0.0)
                    else 0
                ),
                score_up_match_down=int(
                    1
                    if np.isfinite(score_gain)
                    and float(score_gain) > 0.0
                    and np.isfinite(match_gain)
                    and float(match_gain) < 0.0
                    else 0
                ),
            )
        )
    return out


def analyze_artifact_case(
    case: ArtifactCase,
    *,
    chunk_size: int = ANALYSIS_BATCH_CHUNK_SIZE,
    require_batch: bool = ANALYSIS_REQUIRE_BATCH_SCORING,
) -> dict[str, Any]:
    artifact = dict(case.artifact)
    run_config = dict(case.run_config)
    artifact_relpath = _repo_rel(case.artifact_path)
    run_id = str(case.run_dir.name)
    stage3_diag = dict(artifact.get("stage3_diagnostics", {}) or {})
    truth_diag = dict(artifact.get("truth_diagnostics", {}) or {})

    start_rows = build_phasec_start_rows(
        artifact_relpath=artifact_relpath,
        run_id=run_id,
        best_match_ratio=float(artifact.get("best_match_ratio", float("nan"))),
        start_rows=list(stage3_diag.get("phaseC_start_summaries", []) or []),
    )
    start_summary = summarize_phasec_start_rows(start_rows)

    candidate_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    truth_topk_rows = list(truth_diag.get("stage3_topk_truth_diagnostics", []) or [])
    truth_by_rank = {
        int(row.get("rank", 0) or 0): dict(row)
        for row in truth_topk_rows
        if isinstance(row, Mapping)
    }
    topk_rows = list(artifact.get("stage3_topk", []) or [])
    if TOPK_LIMIT_PER_ARTIFACT is not None:
        topk_rows = topk_rows[: int(TOPK_LIMIT_PER_ARTIFACT)]
    if topk_rows and truth_by_rank:
        scorer = _build_scorer_runtime(artifact=artifact, run_config=run_config)
        cipher = _build_cipher(artifact)
        phase_seed = int(_phasec_seed(run_config))
        rescue_slip_swaps = int(_phasec_rescue_slip_swaps(run_config))
        ciphertext_idx = np.asarray(artifact.get("ciphertext_idx", []), dtype=np.uint8).reshape(-1)
        for topk_row in topk_rows:
            rank = int(topk_row.get("rank", 0) or 0)
            truth_row = truth_by_rank.get(rank)
            if truth_row is None:
                warnings.append(f"{artifact_relpath}: missing truth row for stage3_topk rank={rank}")
                continue
            if not topk_row.get("key_idx") or not topk_row.get("plaintext_idx"):
                warnings.append(f"{artifact_relpath}: missing key/plaintext for stage3_topk rank={rank}")
                continue
            candidate_rows.append(
                analyze_stage3_topk_candidate_row(
                    artifact_relpath=artifact_relpath,
                    run_id=run_id,
                    topk_row=topk_row,
                    truth_row=truth_row,
                    period=int(artifact.get("period", 0) or 0),
                    alphabet_size=int(artifact.get("alphabet_size", 0) or 0),
                    scorer=scorer,
                    cipher=cipher,
                    ciphertext_idx=ciphertext_idx,
                    phase_seed=int(phase_seed),
                    rescue_slip_swaps=int(rescue_slip_swaps),
                    chunk_size=int(chunk_size),
                    require_batch=bool(require_batch),
                )
            )

    candidate_count = int(len(candidate_rows))
    legacy_hit_count = int(
        sum(int(row.get("legacy_residue_hit_truth", 0) or 0) for row in candidate_rows)
    )
    oracle_hit_count = int(
        sum(int(row.get("oracle_period_residue_hit_truth", 0) or 0) for row in candidate_rows)
    )
    slice_probe_hit_count = int(
        sum(int(row.get("slice_probe_hit_truth", 0) or 0) for row in candidate_rows)
    )
    slice_probe_better_count = int(
        sum(int(row.get("slice_probe_better_than_legacy", 0) or 0) for row in candidate_rows)
    )

    artifact_row = dict(
        run_id=str(run_id),
        artifact_relpath=str(artifact_relpath),
        best_match_ratio=float(artifact.get("best_match_ratio", float("nan"))),
        best_score=float(artifact.get("best_score", float("nan"))),
        stage3_topk_count=int(len(list(artifact.get("stage3_topk", []) or []))),
        truth_available=bool(truth_diag.get("available", False)),
        truth_worst_substitution_slice=truth_diag.get("worst_substitution_slice", None),
        truth_worst_plaintext_period_residue=truth_diag.get(
            "worst_plaintext_period_residue",
            None,
        ),
        key_hamming_substitution=truth_diag.get("key_hamming_substitution", None),
        key_hamming_columns=truth_diag.get("key_hamming_columns", None),
        phaseC_start_keys_used=int(stage3_diag.get("phaseC_start_keys_used", 0) or 0),
        phaseC_improved_best=int(stage3_diag.get("phaseC_improved_best", 0) or 0),
        phaseC_lexical_requests=int(stage3_diag.get("phaseC_lexical_requests", 0) or 0),
        phaseC_lexical_threshold_skips=int(
            stage3_diag.get("phaseC_lexical_threshold_skips", 0) or 0
        ),
        phaseC_lexical_min_match_cfg=stage3_diag.get("phaseC_lexical_min_match_cfg", None),
        phaseC_rescue_ran=int(stage3_diag.get("phaseC_rescue_ran", 0) or 0),
        phaseC_rescue_target_mode_cfg=str(
            stage3_diag.get("phaseC_rescue_target_mode_cfg", "") or ""
        ),
        analyzed_topk_candidate_count=int(candidate_count),
        legacy_residue_hit_count=int(legacy_hit_count),
        legacy_residue_hit_rate=(
            float(legacy_hit_count) / float(candidate_count)
            if int(candidate_count) > 0
            else float("nan")
        ),
        oracle_period_residue_hit_count=int(oracle_hit_count),
        oracle_period_residue_hit_rate=(
            float(oracle_hit_count) / float(candidate_count)
            if int(candidate_count) > 0
            else float("nan")
        ),
        slice_probe_hit_count=int(slice_probe_hit_count),
        slice_probe_hit_rate=(
            float(slice_probe_hit_count) / float(candidate_count)
            if int(candidate_count) > 0
            else float("nan")
        ),
        slice_probe_better_than_legacy_count=int(slice_probe_better_count),
        phasec_start_count=int(start_summary["phasec_start_count"]),
        phasec_score_up_count=int(start_summary["score_up_count"]),
        phasec_match_up_count=int(start_summary["match_up_count"]),
        phasec_match_down_count=int(start_summary["match_down_count"]),
        phasec_score_up_match_not_up_count=int(
            start_summary["score_up_match_not_up_count"]
        ),
        phasec_score_up_match_down_count=int(
            start_summary["score_up_match_down_count"]
        ),
        phasec_lexical_requests_positive_count=int(
            start_summary["lexical_requests_positive_count"]
        ),
        phasec_rescue_attempted_count=int(start_summary["rescue_attempted_count"]),
        phasec_rescue_applied_count=int(start_summary["rescue_applied_count"]),
    )
    return dict(
        artifact_row=artifact_row,
        candidate_rows=candidate_rows,
        start_rows=start_rows,
        warnings=warnings,
    )


def build_summary(
    *,
    artifact_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    start_rows: Sequence[Mapping[str, Any]],
    warnings: Sequence[str],
) -> dict[str, Any]:
    candidate_count = int(len(candidate_rows))
    start_count = int(len(start_rows))
    legacy_hits = int(
        sum(int(row.get("legacy_residue_hit_truth", 0) or 0) for row in candidate_rows)
    )
    oracle_hits = int(
        sum(int(row.get("oracle_period_residue_hit_truth", 0) or 0) for row in candidate_rows)
    )
    slice_probe_hits = int(
        sum(int(row.get("slice_probe_hit_truth", 0) or 0) for row in candidate_rows)
    )
    slice_probe_better = int(
        sum(int(row.get("slice_probe_better_than_legacy", 0) or 0) for row in candidate_rows)
    )
    score_up_match_not_up = int(
        sum(int(row.get("score_up_match_not_up", 0) or 0) for row in start_rows)
    )
    score_up_match_down = int(
        sum(int(row.get("score_up_match_down", 0) or 0) for row in start_rows)
    )
    lexical_positive = int(
        sum(int(row.get("lexical_requests_delta", 0) > 0) for row in start_rows)
    )
    return dict(
        run_label=RUN_LABEL,
        artifact_count=int(len(artifact_rows)),
        topk_candidate_count=int(candidate_count),
        phasec_start_count=int(start_count),
        legacy_residue_hit_count=int(legacy_hits),
        legacy_residue_hit_rate=(
            float(legacy_hits) / float(candidate_count)
            if int(candidate_count) > 0
            else float("nan")
        ),
        oracle_period_residue_hit_count=int(oracle_hits),
        oracle_period_residue_hit_rate=(
            float(oracle_hits) / float(candidate_count)
            if int(candidate_count) > 0
            else float("nan")
        ),
        slice_probe_hit_count=int(slice_probe_hits),
        slice_probe_hit_rate=(
            float(slice_probe_hits) / float(candidate_count)
            if int(candidate_count) > 0
            else float("nan")
        ),
        slice_probe_better_than_legacy_count=int(slice_probe_better),
        phasec_score_up_match_not_up_count=int(score_up_match_not_up),
        phasec_score_up_match_down_count=int(score_up_match_down),
        phasec_lexical_requests_positive_count=int(lexical_positive),
        warnings=list(map(str, warnings)),
    )


def main() -> None:
    cases = discover_artifact_cases()
    run_dir = OUTPUT_ROOT / f"{_utc_label()}_{RUN_LABEL}"
    run_dir.mkdir(parents=True, exist_ok=True)

    artifact_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    start_rows: list[dict[str, Any]] = []
    warnings: list[str] = []

    for case in cases:
        out = analyze_artifact_case(case)
        artifact_rows.append(dict(out["artifact_row"]))
        candidate_rows.extend(dict(row) for row in out["candidate_rows"])
        start_rows.extend(dict(row) for row in out["start_rows"])
        warnings.extend(list(map(str, out["warnings"])))

    summary = build_summary(
        artifact_rows=artifact_rows,
        candidate_rows=candidate_rows,
        start_rows=start_rows,
        warnings=warnings,
    )

    _write_csv(run_dir / "artifact_summary.csv", artifact_rows)
    _write_csv(run_dir / "stage3_topk_slice_signals.csv", candidate_rows)
    _write_csv(run_dir / "phasec_start_summary.csv", start_rows)
    (run_dir / "summary.json").write_text(
        json.dumps(
            _jsonify(
                dict(
                    summary=summary,
                    artifact_rows=artifact_rows,
                )
            ),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(
        f"[phasec_slice_signal_analysis] run_dir={_repo_rel(run_dir)}",
        flush=True,
    )
    print(
        "[phasec_slice_signal_analysis] "
        f"artifacts={int(summary['artifact_count'])} "
        f"topk_candidates={int(summary['topk_candidate_count'])} "
        f"phasec_starts={int(summary['phasec_start_count'])}",
        flush=True,
    )
    print(
        "[phasec_slice_signal_analysis] "
        f"legacy_residue_hit_rate={float(summary['legacy_residue_hit_rate']):.3f} "
        f"oracle_period_residue_hit_rate={float(summary['oracle_period_residue_hit_rate']):.3f} "
        f"slice_probe_hit_rate={float(summary['slice_probe_hit_rate']):.3f}",
        flush=True,
    )
    print(
        "[phasec_slice_signal_analysis] "
        f"slice_probe_better_than_legacy={int(summary['slice_probe_better_than_legacy_count'])} "
        f"score_up_match_not_up={int(summary['phasec_score_up_match_not_up_count'])} "
        f"score_up_match_down={int(summary['phasec_score_up_match_down_count'])} "
        f"lexical_positive_starts={int(summary['phasec_lexical_requests_positive_count'])}",
        flush=True,
    )
    if warnings:
        print(
            "[phasec_slice_signal_analysis] "
            f"warnings={len(warnings)} first_warning={warnings[0]}",
            flush=True,
        )
    refresh_catalog_safely(print_fn=print)


if __name__ == "__main__":
    main()
