from __future__ import annotations

import cProfile
import csv
import io
import json
import pstats
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rune_decrypter_prime.api import Direction
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Device
from tools.benchmarks.periodic_sub_trans.common.batch_eval import (
    BatchEvalStats,
    score_plaintexts_chunked,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_config import (
    STAGE3_TUNING_PRESETS,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runner_defaults import (
    _discover_word_ngram_sqlite_path,
)
from tools.benchmarks.periodic_sub_trans.no_wli.scoring_experiment_config import (
    build_stage3_experiment_cfg,
    build_word_ngram_report_cfg,
    stage3_char4_pct_baseline_cfg,
)
from tools.benchmarks.periodic_sub_trans.no_wli.word_ngram_report import (
    extract_word_ngram_report_fields,
)
from tools.benchmarks.periodic_sub_trans.no_wli.build_output_catalog import (
    refresh_catalog_safely,
)


RUN_LABEL = "profile_word_ngram_tiebreak_v1"
OUTPUT_ROOT = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "word_ngram_tiebreak_profile"
)
PREFERRED_FINAL_INSTANCE = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260311T145832806343Z__bench_solve_pipeline_no_wli__638b3f0/"
    "final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed511.json"
)
FINAL_INSTANCE_GLOBS: tuple[str, ...] = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/*/final_instances/"
    "fixture_fixture_001_p9_c3_l1000__text0__seed511.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/*/final_instances/"
    "fixture_fixture_001_p9_c3_l1000__text0__seed*.json",
)
ACTIVE_TUNING_PRESET_ID = "lexical_phasec_proof_single"
SCORER_IMPL = "torch"
SCORING_EXPERIMENT_PROFILE = "c_min_late"
SCORING_EXPERIMENT_SPAN_ASSETS_DIR = Path("assets/scoring/span_hamming_nose_assets_v1")
SCORING_EXPERIMENT_SPAN_COVERAGE_MIN = 0.05
SCORING_EXPERIMENT_SPAN_QUALITY_MIN = 0.05
SCORING_EXPERIMENT_C_CHAR_PCT_MIN = 0.70
PREFIX_LENGTHS: tuple[int, ...] = (250, 500, 1000)
EXACT_REPEATS = 6
BATCH_REPEATS = 24
BATCH_CHUNK_SIZES: tuple[int, ...] = (1, 8, 32)
PROFILE_REPEATS = 32
PROFILE_SCENARIO_NAME = "final_best_full_1000"
PROFILE_TOP_N = 40
REQUIRE_BATCH_SCORING = True
WARMUP_CALLS = 2


@dataclass(frozen=True)
class Scenario:
    name: str
    source: str
    length: int
    plaintext_idx: np.ndarray


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _as_u8(values: Sequence[int] | np.ndarray) -> np.ndarray:
    return np.asarray(values, dtype=np.uint8).reshape(-1)


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
        try:
            return str(value.relative_to(REPO_ROOT))
        except Exception:
            return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def discover_final_instance_path() -> Path:
    preferred = REPO_ROOT / PREFERRED_FINAL_INSTANCE
    if preferred.exists():
        return preferred
    candidates: list[Path] = []
    for pattern in FINAL_INSTANCE_GLOBS:
        candidates.extend(REPO_ROOT.glob(pattern))
    existing = [path for path in candidates if path.exists()]
    if not existing:
        raise FileNotFoundError(
            "No suitable final-instance artifact found for p9/c3 word-ngram profiling"
        )
    existing.sort(key=lambda path: (path.stat().st_mtime, str(path)))
    return existing[-1]


def load_final_instance_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_benchmark_scenarios(
    payload: dict[str, Any],
    *,
    prefix_lengths: Sequence[int],
) -> list[Scenario]:
    target = _as_u8(payload["target_plaintext_idx"])
    final_best = _as_u8(payload["final_best_plaintext_idx"])
    stage2_topk = list(payload.get("stage2_topk", []))
    stage2_rank1 = _as_u8(stage2_topk[0]["plaintext_idx"]) if stage2_topk else final_best

    scenarios: list[Scenario] = [
        Scenario(
            name=f"target_full_{int(target.size)}",
            source="target_plaintext_idx",
            length=int(target.size),
            plaintext_idx=target,
        ),
        Scenario(
            name=f"final_best_full_{int(final_best.size)}",
            source="final_best_plaintext_idx",
            length=int(final_best.size),
            plaintext_idx=final_best,
        ),
        Scenario(
            name=f"stage2_rank1_full_{int(stage2_rank1.size)}",
            source="stage2_topk[0].plaintext_idx",
            length=int(stage2_rank1.size),
            plaintext_idx=stage2_rank1,
        ),
    ]

    for prefix_len in prefix_lengths:
        use_len = min(int(prefix_len), int(target.size), int(final_best.size))
        if use_len <= 0:
            continue
        scenarios.append(
            Scenario(
                name=f"target_prefix_{use_len}",
                source=f"target_plaintext_idx[:{use_len}]",
                length=use_len,
                plaintext_idx=np.ascontiguousarray(target[:use_len], dtype=np.uint8),
            )
        )
        scenarios.append(
            Scenario(
                name=f"final_best_prefix_{use_len}",
                source=f"final_best_plaintext_idx[:{use_len}]",
                length=use_len,
                plaintext_idx=np.ascontiguousarray(final_best[:use_len], dtype=np.uint8),
            )
        )

    deduped: list[Scenario] = []
    seen_names: set[str] = set()
    for scenario in scenarios:
        if scenario.name in seen_names:
            continue
        seen_names.add(scenario.name)
        deduped.append(scenario)
    preferred_order = {
        "final_best_full_1000": 0,
        "target_full_1000": 1,
        "stage2_rank1_full_1000": 2,
        "final_best_prefix_500": 3,
        "target_prefix_500": 4,
        "final_best_prefix_250": 5,
        "target_prefix_250": 6,
    }
    deduped.sort(key=lambda scenario: (preferred_order.get(scenario.name, 999), scenario.name))
    return deduped


def build_word_ngram_runtime(
    *,
    period: int,
    columns: int,
    alphabet_size: int,
    order: str,
    preset: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    direction = Direction.LTR
    cfg_full = CipherConfig(
        name="periodic_columnar",
        ciphertext=[],
        period=int(period),
        columns=int(columns),
        alphabet_size=int(alphabet_size),
        key_length=int(period) * int(alphabet_size) + int(columns),
        order=str(order),
        encoding_dir=direction,
        wli_data=[],
        device=Device.CPU,
    )
    baseline_cfg = stage3_char4_pct_baseline_cfg(scorer_impl=SCORER_IMPL)
    scorer_basin_judge_cfg = build_stage3_experiment_cfg(
        profile_name=SCORING_EXPERIMENT_PROFILE,
        direction=direction,
        span_assets_dir=REPO_ROOT / SCORING_EXPERIMENT_SPAN_ASSETS_DIR,
        char_pct_min_override=None,
        disable_char_pct_gate=True,
        scoring_experiment_span_coverage_min=SCORING_EXPERIMENT_SPAN_COVERAGE_MIN,
        scoring_experiment_span_quality_min=SCORING_EXPERIMENT_SPAN_QUALITY_MIN,
        scoring_experiment_c_char_pct_min=SCORING_EXPERIMENT_C_CHAR_PCT_MIN,
        baseline_cfg=baseline_cfg,
    )
    sqlite_path = _discover_word_ngram_sqlite_path(repo_root=REPO_ROOT)
    if sqlite_path is None:
        raise FileNotFoundError("Word-ngram sqlite asset could not be discovered")
    report_min_positions = int(
        preset.get("force_word_ngram_report_min_positions", 12)
    )
    scorer_cfg = build_word_ngram_report_cfg(
        base_cfg=scorer_basin_judge_cfg,
        direction=direction,
        word_ngram_report_enabled=True,
        word_ngram_report_sqlite_path=sqlite_path,
        word_ngram_report_alpha=0.4,
        word_ngram_report_miss_logp=-20.0,
        word_ngram_report_min_positions=report_min_positions,
        word_ngram_report_prefix_total_thresholds=(1, 10, 100),
        resolve_repo_path_fn=lambda path_like: (
            None
            if path_like is None
            else (
                path_like
                if Path(path_like).is_absolute()
                else REPO_ROOT / Path(path_like)
            )
        ),
    )
    scorer_runtime = build_scorer(cfg_full, ScoringConfig(**scorer_cfg))
    return scorer_runtime, dict(scorer_cfg)


def _merge_stats(parts: Iterable[BatchEvalStats]) -> BatchEvalStats:
    total = BatchEvalStats()
    for part in parts:
        total.candidates += int(part.candidates)
        total.batch_calls += int(part.batch_calls)
        total.scalar_fallback_calls += int(part.scalar_fallback_calls)
        total.decrypt_seconds += float(part.decrypt_seconds)
        total.score_seconds += float(part.score_seconds)
    return total


def execute_exact_single_candidate_calls(
    *,
    scorer_runtime: Any,
    plaintext_idx: np.ndarray,
    repeats: int,
) -> tuple[float, BatchEvalStats, dict[str, Any], float]:
    parts: list[BatchEvalStats] = []
    last_report: dict[str, Any] = {}
    last_score = float("nan")
    start = time.perf_counter()
    for _ in range(int(repeats)):
        score_arr, stats_obj = score_plaintexts_chunked(
            scorer=scorer_runtime,
            plaintexts=[plaintext_idx],
            wli=None,
            chunk_size=1,
            require_batch=REQUIRE_BATCH_SCORING,
        )
        parts.append(stats_obj)
        last_score = float(score_arr[0]) if int(score_arr.size) > 0 else float("nan")
        try:
            stats_payload = scorer_runtime.last_stats()
        except Exception:
            stats_payload = {}
        last_report = extract_word_ngram_report_fields(stats_payload)
    elapsed = float(time.perf_counter() - start)
    return elapsed, _merge_stats(parts), last_report, last_score


def execute_batched_candidate_calls(
    *,
    scorer_runtime: Any,
    plaintext_idx: np.ndarray,
    repeats: int,
    chunk_size: int,
) -> tuple[float, BatchEvalStats, dict[str, Any], float]:
    matrix = np.repeat(plaintext_idx.reshape(1, -1), int(repeats), axis=0)
    start = time.perf_counter()
    score_arr, stats_obj = score_plaintexts_chunked(
        scorer=scorer_runtime,
        plaintexts=matrix,
        wli=None,
        chunk_size=int(chunk_size),
        require_batch=REQUIRE_BATCH_SCORING,
    )
    elapsed = float(time.perf_counter() - start)
    try:
        stats_payload = scorer_runtime.last_stats()
    except Exception:
        stats_payload = {}
    report = extract_word_ngram_report_fields(stats_payload)
    last_score = float(score_arr[-1]) if int(score_arr.size) > 0 else float("nan")
    return elapsed, stats_obj, report, last_score


def benchmark_exact_path(
    *,
    scorer_runtime: Any,
    scenario: Scenario,
    repeats: int,
) -> dict[str, Any]:
    for _ in range(WARMUP_CALLS):
        execute_exact_single_candidate_calls(
            scorer_runtime=scorer_runtime,
            plaintext_idx=scenario.plaintext_idx,
            repeats=1,
        )
    elapsed, stats_obj, report, last_score = execute_exact_single_candidate_calls(
        scorer_runtime=scorer_runtime,
        plaintext_idx=scenario.plaintext_idx,
        repeats=repeats,
    )
    return {
        "scenario": scenario.name,
        "source": scenario.source,
        "length": int(scenario.length),
        "repeats": int(repeats),
        "elapsed_seconds": elapsed,
        "per_call_ms": (1000.0 * elapsed / int(repeats)),
        "calls_per_second": (float(repeats) / elapsed) if elapsed > 0.0 else float("nan"),
        "batch_calls": int(stats_obj.batch_calls),
        "scalar_fallback_calls": int(stats_obj.scalar_fallback_calls),
        "score_seconds": float(stats_obj.score_seconds),
        "last_score": float(last_score),
        "word_ngram_judge_active": bool(report.get("word_ngram_judge_active", False)),
        "word_ngram_judge_n_positions": int(
            report.get("word_ngram_judge_n_positions", 0) or 0
        ),
        "word_ngram_judge_report_xent": report.get("word_ngram_judge_report_xent"),
        "word_ngram_judge_trust_score": report.get("word_ngram_judge_trust_score"),
        "word_ngram_judge_trust_tier": str(
            report.get("word_ngram_judge_trust_tier", "") or ""
        ),
    }


def benchmark_batch_path(
    *,
    scorer_runtime: Any,
    scenario: Scenario,
    repeats: int,
    chunk_size: int,
) -> dict[str, Any]:
    for _ in range(WARMUP_CALLS):
        execute_batched_candidate_calls(
            scorer_runtime=scorer_runtime,
            plaintext_idx=scenario.plaintext_idx,
            repeats=min(4, int(repeats)),
            chunk_size=chunk_size,
        )
    elapsed, stats_obj, report, last_score = execute_batched_candidate_calls(
        scorer_runtime=scorer_runtime,
        plaintext_idx=scenario.plaintext_idx,
        repeats=repeats,
        chunk_size=chunk_size,
    )
    return {
        "scenario": scenario.name,
        "length": int(scenario.length),
        "repeats": int(repeats),
        "chunk_size": int(chunk_size),
        "elapsed_seconds": elapsed,
        "per_candidate_ms": (1000.0 * elapsed / int(repeats)),
        "candidates_per_second": (float(repeats) / elapsed) if elapsed > 0.0 else float("nan"),
        "batch_calls": int(stats_obj.batch_calls),
        "scalar_fallback_calls": int(stats_obj.scalar_fallback_calls),
        "score_seconds": float(stats_obj.score_seconds),
        "last_score": float(last_score),
        "word_ngram_judge_active": bool(report.get("word_ngram_judge_active", False)),
        "word_ngram_judge_n_positions": int(
            report.get("word_ngram_judge_n_positions", 0) or 0
        ),
    }


def estimate_phasec_budget(
    *,
    preset: dict[str, Any],
    per_call_ms: float,
) -> dict[str, Any]:
    phasec_cfg = dict(preset.get("force_stage3_phasec_cfg", {}))
    phasec_steps = int(phasec_cfg.get("steps", 0) or 0)
    proposals_per_step = int(phasec_cfg.get("proposals_per_step", 0) or 0)
    configured_start_keys = int(preset.get("force_stage3_phasec_start_keys", 0) or 0)
    phaseb_top_n = int(preset.get("force_stage3_phaseb_top_n", 0) or 0)
    realistic_start_keys = int(min(configured_start_keys, phaseb_top_n + 1))
    configured_calls = int(configured_start_keys * phasec_steps * proposals_per_step)
    realistic_calls = int(realistic_start_keys * phasec_steps * proposals_per_step)
    return {
        "preset_id": ACTIVE_TUNING_PRESET_ID,
        "configured_start_keys": configured_start_keys,
        "realistic_start_keys": realistic_start_keys,
        "phaseb_top_n": phaseb_top_n,
        "phasec_steps": phasec_steps,
        "proposals_per_step": proposals_per_step,
        "configured_lexical_calls": configured_calls,
        "realistic_lexical_calls": realistic_calls,
        "configured_seconds": float(configured_calls * per_call_ms / 1000.0),
        "realistic_seconds": float(realistic_calls * per_call_ms / 1000.0),
        "assumption": (
            "Assumes one unique word-ngram lexical scorer call per Phase-C proposal; "
            "cache hits or repeated keys would reduce runtime."
        ),
    }


def write_profile_report(
    *,
    scorer_runtime: Any,
    scenario: Scenario,
    repeats: int,
    out_dir: Path,
) -> dict[str, Any]:
    profiler = cProfile.Profile()
    profiler.enable()
    elapsed, _stats_obj, report, last_score = execute_exact_single_candidate_calls(
        scorer_runtime=scorer_runtime,
        plaintext_idx=scenario.plaintext_idx,
        repeats=repeats,
    )
    profiler.disable()

    prof_path = out_dir / "cprofile.prof"
    txt_path = out_dir / "cprofile_top_cumulative.txt"
    profiler.dump_stats(str(prof_path))
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats(PROFILE_TOP_N)
    txt_path.write_text(stream.getvalue(), encoding="utf-8")
    return {
        "scenario": scenario.name,
        "repeats": int(repeats),
        "elapsed_seconds": float(elapsed),
        "per_call_ms": (1000.0 * elapsed / int(repeats)),
        "last_score": float(last_score),
        "word_ngram_judge_active": bool(report.get("word_ngram_judge_active", False)),
        "profile_relpath": str(prof_path.relative_to(REPO_ROOT)),
        "profile_text_relpath": str(txt_path.relative_to(REPO_ROOT)),
    }


def main() -> None:
    preset = dict(STAGE3_TUNING_PRESETS[ACTIVE_TUNING_PRESET_ID])
    final_instance_path = discover_final_instance_path()
    payload = load_final_instance_payload(final_instance_path)
    scenarios = build_benchmark_scenarios(payload, prefix_lengths=PREFIX_LENGTHS)

    scorer_runtime, scorer_cfg = build_word_ngram_runtime(
        period=int(payload["period"]),
        columns=int(payload["columns"]),
        alphabet_size=int(payload["alphabet_size"]),
        order=str(payload["order"]),
        preset=preset,
    )

    run_dir = REPO_ROOT / OUTPUT_ROOT / f"{_utc_label()}__{RUN_LABEL}"
    run_dir.mkdir(parents=True, exist_ok=True)

    exact_rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        print(
            "[word_ngram_tiebreak_profile] "
            f"exact_start scenario={scenario.name} length={scenario.length} repeats={EXACT_REPEATS}",
            flush=True,
        )
        exact_rows.append(
            benchmark_exact_path(
                scorer_runtime=scorer_runtime,
                scenario=scenario,
                repeats=EXACT_REPEATS,
            )
        )
        latest = exact_rows[-1]
        print(
            "[word_ngram_tiebreak_profile] "
            f"exact_done scenario={scenario.name} per_call_ms={float(latest['per_call_ms']):.3f} "
            f"active={int(bool(latest['word_ngram_judge_active']))} "
            f"trust={latest['word_ngram_judge_trust_score']}",
            flush=True,
        )

    batch_focus = next(
        scenario for scenario in scenarios if scenario.name == PROFILE_SCENARIO_NAME
    )
    batch_rows: list[dict[str, Any]] = []
    for chunk_size in BATCH_CHUNK_SIZES:
        print(
            "[word_ngram_tiebreak_profile] "
            f"batch_start scenario={batch_focus.name} chunk_size={chunk_size} repeats={BATCH_REPEATS}",
            flush=True,
        )
        batch_rows.append(
            benchmark_batch_path(
                scorer_runtime=scorer_runtime,
                scenario=batch_focus,
                repeats=BATCH_REPEATS,
                chunk_size=chunk_size,
            )
        )
        latest = batch_rows[-1]
        print(
            "[word_ngram_tiebreak_profile] "
            f"batch_done scenario={batch_focus.name} chunk_size={chunk_size} "
            f"per_candidate_ms={float(latest['per_candidate_ms']):.3f}",
            flush=True,
        )

    exact_focus = next(
        row for row in exact_rows if str(row["scenario"]) == PROFILE_SCENARIO_NAME
    )
    phasec_estimate = estimate_phasec_budget(
        preset=preset,
        per_call_ms=float(exact_focus["per_call_ms"]),
    )
    profile_summary = write_profile_report(
        scorer_runtime=scorer_runtime,
        scenario=batch_focus,
        repeats=PROFILE_REPEATS,
        out_dir=run_dir,
    )

    _write_csv(run_dir / "exact_path_timings.csv", exact_rows)
    _write_csv(run_dir / "batch_compare.csv", batch_rows)

    summary = {
        "run_label": RUN_LABEL,
        "final_instance_relpath": str(final_instance_path.relative_to(REPO_ROOT)),
        "active_preset_id": ACTIVE_TUNING_PRESET_ID,
        "scorer_cfg": _jsonify(scorer_cfg),
        "scenario_count": len(scenarios),
        "exact_repeats": EXACT_REPEATS,
        "batch_repeats": BATCH_REPEATS,
        "profile_repeats": PROFILE_REPEATS,
        "phasec_estimate": _jsonify(phasec_estimate),
        "profile_summary": _jsonify(profile_summary),
        "fastest_exact_scenario": _jsonify(
            min(exact_rows, key=lambda row: float(row["per_call_ms"]))
        ),
        "slowest_exact_scenario": _jsonify(
            max(exact_rows, key=lambda row: float(row["per_call_ms"]))
        ),
        "best_batch_row": _jsonify(
            min(batch_rows, key=lambda row: float(row["per_candidate_ms"]))
        ),
    }
    (run_dir / "summary.json").write_text(
        json.dumps(_jsonify(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(
        f"[word_ngram_tiebreak_profile] run_dir={run_dir.relative_to(REPO_ROOT)}",
        flush=True,
    )
    print(
        "[word_ngram_tiebreak_profile] "
        f"artifact={final_instance_path.relative_to(REPO_ROOT)}",
        flush=True,
    )
    print(
        "[word_ngram_tiebreak_profile] "
        f"focus_exact scenario={PROFILE_SCENARIO_NAME} "
        f"per_call_ms={float(exact_focus['per_call_ms']):.3f} "
        f"calls_per_second={float(exact_focus['calls_per_second']):.2f}",
        flush=True,
    )
    print(
        "[word_ngram_tiebreak_profile] "
        f"phasec_estimate realistic_calls={int(phasec_estimate['realistic_lexical_calls'])} "
        f"realistic_seconds={float(phasec_estimate['realistic_seconds']):.1f} "
        f"configured_calls={int(phasec_estimate['configured_lexical_calls'])} "
        f"configured_seconds={float(phasec_estimate['configured_seconds']):.1f}",
        flush=True,
    )
    best_batch = summary["best_batch_row"]
    print(
        "[word_ngram_tiebreak_profile] "
        f"best_batch chunk_size={int(best_batch['chunk_size'])} "
        f"per_candidate_ms={float(best_batch['per_candidate_ms']):.3f} "
        f"candidates_per_second={float(best_batch['candidates_per_second']):.2f}",
        flush=True,
    )
    refresh_catalog_safely(print_fn=print)


if __name__ == "__main__":
    main()
