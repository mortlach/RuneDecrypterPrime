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
from tools.benchmarks.periodic_sub_trans.no_wli import (
    analyze_phasec_slice_signals as slice_signal_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_rescue_candidates import (
    apply_slice_pair_swap as shared_apply_slice_pair_swap,
    apply_slice_slip as shared_apply_slice_slip,
    target_slice_active_positions as shared_target_slice_active_positions,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_rescue_search import (
    run_slice_local_mini_search as shared_run_slice_local_mini_search,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_rescue_selector import (
    lexical_rank_from_row as shared_lexical_rank_from_row,
    landing_sort_key as shared_landing_sort_key,
    pareto_shortlist as shared_pareto_shortlist,
    rank_rows as shared_rank_rows,
    row_match_gain as shared_row_match_gain,
    row_score_gain as shared_row_score_gain,
    row_search_gain as shared_row_search_gain,
    score_band_shortlist as shared_score_band_shortlist,
    score_sort_key as shared_score_sort_key,
    select_guard_passing_row as shared_select_guard_passing_row,
)
from tools.benchmarks.periodic_sub_trans.no_wli.scoring_experiment_config import (
    build_word_ngram_report_cfg,
)
from tools.benchmarks.periodic_sub_trans.no_wli.word_ngram_report import (
    extract_word_ngram_report_fields,
    score_word_ngram_report_for_plaintext,
)


RUN_LABEL = "phasec_rescue_replay_v5"
OUTPUT_ROOT = Path("output/tools/benchmarks/periodic_sub_trans/no_wli/phasec_rescue_replay")
FINAL_INSTANCE_GLOBS = slice_signal_mod.FINAL_INSTANCE_GLOBS
MAX_ARTIFACTS: int | None = None
ANALYSIS_BATCH_CHUNK_SIZE = slice_signal_mod.ANALYSIS_BATCH_CHUNK_SIZE
ANALYSIS_REQUIRE_BATCH_SCORING = slice_signal_mod.ANALYSIS_REQUIRE_BATCH_SCORING
REPLAY_GUARD_MAX_DROP_VALUES: tuple[float, ...] = (
    0.0,
    0.002,
    0.005,
    0.01,
    0.02,
    0.05,
    0.10,
    0.20,
    0.30,
    0.35,
)
REPLAY_PHASEB_TOPK_MIN_RANK = 2
REPLAY_MAX_CHALLENGERS_PER_ARTIFACT: int | None = None
REPLAY_RESCUE_CANDIDATES_FALLBACK = 8
REPLAY_MINI_SEARCH_STEPS = 2
REPLAY_MINI_SEARCH_BEAM_WIDTH = 4
REPLAY_MINI_SEARCH_TOP_SYMBOLS = 10
REPLAY_MINI_SEARCH_FINAL_KEEP = 8
REPLAY_MINI_SEARCH_KEEP_ALL_ROWS = True
REPLAY_SELECTOR_MODES: tuple[str, ...] = (
    "baseline",
    "top_score_then_search",
    "rescue_shallow_then_search",
    "score_band_then_lexical_then_search",
    "gain_based",
    "pareto_shortlist",
)
REPLAY_SELECTOR_TOP_SCORE_BAND_EPS = 0.001


@dataclass(frozen=True)
class ArtifactCase:
    artifact_path: Path
    run_dir: Path
    run_config_path: Path
    artifact: dict[str, Any]
    run_config: dict[str, Any]


@dataclass(frozen=True)
class ReplayStart:
    artifact_relpath: str
    run_id: str
    start_idx: int
    lane: str
    source: str
    source_rank: int
    candidate_hash: str
    key_idx: tuple[int, ...]
    plaintext_idx: tuple[int, ...]
    init_match: float
    init_score: float
    init_search_score: float
    live_rescue_attempted: int
    live_rescue_applied: int
    live_rescue_guard_search_passed: int
    live_rescue_target_slice: int | None
    live_overtook_anchor: int
    live_became_global_best: int


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except Exception:
        return str(path)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="\n") as fh:
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


def _build_stage3_scorer_runtime(
    *,
    artifact: Mapping[str, Any],
    run_config: Mapping[str, Any],
    scorer_key: str,
) -> Any:
    stage3_cfg = dict(
        ((run_config.get("stage3") or {}) if isinstance(run_config, Mapping) else {})
    )
    scorer_cfg = dict(
        (stage3_cfg.get(str(scorer_key)) or {})
        if isinstance(stage3_cfg, Mapping)
        else {}
    )
    if not scorer_cfg and str(scorer_key) != "scorer":
        scorer_cfg = dict(stage3_cfg.get("scorer") or {})
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


def _resolve_repo_path(path_like: Path | str | None) -> Path | None:
    if path_like is None:
        return None
    path = Path(path_like)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _build_stage3_word_ngram_report_runtime(
    *,
    artifact: Mapping[str, Any],
    run_config: Mapping[str, Any],
) -> Any | None:
    stage3_cfg = dict(
        ((run_config.get("stage3") or {}) if isinstance(run_config, Mapping) else {})
    )
    raw_cfg = dict(
        (stage3_cfg.get("word_ngram_report") or {})
        if isinstance(stage3_cfg, Mapping)
        else {}
    )
    if not bool(raw_cfg.get("enabled", False)):
        return None
    base_cfg = dict(
        (stage3_cfg.get("judge_scorer") or {})
        if isinstance(stage3_cfg, Mapping)
        else {}
    )
    direction = Direction(str(artifact.get("direction", "ltr")))
    scorer_cfg = build_word_ngram_report_cfg(
        base_cfg=base_cfg,
        direction=direction,
        word_ngram_report_enabled=bool(raw_cfg.get("enabled", False)),
        word_ngram_report_sqlite_path=raw_cfg.get("sqlite_path", None),
        word_ngram_report_alpha=float(raw_cfg.get("alpha", 0.4) or 0.4),
        word_ngram_report_miss_logp=float(raw_cfg.get("miss_logp", -20.0) or -20.0),
        word_ngram_report_min_positions=int(raw_cfg.get("min_positions", 0) or 0),
        word_ngram_report_prefix_total_thresholds=tuple(
            raw_cfg.get("prefix_total_thresholds", ()) or ()
        ),
        resolve_repo_path_fn=_resolve_repo_path,
    )
    if scorer_cfg is None:
        return None
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
    seed_offset = int(
        phasec.get(
            "seed_offset",
            slice_signal_mod.ANALYSIS_PHASEC_SEED_OFFSET_FALLBACK,
        )
        or 0
    )
    return int(_solver_seed(run_config) + int(seed_offset))


def _phasec_rescue_cfg(run_config: Mapping[str, Any]) -> dict[str, Any]:
    phasec = _phasec_cfg(run_config)
    cfg = (phasec.get("cfg") or {}) if isinstance(phasec, Mapping) else {}
    return {
        "rescue_candidates": int(
            max(
                0,
                int(cfg.get("rescue_candidates", REPLAY_RESCUE_CANDIDATES_FALLBACK) or 0),
            )
        ),
        "rescue_slip_swaps": int(
            max(
                1,
                int(
                    cfg.get(
                        "rescue_slip_swaps",
                        slice_signal_mod.ANALYSIS_RESCUE_SLIP_SWAPS_FALLBACK,
                    )
                    or 0
                ),
            )
        ),
    }


def _score_plaintexts(
    *,
    scorer: Any,
    plaintext_rows: Sequence[np.ndarray] | np.ndarray,
    chunk_size: int,
    require_batch: bool,
) -> np.ndarray:
    scores, _stats = score_plaintexts_chunked(
        scorer=scorer,
        plaintexts=plaintext_rows,
        wli=None,
        chunk_size=int(max(1, int(chunk_size))),
        require_batch=bool(require_batch),
    )
    _ = _stats
    return np.asarray(scores, dtype=np.float64).reshape(-1)


def _score_single_plaintext(
    *,
    scorer: Any,
    plaintext_idx: Sequence[int] | np.ndarray,
    chunk_size: int,
    require_batch: bool,
) -> float:
    scores = _score_plaintexts(
        scorer=scorer,
        plaintext_rows=[np.asarray(plaintext_idx, dtype=np.uint8).reshape(-1)],
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
    )
    return float(scores[0]) if int(scores.size) > 0 else float("nan")


def _truth_match_ratio(lhs: Sequence[int] | np.ndarray, rhs: Sequence[int] | np.ndarray) -> float:
    lhs_arr = np.asarray(lhs, dtype=np.uint8).reshape(-1)
    rhs_arr = np.asarray(rhs, dtype=np.uint8).reshape(-1)
    if int(rhs_arr.size) <= 0:
        return float("nan")
    same = int(np.sum(lhs_arr[: int(rhs_arr.size)] == rhs_arr))
    return float(same) / float(rhs_arr.size)


def _truth_better(
    cand_match: float,
    cand_score: float,
    best_match: float,
    best_score: float,
) -> bool:
    if np.isfinite(cand_match) and np.isfinite(best_match):
        if float(cand_match) != float(best_match):
            return bool(float(cand_match) > float(best_match))
    if np.isfinite(cand_score) and np.isfinite(best_score):
        if float(cand_score) != float(best_score):
            return bool(float(cand_score) > float(best_score))
    if np.isfinite(cand_match) and (not np.isfinite(best_match)):
        return True
    if np.isfinite(cand_score) and (not np.isfinite(best_score)):
        return True
    return False


def _is_anchor_summary_row(row: Mapping[str, Any]) -> bool:
    lane = str(row.get("lane", "") or "").strip().lower()
    if lane == "anchor":
        return True
    source = str(row.get("source", "") or "").strip()
    if source.startswith("stage3_best"):
        return True
    start_idx = int(row.get("start_idx", 0) or 0)
    source_rank = int(row.get("source_rank", 0) or 0)
    return bool(int(start_idx) == 1 and int(source_rank) == 1)


def _apply_slice_slip(
    *,
    key_vals: Sequence[int],
    target_slice: int,
    swaps: int,
    rng_obj: np.random.Generator,
    alphabet_size: int,
) -> list[int]:
    return shared_apply_slice_slip(
        key_vals=key_vals,
        target_slice=int(target_slice),
        swaps=int(swaps),
        rng_obj=rng_obj,
        alphabet_size=int(alphabet_size),
    )


def _apply_slice_pair_swap(
    *,
    key_vals: Sequence[int],
    target_slice: int,
    pos_a: int,
    pos_b: int,
    alphabet_size: int,
) -> list[int]:
    return shared_apply_slice_pair_swap(
        key_vals=key_vals,
        target_slice=int(target_slice),
        pos_a=int(pos_a),
        pos_b=int(pos_b),
        alphabet_size=int(alphabet_size),
    )


def _score_sort_key(value: float) -> tuple[int, float]:
    return shared_score_sort_key(float(value))


def _landing_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return shared_landing_sort_key(row)


def _rank_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    return shared_rank_rows(rows, limit=int(limit))


def _score_band_shortlist(
    rows: Sequence[Mapping[str, Any]],
    *,
    score_eps: float,
) -> list[dict[str, Any]]:
    return shared_score_band_shortlist(rows, score_eps=float(score_eps))


def _row_score_gain(row: Mapping[str, Any], *, current_score: float) -> float:
    return shared_row_score_gain(row, current_score=float(current_score))


def _row_search_gain(row: Mapping[str, Any], *, current_search_score: float) -> float:
    return shared_row_search_gain(
        row,
        current_search_score=float(current_search_score),
    )


def _row_match_gain(row: Mapping[str, Any], *, current_match: float) -> float:
    return shared_row_match_gain(row, current_match=float(current_match))


def _lexical_rank_from_row(row: Mapping[str, Any]) -> tuple[float, float, float]:
    return shared_lexical_rank_from_row(row)


def _attach_word_ngram_rank(
    *,
    rows: Sequence[Mapping[str, Any]],
    scorer_word_ngram_report: Any | None,
    chunk_size: int,
    require_batch: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    cache: dict[tuple[int, ...], dict[str, Any]] = {}
    for row in rows:
        row_out = dict(row)
        key_t = tuple(map(int, row_out.get("key", []) or []))
        cached = cache.get(key_t, None)
        if cached is None:
            lexical_active = False
            lexical_trust = float("-inf")
            lexical_report_xent = float("nan")
            lexical_n_positions = 0
            if scorer_word_ngram_report is not None:
                pt = np.asarray(row_out.get("pt", []), dtype=np.uint8).reshape(-1)
                report = score_word_ngram_report_for_plaintext(
                    scorer_runtime=scorer_word_ngram_report,
                    plaintext_idx=pt,
                    wli=None,
                    require_batch_scoring=bool(require_batch),
                )
                _ = chunk_size
                lexical_fields = extract_word_ngram_report_fields(report)
                lexical_active = bool(lexical_fields.get("word_ngram_judge_active", False))
                lexical_trust_raw = lexical_fields.get("word_ngram_judge_trust_score", None)
                lexical_trust = (
                    float(lexical_trust_raw)
                    if lexical_trust_raw is not None and np.isfinite(float(lexical_trust_raw))
                    else float("-inf")
                )
                lexical_report_xent_raw = lexical_fields.get("word_ngram_judge_report_xent", None)
                lexical_report_xent = (
                    float(lexical_report_xent_raw)
                    if lexical_report_xent_raw is not None
                    else float("nan")
                )
                lexical_n_positions = int(
                    lexical_fields.get("word_ngram_judge_n_positions", 0) or 0
                )
            cached = dict(
                lexical_active=int(1 if lexical_active else 0),
                lexical_trust=float(lexical_trust),
                lexical_report_xent=float(lexical_report_xent),
                lexical_n_positions=int(lexical_n_positions),
            )
            cache[key_t] = dict(cached)
        row_out.update(dict(cached))
        out.append(row_out)
    return out


def _selector_sort_key(
    row: Mapping[str, Any],
    *,
    selector_mode: str,
    current_score: float,
    current_search_score: float,
) -> tuple[Any, ...]:
    score_gain = _row_score_gain(row, current_score=float(current_score))
    search_gain = _row_search_gain(row, current_search_score=float(current_search_score))
    key_t = tuple(map(int, row.get("key", []) or []))
    if str(selector_mode) == "baseline":
        return (
            _score_sort_key(float(row.get("score", float("nan")))),
            _score_sort_key(float(row.get("search_score", float("nan")))),
            _score_sort_key(float(score_gain)),
            key_t,
        )
    if str(selector_mode) == "top_score_then_search":
        return (
            _score_sort_key(float(search_gain)),
            _score_sort_key(float(score_gain)),
            _score_sort_key(float(row.get("score", float("nan")))),
            key_t,
        )
    if str(selector_mode) == "rescue_shallow_then_search":
        return (
            int(row.get("mini_search_step", 0) or 0),
            _score_sort_key(float(search_gain)),
            _score_sort_key(float(score_gain)),
            _score_sort_key(float(row.get("score", float("nan")))),
            key_t,
        )
    if str(selector_mode) == "score_band_then_lexical_then_search":
        return (
            tuple(-float(v) for v in _lexical_rank_from_row(row)),
            _score_sort_key(float(search_gain)),
            _score_sort_key(float(score_gain)),
            _score_sort_key(float(row.get("score", float("nan")))),
            key_t,
        )
    if str(selector_mode) == "gain_based":
        return (
            _score_sort_key(float(search_gain)),
            _score_sort_key(float(score_gain)),
            _score_sort_key(float(row.get("search_score", float("nan")))),
            key_t,
        )
    if str(selector_mode) == "pareto_shortlist":
        return (
            _score_sort_key(float(search_gain)),
            _score_sort_key(float(score_gain)),
            _score_sort_key(float(row.get("score", float("nan")))),
            key_t,
        )
    raise ValueError(f"unknown selector_mode={selector_mode!r}")


def _pareto_shortlist(
    rows: Sequence[Mapping[str, Any]],
    *,
    current_score: float,
    current_search_score: float,
) -> list[dict[str, Any]]:
    return shared_pareto_shortlist(
        rows,
        current_score=float(current_score),
        current_search_score=float(current_search_score),
    )


def _select_guard_passing_row(
    *,
    passing_rows: Sequence[Mapping[str, Any]],
    selector_mode: str,
    current_score: float,
    current_search_score: float,
) -> dict[str, Any] | None:
    return shared_select_guard_passing_row(
        passing_rows=passing_rows,
        selector_mode=str(selector_mode),
        current_score=float(current_score),
        current_search_score=float(current_search_score),
        score_band_eps=float(REPLAY_SELECTOR_TOP_SCORE_BAND_EPS),
    )


def _best_guard_truth_row(
    *,
    passing_rows: Sequence[Mapping[str, Any]],
    current_match: float,
) -> dict[str, Any] | None:
    truth_rows = [
        dict(row)
        for row in passing_rows
        if _row_match_gain(row, current_match=float(current_match)) > 0.0
    ]
    if not truth_rows:
        return None
    best_row = dict(truth_rows[0])
    for row in truth_rows[1:]:
        if _truth_better(
            float(row.get("match", float("nan"))),
            float(row.get("score", float("nan"))),
            float(best_row.get("match", float("nan"))),
            float(best_row.get("score", float("nan"))),
        ):
            best_row = dict(row)
            continue
        if (
            float(row.get("match", float("nan")))
            == float(best_row.get("match", float("nan")))
            and float(row.get("score", float("nan")))
            == float(best_row.get("score", float("nan")))
            and tuple(map(int, row.get("key", []) or []))
            < tuple(map(int, best_row.get("key", []) or []))
        ):
            best_row = dict(row)
    return best_row


def _score_key_rows(
    *,
    keys: Sequence[Sequence[int]],
    artifact: Mapping[str, Any],
    scorer_full: Any,
    scorer_search: Any,
    cipher: Any,
    chunk_size: int,
    require_batch: bool,
    target_plaintext_idx: np.ndarray,
) -> list[dict[str, Any]]:
    if not keys:
        return []
    pts, scores, _stats = decrypt_and_score_keys_chunked(
        cipher=cipher,
        ciphertext=np.asarray(artifact.get("ciphertext_idx", []), dtype=np.uint8).reshape(-1),
        keys=[list(map(int, key_vals)) for key_vals in keys],
        scorer=scorer_full,
        wli=None,
        chunk_size=int(max(1, min(int(chunk_size), len(keys)))),
        require_batch=bool(require_batch),
    )
    _ = _stats
    search_scores = _score_plaintexts(
        scorer=scorer_search,
        plaintext_rows=[
            np.asarray(pts[row_idx], dtype=np.uint8).reshape(-1)
            for row_idx in range(int(pts.shape[0]))
        ],
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
    )
    rows: list[dict[str, Any]] = []
    for row_idx, key_vals in enumerate(keys):
        if row_idx >= int(pts.shape[0]):
            continue
        pt = np.asarray(pts[row_idx], dtype=np.uint8).reshape(-1)
        rows.append(
            dict(
                key=list(map(int, key_vals)),
                pt=pt.copy(),
                score=(
                    float(scores[row_idx]) if row_idx < int(scores.size) else float("nan")
                ),
                search_score=(
                    float(search_scores[row_idx])
                    if row_idx < int(search_scores.size)
                    else float("nan")
                ),
                match=float(_truth_match_ratio(pt, target_plaintext_idx)),
            )
        )
    return rows


def _target_slice_active_positions(
    *,
    ciphertext_idx: np.ndarray,
    period: int,
    target_slice: int,
    alphabet_size: int,
    current_key: Sequence[int],
    probe_key: Sequence[int],
    top_symbols: int,
) -> list[int]:
    return shared_target_slice_active_positions(
        ciphertext_idx=np.asarray(ciphertext_idx, dtype=np.uint8).reshape(-1),
        period=int(period),
        target_slice=int(target_slice),
        alphabet_size=int(alphabet_size),
        current_key=current_key,
        probe_key=probe_key,
        top_symbols=int(top_symbols),
    )


def _run_slice_local_mini_search(
    *,
    artifact: Mapping[str, Any],
    current_key: Sequence[int],
    current_pt: np.ndarray,
    current_score: float,
    current_search_score: float,
    current_match: float,
    probe: Mapping[str, Any],
    scorer_full: Any,
    scorer_search: Any,
    cipher: Any,
    chunk_size: int,
    require_batch: bool,
    target_plaintext_idx: np.ndarray,
    final_keep: int,
) -> dict[str, Any]:
    target_slice = int(probe.get("target_slice", 0) or 0)
    probe_key = list(map(int, probe.get("probe_key", current_key) or current_key))
    probe_pt = np.asarray(probe.get("probe_plaintext", []), dtype=np.uint8).reshape(-1)
    probe_search_score = float("nan")
    if int(probe_pt.size) > 0:
        probe_search_score = _score_single_plaintext(
            scorer=scorer_search,
            plaintext_idx=probe_pt,
            chunk_size=int(chunk_size),
            require_batch=bool(require_batch),
        )
    mini_search = shared_run_slice_local_mini_search(
        current_key=current_key,
        current_pt=np.asarray(current_pt, dtype=np.uint8).reshape(-1),
        current_score=float(current_score),
        current_search_score=float(current_search_score),
        current_match=float(current_match),
        probe_key=probe_key,
        probe_pt=probe_pt,
        probe_score=float(probe.get("target_score", float("nan"))),
        probe_search_score=float(probe_search_score),
        probe_match=float(
            probe.get(
                "probe_match",
                _truth_match_ratio(probe_pt, target_plaintext_idx),
            )
        ),
        target_slice=int(target_slice),
        ciphertext_idx=np.asarray(artifact.get("ciphertext_idx", []), dtype=np.uint8).reshape(-1),
        period=int(max(1, int(artifact.get("period", 0) or 1))),
        alphabet_size=int(max(1, int(artifact.get("alphabet_size", 0) or 1))),
        top_symbols=int(REPLAY_MINI_SEARCH_TOP_SYMBOLS),
        beam_width=int(max(1, min(int(REPLAY_MINI_SEARCH_BEAM_WIDTH), int(max(1, int(final_keep)))))),
        steps=int(max(0, int(REPLAY_MINI_SEARCH_STEPS))),
        final_keep=int(max(1, int(final_keep))),
        keep_all_rows=bool(REPLAY_MINI_SEARCH_KEEP_ALL_ROWS),
        score_key_rows_fn=lambda keys: _score_key_rows(
            keys=keys,
            artifact=artifact,
            scorer_full=scorer_full,
            scorer_search=scorer_search,
            cipher=cipher,
            chunk_size=int(chunk_size),
            require_batch=bool(require_batch),
            target_plaintext_idx=target_plaintext_idx,
        ),
    )
    truth_best_row: dict[str, Any] | None = None
    for row in list(mini_search.get("collected_rows", []) or []):
        if truth_best_row is None or _truth_better(
            float(row.get("match", float("nan"))),
            float(row.get("score", float("nan"))),
            float(truth_best_row.get("match", float("nan"))),
            float(truth_best_row.get("score", float("nan"))),
        ):
            truth_best_row = dict(row)
    return dict(
        rows=[dict(row) for row in list(mini_search.get("rows", []) or [])],
        collected_row_count=int(mini_search.get("collected_row_count", 0) or 0),
        evals=int(mini_search.get("evals", 0) or 0),
        expanded_steps=int(mini_search.get("expanded_steps", 0) or 0),
        active_positions=list(mini_search.get("active_positions", []) or []),
        seed_count=int(mini_search.get("seed_count", 0) or 0),
        truth_best_row=(dict(truth_best_row) if truth_best_row is not None else None),
    )


def _select_probe_candidate(
    *,
    current_key: Sequence[int],
    current_score: float,
    start_idx: int,
    phase_seed: int,
    period: int,
    alphabet_size: int,
    rescue_slip_swaps: int,
    scorer_full: Any,
    cipher: Any,
    ciphertext_idx: Sequence[int] | np.ndarray,
    target_plaintext_idx: Sequence[int] | np.ndarray,
    chunk_size: int,
    require_batch: bool,
) -> dict[str, Any]:
    period_i = int(max(1, int(period)))
    current_key_t = tuple(map(int, current_key))
    probe_keys: list[list[int]] = []
    probe_meta: list[dict[str, Any]] = []
    for slice_idx in range(period_i):
        probe_seed = int(phase_seed) + int(start_idx) * 10007 + int(slice_idx) * 313
        probe_rng = np.random.default_rng(int(probe_seed))
        cand = _apply_slice_slip(
            key_vals=current_key,
            target_slice=int(slice_idx),
            swaps=int(rescue_slip_swaps),
            rng_obj=probe_rng,
            alphabet_size=int(alphabet_size),
        )
        cand_t = tuple(map(int, cand))
        if cand_t == current_key_t:
            continue
        probe_keys.append(list(cand))
        probe_meta.append(dict(slice_idx=int(slice_idx)))
    if not probe_keys:
        return dict(
            target_slice=0,
            target_score=float("nan"),
            target_score_gain=float("nan"),
            probe_key=list(map(int, current_key)),
            probe_plaintext=[],
            probe_match=float("nan"),
            probe_evals=0,
        )
    probe_pts, probe_scores, _stats = decrypt_and_score_keys_chunked(
        cipher=cipher,
        ciphertext=np.asarray(ciphertext_idx, dtype=np.uint8).reshape(-1),
        keys=probe_keys,
        scorer=scorer_full,
        wli=None,
        chunk_size=int(max(1, min(int(chunk_size), len(probe_keys)))),
        require_batch=bool(require_batch),
    )
    _ = _stats
    best_idx = 0
    best_score = float("nan")
    best_gain = float("nan")
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
    best_pt = (
        np.asarray(probe_pts[best_idx], dtype=np.uint8).reshape(-1)
        if best_idx < int(probe_pts.shape[0])
        else np.asarray([], dtype=np.uint8)
    )
    best_match = (
        _truth_match_ratio(best_pt, target_plaintext_idx)
        if int(best_pt.size) > 0
        else float("nan")
    )
    return dict(
        target_slice=int(probe_meta[best_idx]["slice_idx"]),
        target_score=float(best_score),
        target_score_gain=float(best_gain),
        probe_key=list(map(int, probe_keys[best_idx])),
        probe_plaintext=best_pt.astype(int).tolist(),
        probe_match=float(best_match),
        probe_evals=int(len(probe_keys)),
    )


def build_replay_starts(case: ArtifactCase) -> dict[str, Any]:
    artifact = dict(case.artifact)
    stage3_diag = dict(artifact.get("stage3_diagnostics", {}) or {})
    artifact_relpath = _repo_rel(case.artifact_path)
    run_id = str(case.run_dir.name)
    summaries = list(stage3_diag.get("phaseC_start_summaries", []) or [])
    topk_rows = list(artifact.get("stage3_topk", []) or [])
    by_hash: dict[str, dict[str, Any]] = {}
    by_rank: dict[int, dict[str, Any]] = {}
    for row in topk_rows:
        end_hash = str(row.get("end_hash", "") or "").strip()
        if end_hash:
            by_hash[end_hash] = dict(row)
        rank = int(row.get("rank", 0) or 0)
        if rank > 0:
            by_rank[rank] = dict(row)
    warnings: list[str] = []
    anchor_summary = next(
        (dict(row) for row in summaries if _is_anchor_summary_row(row)),
        None,
    )
    anchor_start: ReplayStart | None = None
    if anchor_summary is not None:
        anchor_hash = str(anchor_summary.get("candidate_hash", "") or "").strip()
        anchor_topk = by_hash.get(anchor_hash) or by_rank.get(1)
        if anchor_topk is not None:
            anchor_start = ReplayStart(
                artifact_relpath=str(artifact_relpath),
                run_id=str(run_id),
                start_idx=int(anchor_summary.get("start_idx", 0) or 0),
                lane="anchor",
                source=str(anchor_summary.get("source", "") or ""),
                source_rank=int(anchor_summary.get("source_rank", 0) or 0),
                candidate_hash=str(anchor_hash),
                key_idx=tuple(map(int, anchor_topk.get("key_idx", []) or [])),
                plaintext_idx=tuple(map(int, anchor_topk.get("plaintext_idx", []) or [])),
                init_match=float(anchor_summary.get("init_match", float("nan"))),
                init_score=float(anchor_summary.get("init_score", float("nan"))),
                init_search_score=float(
                    anchor_summary.get("init_search_score", float("nan"))
                ),
                live_rescue_attempted=int(
                    anchor_summary.get("rescue_attempted", 0) or 0
                ),
                live_rescue_applied=int(anchor_summary.get("rescue_applied", 0) or 0),
                live_rescue_guard_search_passed=int(
                    anchor_summary.get("rescue_guard_search_passed", 0) or 0
                ),
                live_rescue_target_slice=(
                    int(anchor_summary.get("rescue_target_slice"))
                    if anchor_summary.get("rescue_target_slice", None) is not None
                    else None
                ),
                live_overtook_anchor=int(
                    anchor_summary.get("overtook_anchor", 0) or 0
                ),
                live_became_global_best=int(
                    anchor_summary.get("became_global_best", 0) or 0
                ),
            )
            if str(anchor_summary.get("lane", "") or "").strip().lower() != "anchor":
                warnings.append(
                    f"{artifact_relpath}: inferred anchor summary from source/start_idx fallback"
                )
        else:
            warnings.append(f"{artifact_relpath}: missing anchor topk row for replay")

    challenger_starts: list[ReplayStart] = []
    for summary_row in summaries:
        source = str(summary_row.get("source", "") or "")
        source_rank = int(summary_row.get("source_rank", 0) or 0)
        if str(source) != "phaseB_topk":
            continue
        if int(source_rank) < int(REPLAY_PHASEB_TOPK_MIN_RANK):
            continue
        candidate_hash = str(summary_row.get("candidate_hash", "") or "").strip()
        topk_row = by_hash.get(candidate_hash) or by_rank.get(source_rank)
        if topk_row is None:
            warnings.append(
                f"{artifact_relpath}: missing phaseB_topk row for source_rank={source_rank}"
            )
            continue
        challenger_starts.append(
            ReplayStart(
                artifact_relpath=str(artifact_relpath),
                run_id=str(run_id),
                start_idx=int(summary_row.get("start_idx", 0) or 0),
                lane=str(summary_row.get("lane", "") or "challenger"),
                source=str(source),
                source_rank=int(source_rank),
                candidate_hash=str(candidate_hash),
                key_idx=tuple(map(int, topk_row.get("key_idx", []) or [])),
                plaintext_idx=tuple(map(int, topk_row.get("plaintext_idx", []) or [])),
                init_match=float(summary_row.get("init_match", float("nan"))),
                init_score=float(summary_row.get("init_score", float("nan"))),
                init_search_score=float(
                    summary_row.get("init_search_score", float("nan"))
                ),
                live_rescue_attempted=int(
                    summary_row.get("rescue_attempted", 0) or 0
                ),
                live_rescue_applied=int(summary_row.get("rescue_applied", 0) or 0),
                live_rescue_guard_search_passed=int(
                    summary_row.get("rescue_guard_search_passed", 0) or 0
                ),
                live_rescue_target_slice=(
                    int(summary_row.get("rescue_target_slice"))
                    if summary_row.get("rescue_target_slice", None) is not None
                    else None
                ),
                live_overtook_anchor=int(summary_row.get("overtook_anchor", 0) or 0),
                live_became_global_best=int(
                    summary_row.get("became_global_best", 0) or 0
                ),
            )
        )
    challenger_starts = sorted(
        challenger_starts,
        key=lambda row: (int(row.start_idx), int(row.source_rank)),
    )
    if REPLAY_MAX_CHALLENGERS_PER_ARTIFACT is not None:
        challenger_starts = challenger_starts[: int(REPLAY_MAX_CHALLENGERS_PER_ARTIFACT)]
    return dict(
        anchor_start=anchor_start,
        challenger_starts=challenger_starts,
        warnings=warnings,
    )


def replay_rescue_for_start(
    *,
    start: ReplayStart,
    artifact: Mapping[str, Any],
    phase_seed: int,
    rescue_candidates: int,
    rescue_slip_swaps: int,
    guard_max_drop_values: Sequence[float],
    scorer_full: Any,
    scorer_search: Any,
    scorer_word_ngram_report: Any | None,
    cipher: Any,
    chunk_size: int,
    require_batch: bool,
    anchor_start: ReplayStart | None,
) -> list[dict[str, Any]]:
    ciphertext_idx = np.asarray(artifact.get("ciphertext_idx", []), dtype=np.uint8).reshape(-1)
    target_plaintext_idx = np.asarray(
        artifact.get("target_plaintext_idx", []),
        dtype=np.uint8,
    ).reshape(-1)
    current_key = list(map(int, start.key_idx))
    current_pt = np.asarray(start.plaintext_idx, dtype=np.uint8).reshape(-1)
    current_score = float(start.init_score)
    if not np.isfinite(current_score):
        current_score = _score_single_plaintext(
            scorer=scorer_full,
            plaintext_idx=current_pt,
            chunk_size=int(chunk_size),
            require_batch=bool(require_batch),
        )
    current_search_score = float(start.init_search_score)
    if not np.isfinite(current_search_score):
        current_search_score = _score_single_plaintext(
            scorer=scorer_search,
            plaintext_idx=current_pt,
            chunk_size=int(chunk_size),
            require_batch=bool(require_batch),
        )
    current_match = float(start.init_match)
    if not np.isfinite(current_match):
        current_match = _truth_match_ratio(current_pt, target_plaintext_idx)

    probe = _select_probe_candidate(
        current_key=current_key,
        current_score=float(current_score),
        start_idx=int(start.start_idx),
        phase_seed=int(phase_seed),
        period=int(artifact.get("period", 0) or 0),
        alphabet_size=int(artifact.get("alphabet_size", 0) or 0),
        rescue_slip_swaps=int(rescue_slip_swaps),
        scorer_full=scorer_full,
        cipher=cipher,
        ciphertext_idx=ciphertext_idx,
        target_plaintext_idx=target_plaintext_idx,
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
    )

    mini_search = _run_slice_local_mini_search(
        artifact=artifact,
        current_key=current_key,
        current_pt=current_pt,
        current_score=float(current_score),
        current_search_score=float(current_search_score),
        current_match=float(current_match),
        probe=probe,
        scorer_full=scorer_full,
        scorer_search=scorer_search,
        cipher=cipher,
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
        target_plaintext_idx=target_plaintext_idx,
        final_keep=int(
            max(
                1,
                int(rescue_candidates) if int(rescue_candidates) > 0 else int(REPLAY_MINI_SEARCH_FINAL_KEEP),
            )
        ),
    )
    mini_search_truth_best = dict(mini_search.get("truth_best_row", {}) or {})

    landing_candidates: list[dict[str, Any]] = []
    probe_pt = np.asarray(probe.get("probe_plaintext", []), dtype=np.uint8).reshape(-1)
    if int(probe_pt.size) > 0:
        probe_search_score = _score_single_plaintext(
            scorer=scorer_search,
            plaintext_idx=probe_pt,
            chunk_size=int(chunk_size),
            require_batch=bool(require_batch),
        )
        landing_candidates.append(
            dict(
                landing_type="probe",
                key=list(map(int, probe.get("probe_key", current_key) or current_key)),
                pt=probe_pt.copy(),
                score=float(probe.get("target_score", float("nan"))),
                search_score=float(probe_search_score),
                match=float(
                    probe.get(
                        "probe_match",
                        _truth_match_ratio(probe_pt, target_plaintext_idx),
                    )
                ),
                target_slice=int(probe.get("target_slice", 0) or 0),
                mini_search_step=0,
                mini_search_parent_type="probe_seed",
                mini_search_swap_a=None,
                mini_search_swap_b=None,
                mini_search_active_position_count=int(
                    len(list(mini_search.get("active_positions", []) or []))
                ),
            )
        )
    for row in list(mini_search.get("rows", []) or []):
        landing_candidates.append(dict(row))
    landing_candidates = _attach_word_ngram_rank(
        rows=landing_candidates,
        scorer_word_ngram_report=scorer_word_ngram_report,
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
    )
    finite_candidate_search_scores = [
        float(row.get("search_score", float("nan")))
        for row in landing_candidates
        if np.isfinite(float(row.get("search_score", float("nan"))))
    ]
    best_candidate_search_score = (
        float(max(finite_candidate_search_scores))
        if finite_candidate_search_scores
        else float("nan")
    )
    guard_threshold_needed_for_any_pass = (
        max(0.0, float(current_search_score - best_candidate_search_score))
        if np.isfinite(current_search_score) and np.isfinite(best_candidate_search_score)
        else float("nan")
    )
    probe_search_score = float("nan")
    for row in landing_candidates:
        if str(row.get("landing_type", "")) == "probe":
            probe_search_score = float(row.get("search_score", float("nan")))
            break
    probe_search_score_gain = (
        float(probe_search_score - current_search_score)
        if np.isfinite(probe_search_score) and np.isfinite(current_search_score)
        else float("nan")
    )

    anchor_init_match = (
        float(anchor_start.init_match) if anchor_start is not None else float("nan")
    )
    anchor_init_score = (
        float(anchor_start.init_score) if anchor_start is not None else float("nan")
    )
    anchor_available = int(
        bool(
            anchor_start is not None
            and (
                np.isfinite(float(anchor_init_match))
                or np.isfinite(float(anchor_init_score))
            )
        )
    )
    final_best_match = float(artifact.get("best_match_ratio", float("nan")))
    final_best_score = float(artifact.get("best_score", float("nan")))

    out_rows: list[dict[str, Any]] = []
    for guard_max_drop in guard_max_drop_values:
        passing_rows: list[dict[str, Any]] = []
        reject_count = 0
        for row in landing_candidates:
            search_score = float(row.get("search_score", float("nan")))
            guard_pass = bool(
                np.isfinite(current_search_score)
                and np.isfinite(search_score)
                and float(search_score) >= float(current_search_score) - float(guard_max_drop)
            )
            if guard_pass:
                passing_rows.append(dict(row))
            else:
                reject_count += 1
        best_guard_truth_row = _best_guard_truth_row(
            passing_rows=passing_rows,
            current_match=float(current_match),
        )
        for selector_mode in REPLAY_SELECTOR_MODES:
            best_row = _select_guard_passing_row(
                passing_rows=passing_rows,
                selector_mode=str(selector_mode),
                current_score=float(current_score),
                current_search_score=float(current_search_score),
            )
            landing_key = list(map(int, current_key))
            landing_score = float(current_score)
            landing_match = float(current_match)
            landing_search_score = float(current_search_score)
            rescue_applied = 0
            landing_type = "current"
            if best_row is not None:
                landing_key = list(map(int, best_row.get("key", current_key)))
                landing_score = float(best_row.get("score", current_score))
                landing_match = float(best_row.get("match", current_match))
                landing_search_score = float(
                    best_row.get("search_score", current_search_score)
                )
                landing_type = str(best_row.get("landing_type", "current") or "current")
                rescue_applied = int(
                    1
                    if tuple(map(int, landing_key)) != tuple(map(int, current_key))
                    else 0
                )
            match_gain = (
                float(landing_match - float(current_match))
                if np.isfinite(landing_match) and np.isfinite(float(current_match))
                else float("nan")
            )
            score_gain = (
                float(landing_score - float(current_score))
                if np.isfinite(landing_score) and np.isfinite(float(current_score))
                else float("nan")
            )
            search_score_gain = (
                float(landing_search_score - float(current_search_score))
                if np.isfinite(landing_search_score)
                and np.isfinite(float(current_search_score))
                else float("nan")
            )
            best_guard_truth_match = float(
                best_guard_truth_row.get("match", float("nan"))
            ) if best_guard_truth_row is not None else float("nan")
            best_guard_truth_score = float(
                best_guard_truth_row.get("score", float("nan"))
            ) if best_guard_truth_row is not None else float("nan")
            best_guard_truth_search_score = float(
                best_guard_truth_row.get("search_score", float("nan"))
            ) if best_guard_truth_row is not None else float("nan")
            best_guard_truth_match_gain = (
                float(best_guard_truth_match - float(current_match))
                if np.isfinite(best_guard_truth_match)
                and np.isfinite(float(current_match))
                else float("nan")
            )
            best_guard_truth_score_gain = (
                float(best_guard_truth_score - float(current_score))
                if np.isfinite(best_guard_truth_score)
                and np.isfinite(float(current_score))
                else float("nan")
            )
            best_guard_truth_search_score_gain = (
                float(best_guard_truth_search_score - float(current_search_score))
                if np.isfinite(best_guard_truth_search_score)
                and np.isfinite(float(current_search_score))
                else float("nan")
            )
            best_guard_truth_lex = (
                _lexical_rank_from_row(best_guard_truth_row)
                if best_guard_truth_row is not None
                else (0.0, float("-inf"), float("-inf"))
            )
            landing_lex = (
                _lexical_rank_from_row(best_row)
                if best_row is not None
                else (0.0, float("-inf"), float("-inf"))
            )
            landing_matches_best_guard_truth = int(
                1
                if best_row is not None
                and best_guard_truth_row is not None
                and tuple(map(int, best_row.get("key", []) or []))
                == tuple(map(int, best_guard_truth_row.get("key", []) or []))
                else 0
            )
            selector_missed_better_truth = int(
                1
                if best_guard_truth_row is not None
                and (
                    (not np.isfinite(match_gain))
                    or (not np.isfinite(best_guard_truth_match_gain))
                    or float(match_gain) < float(best_guard_truth_match_gain)
                )
                else 0
            )
            selector_truth_regret = (
                float(best_guard_truth_match - landing_match)
                if best_guard_truth_row is not None
                and np.isfinite(best_guard_truth_match)
                and np.isfinite(float(landing_match))
                else float("nan")
            )
            score_up = bool(np.isfinite(score_gain) and float(score_gain) > 0.0)
            match_up = bool(np.isfinite(match_gain) and float(match_gain) > 0.0)
            match_down = bool(np.isfinite(match_gain) and float(match_gain) < 0.0)
            out_rows.append(
                dict(
                    artifact_relpath=str(start.artifact_relpath),
                    run_id=str(start.run_id),
                    selector_mode=str(selector_mode),
                    guard_max_drop=float(guard_max_drop),
                    start_idx=int(start.start_idx),
                    lane=str(start.lane),
                    source=str(start.source),
                    source_rank=int(start.source_rank),
                    candidate_hash=str(start.candidate_hash),
                    target_slice=int(probe.get("target_slice", 0) or 0),
                    probe_score_gain=float(probe.get("target_score_gain", float("nan"))),
                    probe_search_score_gain=float(probe_search_score_gain),
                    probe_evals=int(probe.get("probe_evals", 0) or 0),
                    mini_search_evals=int(mini_search.get("evals", 0) or 0),
                    mini_search_expanded_steps=int(
                        mini_search.get("expanded_steps", 0) or 0
                    ),
                    mini_search_seed_count=int(mini_search.get("seed_count", 0) or 0),
                    mini_search_pool_row_count=int(
                        mini_search.get("collected_row_count", 0) or 0
                    ),
                    mini_search_active_position_count=int(
                        len(list(mini_search.get("active_positions", []) or []))
                    ),
                    mini_search_truth_best_match=float(
                        mini_search_truth_best.get("match", float("nan"))
                    ),
                    mini_search_truth_best_score=float(
                        mini_search_truth_best.get("score", float("nan"))
                    ),
                    mini_search_truth_best_search_score=float(
                        mini_search_truth_best.get("search_score", float("nan"))
                    ),
                    mini_search_truth_best_step=int(
                        mini_search_truth_best.get("mini_search_step", 0) or 0
                    ),
                    mini_search_truth_best_gain=(
                        float(mini_search_truth_best.get("match", float("nan")) - float(current_match))
                        if np.isfinite(float(mini_search_truth_best.get("match", float("nan"))))
                        and np.isfinite(float(current_match))
                        else float("nan")
                    ),
                    rescue_candidates_total=int(len(landing_candidates)),
                    best_candidate_search_score=float(best_candidate_search_score),
                    guard_threshold_needed_for_any_pass=float(
                        guard_threshold_needed_for_any_pass
                    ),
                    guard_pass_candidate_count=int(len(passing_rows)),
                    guard_reject_candidate_count=int(reject_count),
                    guard_pass_start=int(1 if passing_rows else 0),
                    rescue_applied=int(rescue_applied),
                    landing_type=str(landing_type),
                    landing_matches_mini_search_truth_best=int(
                        1
                        if best_row is not None
                        and mini_search_truth_best
                        and tuple(map(int, best_row.get("key", []) or []))
                        == tuple(map(int, mini_search_truth_best.get("key", []) or []))
                        else 0
                    ),
                    best_guard_truth_available=int(1 if best_guard_truth_row is not None else 0),
                    best_guard_truth_match=float(best_guard_truth_match),
                    best_guard_truth_score=float(best_guard_truth_score),
                    best_guard_truth_search_score=float(best_guard_truth_search_score),
                    best_guard_truth_match_gain=float(best_guard_truth_match_gain),
                    best_guard_truth_score_gain=float(best_guard_truth_score_gain),
                    best_guard_truth_search_score_gain=float(
                        best_guard_truth_search_score_gain
                    ),
                    best_guard_truth_landing_type=(
                        str(best_guard_truth_row.get("landing_type", "") or "")
                        if best_guard_truth_row is not None
                        else ""
                    ),
                    best_guard_truth_mini_search_step=(
                        int(best_guard_truth_row.get("mini_search_step", 0) or 0)
                        if best_guard_truth_row is not None
                        else 0
                    ),
                    best_guard_truth_mini_search_parent_type=(
                        str(best_guard_truth_row.get("mini_search_parent_type", "") or "")
                        if best_guard_truth_row is not None
                        else ""
                    ),
                    best_guard_truth_mini_search_swap_a=(
                        int(best_guard_truth_row.get("mini_search_swap_a"))
                        if best_guard_truth_row is not None
                        and best_guard_truth_row.get("mini_search_swap_a", None) is not None
                        else None
                    ),
                    best_guard_truth_mini_search_swap_b=(
                        int(best_guard_truth_row.get("mini_search_swap_b"))
                        if best_guard_truth_row is not None
                        and best_guard_truth_row.get("mini_search_swap_b", None) is not None
                        else None
                    ),
                    best_guard_truth_lexical_active=int(best_guard_truth_lex[0]),
                    best_guard_truth_lexical_trust=float(best_guard_truth_lex[1]),
                    best_guard_truth_lexical_report_xent_sort=float(best_guard_truth_lex[2]),
                    landing_matches_best_guard_truth=int(landing_matches_best_guard_truth),
                    selector_missed_better_truth=int(selector_missed_better_truth),
                    selector_truth_regret=float(selector_truth_regret),
                    landing_mini_search_step=(
                        int(best_row.get("mini_search_step", 0) or 0)
                        if best_row is not None
                        else 0
                    ),
                    landing_mini_search_parent_type=(
                        str(best_row.get("mini_search_parent_type", "") or "")
                        if best_row is not None
                        else ""
                    ),
                    landing_mini_search_swap_a=(
                        int(best_row.get("mini_search_swap_a"))
                        if best_row is not None
                        and best_row.get("mini_search_swap_a", None) is not None
                        else None
                    ),
                    landing_mini_search_swap_b=(
                        int(best_row.get("mini_search_swap_b"))
                        if best_row is not None
                        and best_row.get("mini_search_swap_b", None) is not None
                        else None
                    ),
                    init_match=float(current_match),
                    landing_match=float(landing_match),
                    match_gain=float(match_gain),
                    init_score=float(current_score),
                    landing_score=float(landing_score),
                    score_gain=float(score_gain),
                    init_search_score=float(current_search_score),
                    landing_search_score=float(landing_search_score),
                    search_score_gain=float(search_score_gain),
                    landing_lexical_active=int(landing_lex[0]),
                    landing_lexical_trust=float(landing_lex[1]),
                    landing_lexical_report_xent_sort=float(landing_lex[2]),
                    truth_match_improved=int(1 if match_up else 0),
                    score_up_match_not_up=int(1 if score_up and (not match_up) else 0),
                    score_up_match_down=int(1 if score_up and match_down else 0),
                    anchor_available=int(anchor_available),
                    overtook_anchor_init=int(
                        1
                        if int(anchor_available) > 0
                        and _truth_better(
                            float(landing_match),
                            float(landing_score),
                            float(anchor_init_match),
                            float(anchor_init_score),
                        )
                        else 0
                    ),
                    overtook_anchor_final=int(
                        1
                        if _truth_better(
                            float(landing_match),
                            float(landing_score),
                            float(final_best_match),
                            float(final_best_score),
                        )
                        else 0
                    ),
                    live_rescue_attempted=int(start.live_rescue_attempted),
                    live_rescue_applied=int(start.live_rescue_applied),
                    live_rescue_guard_search_passed=int(
                        start.live_rescue_guard_search_passed
                    ),
                    live_rescue_target_slice=(
                        int(start.live_rescue_target_slice)
                        if start.live_rescue_target_slice is not None
                        else None
                    ),
                    live_overtook_anchor=int(start.live_overtook_anchor),
                    live_became_global_best=int(start.live_became_global_best),
                )
            )
    return out_rows


def summarize_replay_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, float], list[Mapping[str, Any]]] = {}
    for row in rows:
        key = (
            str(row.get("selector_mode", "baseline") or "baseline"),
            float(row.get("guard_max_drop", 0.0)),
        )
        grouped.setdefault(key, []).append(row)
    out: list[dict[str, Any]] = []
    for selector_mode, guard_max_drop in sorted(grouped.keys()):
        bucket = list(grouped[(selector_mode, guard_max_drop)])
        out.append(
            dict(
                selector_mode=str(selector_mode),
                guard_max_drop=float(guard_max_drop),
                replay_row_count=int(len(bucket)),
                artifact_count=int(len({str(row.get("artifact_relpath", "")) for row in bucket})),
                guard_pass_start_count=int(
                    sum(int(row.get("guard_pass_start", 0) or 0) for row in bucket)
                ),
                rescue_applied_count=int(
                    sum(int(row.get("rescue_applied", 0) or 0) for row in bucket)
                ),
                guard_pass_candidate_total=int(
                    sum(int(row.get("guard_pass_candidate_count", 0) or 0) for row in bucket)
                ),
                guard_reject_candidate_total=int(
                    sum(int(row.get("guard_reject_candidate_count", 0) or 0) for row in bucket)
                ),
                truth_match_improved_count=int(
                    sum(int(row.get("truth_match_improved", 0) or 0) for row in bucket)
                ),
                mini_search_truth_improve_available_count=int(
                    sum(
                        1
                        for row in bucket
                        if float(row.get("mini_search_truth_best_gain", float("nan"))) > 0.0
                    )
                ),
                mini_search_truth_best_pass_guard_count=int(
                    sum(
                        1
                        for row in bucket
                        if np.isfinite(float(row.get("init_search_score", float("nan"))))
                        and np.isfinite(
                            float(
                                row.get(
                                    "mini_search_truth_best_search_score",
                                    float("nan"),
                                )
                            )
                        )
                        and float(
                            row.get("mini_search_truth_best_search_score", float("nan"))
                        )
                        >= float(row.get("init_search_score", float("nan")))
                        - float(guard_max_drop)
                    )
                ),
                landing_matches_truth_best_count=int(
                    sum(
                        int(row.get("landing_matches_mini_search_truth_best", 0) or 0)
                        for row in bucket
                    )
                ),
                best_guard_truth_available_count=int(
                    sum(int(row.get("best_guard_truth_available", 0) or 0) for row in bucket)
                ),
                landing_lexical_active_count=int(
                    sum(int(row.get("landing_lexical_active", 0) or 0) for row in bucket)
                ),
                best_guard_truth_lexical_active_count=int(
                    sum(
                        int(row.get("best_guard_truth_lexical_active", 0) or 0)
                        for row in bucket
                    )
                ),
                landing_matches_best_guard_truth_count=int(
                    sum(
                        int(row.get("landing_matches_best_guard_truth", 0) or 0)
                        for row in bucket
                    )
                ),
                selector_missed_better_truth_count=int(
                    sum(
                        int(row.get("selector_missed_better_truth", 0) or 0)
                        for row in bucket
                    )
                ),
                selector_truth_regret_sum=float(
                    sum(
                        float(row.get("selector_truth_regret", 0.0) or 0.0)
                        for row in bucket
                        if np.isfinite(float(row.get("selector_truth_regret", float("nan"))))
                    )
                ),
                anchor_available_start_count=int(
                    sum(int(row.get("anchor_available", 0) or 0) for row in bucket)
                ),
                overtook_anchor_init_count=int(
                    sum(int(row.get("overtook_anchor_init", 0) or 0) for row in bucket)
                ),
                overtook_anchor_final_count=int(
                    sum(int(row.get("overtook_anchor_final", 0) or 0) for row in bucket)
                ),
                score_up_match_not_up_count=int(
                    sum(int(row.get("score_up_match_not_up", 0) or 0) for row in bucket)
                ),
                score_up_match_down_count=int(
                    sum(int(row.get("score_up_match_down", 0) or 0) for row in bucket)
                ),
            )
        )
    return out


def summarize_artifact_threshold_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, float], list[Mapping[str, Any]]] = {}
    for row in rows:
        key = (
            str(row.get("artifact_relpath", "")),
            str(row.get("selector_mode", "baseline") or "baseline"),
            float(row.get("guard_max_drop", 0.0)),
        )
        grouped.setdefault(key, []).append(row)
    out: list[dict[str, Any]] = []
    for artifact_relpath, selector_mode, guard_max_drop in sorted(grouped.keys()):
        bucket = list(grouped[(artifact_relpath, selector_mode, guard_max_drop)])
        out.append(
            dict(
                artifact_relpath=str(artifact_relpath),
                selector_mode=str(selector_mode),
                guard_max_drop=float(guard_max_drop),
                replay_row_count=int(len(bucket)),
                guard_pass_start_count=int(
                    sum(int(row.get("guard_pass_start", 0) or 0) for row in bucket)
                ),
                rescue_applied_count=int(
                    sum(int(row.get("rescue_applied", 0) or 0) for row in bucket)
                ),
                truth_match_improved_count=int(
                    sum(int(row.get("truth_match_improved", 0) or 0) for row in bucket)
                ),
                best_guard_truth_available_count=int(
                    sum(int(row.get("best_guard_truth_available", 0) or 0) for row in bucket)
                ),
                selector_missed_better_truth_count=int(
                    sum(
                        int(row.get("selector_missed_better_truth", 0) or 0)
                        for row in bucket
                    )
                ),
                overtook_anchor_final_count=int(
                    sum(int(row.get("overtook_anchor_final", 0) or 0) for row in bucket)
                ),
            )
        )
    return out


def build_miss_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    selector_modes: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    allowed_modes = (
        {str(mode) for mode in selector_modes}
        if selector_modes is not None
        else None
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        selector_mode = str(row.get("selector_mode", "baseline") or "baseline")
        if allowed_modes is not None and selector_mode not in allowed_modes:
            continue
        if int(row.get("selector_missed_better_truth", 0) or 0) != 1:
            continue
        out.append(dict(row))
    return out


def analyze_artifact_case(
    case: ArtifactCase,
    *,
    guard_max_drop_values: Sequence[float],
    chunk_size: int = ANALYSIS_BATCH_CHUNK_SIZE,
    require_batch: bool = ANALYSIS_REQUIRE_BATCH_SCORING,
) -> dict[str, Any]:
    artifact = dict(case.artifact)
    run_config = dict(case.run_config)
    artifact_relpath = _repo_rel(case.artifact_path)
    replay_inputs = build_replay_starts(case)
    warnings = list(replay_inputs.get("warnings", []))
    anchor_start = replay_inputs.get("anchor_start", None)
    challenger_starts = list(replay_inputs.get("challenger_starts", []))
    if anchor_start is None:
        warnings.append(f"{artifact_relpath}: missing anchor start for replay")
    if not challenger_starts:
        warnings.append(f"{artifact_relpath}: no challenger starts for replay")
        return dict(
            artifact_relpath=str(artifact_relpath),
            run_id=str(case.run_dir.name),
            replay_rows=[],
            warnings=warnings,
        )
    scorer_full = _build_stage3_scorer_runtime(
        artifact=artifact,
        run_config=run_config,
        scorer_key="scorer",
    )
    scorer_search = _build_stage3_scorer_runtime(
        artifact=artifact,
        run_config=run_config,
        scorer_key="search_scorer",
    )
    scorer_word_ngram_report = _build_stage3_word_ngram_report_runtime(
        artifact=artifact,
        run_config=run_config,
    )
    cipher = _build_cipher(artifact)
    phase_seed = int(_phasec_seed(run_config))
    rescue_cfg = _phasec_rescue_cfg(run_config)
    replay_rows: list[dict[str, Any]] = []
    for start in challenger_starts:
        replay_rows.extend(
            replay_rescue_for_start(
                start=start,
                artifact=artifact,
                phase_seed=int(phase_seed),
                rescue_candidates=int(rescue_cfg["rescue_candidates"]),
                rescue_slip_swaps=int(rescue_cfg["rescue_slip_swaps"]),
                guard_max_drop_values=guard_max_drop_values,
                scorer_full=scorer_full,
                scorer_search=scorer_search,
                scorer_word_ngram_report=scorer_word_ngram_report,
                cipher=cipher,
                chunk_size=int(chunk_size),
                require_batch=bool(require_batch),
                anchor_start=anchor_start,
            )
        )
    return dict(
        artifact_relpath=str(artifact_relpath),
        run_id=str(case.run_dir.name),
        replay_rows=replay_rows,
        warnings=warnings,
    )


def main() -> None:
    cases = discover_artifact_cases()
    label = f"{_utc_label()}_{RUN_LABEL}"
    output_dir = OUTPUT_ROOT / label
    output_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    artifact_rows: list[dict[str, Any]] = []
    for case in cases:
        result = analyze_artifact_case(
            case,
            guard_max_drop_values=REPLAY_GUARD_MAX_DROP_VALUES,
            chunk_size=int(ANALYSIS_BATCH_CHUNK_SIZE),
            require_batch=bool(ANALYSIS_REQUIRE_BATCH_SCORING),
        )
        all_rows.extend(list(result.get("replay_rows", [])))
        warnings.extend(list(result.get("warnings", [])))
        artifact_rows.append(
            dict(
                artifact_relpath=str(result.get("artifact_relpath", "")),
                run_id=str(result.get("run_id", "")),
                replay_row_count=int(len(result.get("replay_rows", []))),
                warning_count=int(len(result.get("warnings", []))),
            )
        )

    threshold_summary_rows = summarize_replay_rows(all_rows)
    artifact_threshold_rows = summarize_artifact_threshold_rows(all_rows)
    miss_rows = build_miss_rows(all_rows)
    miss_rows_top_score_then_search = build_miss_rows(
        all_rows,
        selector_modes=("top_score_then_search",),
    )
    miss_rows_score_band_then_lexical_then_search = build_miss_rows(
        all_rows,
        selector_modes=("score_band_then_lexical_then_search",),
    )
    summary = dict(
        run_label=str(RUN_LABEL),
        guard_max_drop_values=[float(v) for v in REPLAY_GUARD_MAX_DROP_VALUES],
        selector_modes=[str(v) for v in REPLAY_SELECTOR_MODES],
        selector_top_score_band_eps=float(REPLAY_SELECTOR_TOP_SCORE_BAND_EPS),
        mini_search_steps=int(REPLAY_MINI_SEARCH_STEPS),
        mini_search_beam_width=int(REPLAY_MINI_SEARCH_BEAM_WIDTH),
        mini_search_top_symbols=int(REPLAY_MINI_SEARCH_TOP_SYMBOLS),
        mini_search_final_keep=int(REPLAY_MINI_SEARCH_FINAL_KEEP),
        mini_search_keep_all_rows=int(1 if REPLAY_MINI_SEARCH_KEEP_ALL_ROWS else 0),
        discovered_artifact_count=int(len(cases)),
        replay_artifact_count=int(
            len({str(row.get("artifact_relpath", "")) for row in all_rows})
        ),
        replay_row_count=int(len(all_rows)),
        miss_row_count=int(len(miss_rows)),
        miss_row_top_score_then_search_count=int(
            len(miss_rows_top_score_then_search)
        ),
        miss_row_score_band_then_lexical_then_search_count=int(
            len(miss_rows_score_band_then_lexical_then_search)
        ),
        threshold_summary_rows=threshold_summary_rows,
        warnings=warnings,
    )

    (output_dir / "summary.json").write_text(
        json.dumps(_jsonify(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_csv(output_dir / "artifact_summary.csv", artifact_rows)
    _write_csv(output_dir / "threshold_summary.csv", threshold_summary_rows)
    _write_csv(output_dir / "artifact_threshold_summary.csv", artifact_threshold_rows)
    _write_csv(output_dir / "replay_rows.csv", all_rows)
    _write_csv(output_dir / "miss_rows.csv", miss_rows)
    _write_csv(
        output_dir / "miss_rows_top_score_then_search.csv",
        miss_rows_top_score_then_search,
    )
    _write_csv(
        output_dir / "miss_rows_score_band_then_lexical_then_search.csv",
        miss_rows_score_band_then_lexical_then_search,
    )
    print(
        json.dumps(
            _jsonify(
                dict(
                    output_dir=_repo_rel(output_dir),
                    discovered_artifact_count=int(len(cases)),
                    replay_artifact_count=int(
                        len({str(row.get("artifact_relpath", "")) for row in all_rows})
                    ),
                    replay_row_count=int(len(all_rows)),
                    miss_row_count=int(len(miss_rows)),
                    warnings=int(len(warnings)),
                )
            ),
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
