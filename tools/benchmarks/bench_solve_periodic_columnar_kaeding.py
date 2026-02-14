"""
End-to-end benchmark: seed pool -> Kaeding solver (PeriodicColumnar).

Purpose
-------
We already have a seed-quality benchmark (`bench_seed_periodic_columnar.py`) that
measures raw_fulltext (unwindowed avg logp over the whole text) and reports
PCT/ECDF transfer diagnostics.

This benchmark answers the next questions:
  1) Do these seeds improve Kaeding Stage-1 outcomes under the real engine?
  2) If Kaeding emits a top-K candidate set, can WLI-2 rerank "snap" us closer to truth
     (measured by best-1 / best-K match_ratio), without letting WLI steer the optimiser yet?

Notes
-----
* Kaeding in the engine operates on the scorer's objective (typically PCT) but can
  optimise "raw" when available via evaluate_keys_with_raw(). In the current engine,
  that "raw" is the win=10 windowed mean-per-ngram stat (diagnostic here as raw_native_win10).
* We intentionally report:
    - raw_fulltext_char (primary, Kaeding-original-style)
    - raw_fulltext_wli1/wli2 (Stage-2 rerank metrics; full-stream and within-word variants)
    - raw_native_win10 (engine raw)
    - pct_ecdf (engine objective)
  so we can see transfer and objective mismatch.
* WLI is only used for reranking here; Stage-1 solver runs with WLI disabled.
"""

from __future__ import annotations

import sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import json
import csv
import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np

from rune_decrypter_prime.api import run, KeySpec, SolverSpec, Direction, by_name
from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Device, ObjectiveFamily, ObjectiveSpec, SeMode, Stat, ScorerImpl
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps
from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.seed_utils_periodic_columnar import SeedPlan, generate_seed_keys_periodic_columnar
from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext_string

ALPHABET_SIZE = 29
ORDER = "col_then_sub"

# How many random keys to sample for a quick "is the oracle sane?" guard.
RANDOM_KEYS_SANITY = 32
TOP_K = 64  # candidate retention / rerank pool size
PREVIEW_CHARS = 240

# Benchmark profile (no CLI):
# - focus_p7_p13: period-7 + period-13 focused matrix (recommended next run)
# - overnight_8h: default practical run (drops p10 calibration tiers)
# - pilot_quick: short A/B sanity run (includes tail-heavy budget)
# - preflight_1h: ~1h run with tail-diverse seed mode enabled
# - overnight_p13_all: overnight run focused on period=13 with all seed/budget options
# - explore_long: larger matrix for research runs
BENCH_PROFILE = "focus_p7_p13"

# Optional resume mode
# - Set to a previous benchmark output folder to continue only missing runs.
# - Keep as None for a fresh run.
#
# Example:
# RESUME_FROM_RUN_DIR = r"output/tools/benchmarks/20260213T062803Z__bench_solve__82e3c05"
RESUME_FROM_RUN_DIR: str | None = None


@dataclass(frozen=True)
class Tier:
    name: str
    period: int
    columns: int
    length: int


@dataclass(frozen=True)
class Budget:
    name: str
    solver: SolverSpec
    seed_plan: SeedPlan
    n_seed_keys: int


# Tail-diverse seed-pool controls (benchmark mode only).
TAIL_DIVERSE_TAIL_COUNT = 8
TAIL_DIVERSE_B_PER_TAIL = 3
TAIL_DIVERSE_M_PER_TAIL = 2
TAIL_DIVERSE_POOL_MULT = 4
TAIL_DIVERSE_E_TAIL = 2048  # approximate per-tail Stage-1 eval budget
TAIL_DIVERSE_INNER_BATCH = 64
TAIL_DIVERSE_TOPK_DIAG = 16

# Seed rerank configuration used only for mode="seed_pct_rerank".
# This is intentionally mixed char+WLI (includes WLI 3/4) to reduce
# char-only false attractors before Stage-1 solve.
SEED_RERANK_CHAR_WEIGHTS = {3: 0.25, 4: 0.25}
SEED_RERANK_WLI_WEIGHTS = {1: 0.125, 2: 0.125, 3: 0.25, 4: 0.25}


# Tier catalog
_CALIBRATION_TIERS_ALL: List[Tier] = [
    Tier(name="calib_p7_c1_l400", period=7, columns=1, length=400),
    Tier(name="calib_p10_c1_l400", period=10, columns=1, length=400),
    Tier(name="calib_p7_c5_l400", period=7, columns=5, length=400),
    Tier(name="calib_p10_c7_l400", period=10, columns=7, length=400),
]
_REAL_TIERS_ALL: List[Tier] = [
    Tier(name="hard_p9_c13_l1200", period=9, columns=13, length=1200),
    Tier(name="goal_p13_c13_l300", period=13, columns=13, length=300),
]

def _budget_small() -> Budget:
    return Budget(
        name="small",
        solver=SolverSpec.kaeding(
            steps=300,
            restarts=2,
            inner_batch=128,
            col_every=10,
            col_batch=64,
            slip_every=60,
            slip_blocks=1,
            slip_policy="stall",
            stall_rounds=250,
            stall_slip_limit=3,
            slip_swaps=40,
            use_raw_score=True,
            top_k=TOP_K,
            progress_pct=10,
            print_progress=True,
            seed=2026,
        ),
        seed_plan=SeedPlan(n_block_seeds=8, n_tail_seeds=8, n_starts=64, refine_steps=800),
        n_seed_keys=64,
    )


def _budget_tail_heavy() -> Budget:
    # Keep expected evals close to "small": (128 + 64/10) ~= (128 + 32/5) per step.
    return Budget(
        name="tail_heavy",
        solver=SolverSpec.kaeding(
            steps=300,
            restarts=2,
            inner_batch=128,
            col_every=5,
            col_batch=32,
            slip_every=60,
            slip_blocks=1,
            slip_policy="stall",
            stall_rounds=250,
            stall_slip_limit=3,
            slip_swaps=40,
            use_raw_score=True,
            top_k=TOP_K,
            progress_pct=10,
            print_progress=True,
            seed=2026,
        ),
        seed_plan=SeedPlan(
            n_block_seeds=6,
            n_tail_seeds=12,
            n_starts=64,
            refine_steps=800,
            tail_move_prob=0.70,
        ),
        n_seed_keys=64,
    )


def _profile_settings(profile: str) -> tuple[List[Tier], List[int], List[int], List[Budget], List[str]]:
    p = str(profile).strip().lower()
    if p == "focus_p7_p13":
        tiers = [
            Tier(name="calib_p7_c5_l400", period=7, columns=5, length=400),
            Tier(name="goal_p13_c13_l300", period=13, columns=13, length=300),
        ]
        modes = ["none", "seed_raw", "seed_pct_rerank", "seed_tail_diverse"]
        return tiers, [0, 211], [111, 222], [_budget_small(), _budget_tail_heavy()], modes
    if p == "overnight_p13_all":
        tiers = [
            Tier(name="goal_p13_c13_l300", period=13, columns=13, length=300),
        ]
        modes = ["none", "seed_raw", "seed_pct_rerank", "seed_tail_diverse"]
        return tiers, [0, 211], [111, 222], [_budget_small(), _budget_tail_heavy()], modes
    if p == "overnight_8h":
        tiers = [
            Tier(name="calib_p7_c1_l400", period=7, columns=1, length=400),
            Tier(name="calib_p7_c5_l400", period=7, columns=5, length=400),
            Tier(name="hard_p9_c13_l1200", period=9, columns=13, length=1200),
            Tier(name="goal_p13_c13_l300", period=13, columns=13, length=300),
        ]
        modes = ["none", "seed_raw", "seed_pct_rerank"]
        return tiers, [0, 211], [111, 222], [_budget_small()], modes
    if p == "pilot_quick":
        tiers = [
            Tier(name="calib_p7_c5_l400", period=7, columns=5, length=400),
            Tier(name="goal_p13_c13_l300", period=13, columns=13, length=300),
        ]
        modes = ["none", "seed_raw", "seed_pct_rerank"]
        return tiers, [0], [111], [_budget_small(), _budget_tail_heavy()], modes
    if p == "preflight_1h":
        tiers = [
            Tier(name="calib_p7_c5_l400", period=7, columns=5, length=400),
            Tier(name="goal_p13_c13_l300", period=13, columns=13, length=300),
        ]
        modes = ["none", "seed_raw", "seed_pct_rerank", "seed_tail_diverse"]
        return tiers, [0], [111], [_budget_small()], modes
    if p == "explore_long":
        modes = ["none", "seed_raw", "seed_pct_rerank", "seed_tail_diverse"]
        return (
            list(_CALIBRATION_TIERS_ALL) + list(_REAL_TIERS_ALL),
            [0, 211],
            [111, 222],
            [_budget_small(), _budget_tail_heavy()],
            modes,
        )
    raise ValueError(
        f"[bench_solve] Unknown BENCH_PROFILE={profile!r}. "
        f"Use focus_p7_p13|overnight_p13_all|overnight_8h|pilot_quick|preflight_1h|explore_long."
    )


TIERS, TEXT_OFFSETS, KEY_SEEDS, SOLVER_BUDGETS, SEED_MODES = _profile_settings(BENCH_PROFILE)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_short_hash() -> str:
    try:
        value = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=_repo_root()).decode().strip()
        return value or "nogit"
    except Exception:
        return "nogit"


def _write_reports(rows: List[dict], summary: dict) -> Path:
    root = _repo_root()
    out_root = root / "output" / "tools" / "benchmarks"
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / f"{stamp}__bench_solve__{_git_short_hash()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "instances.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_csv(run_dir / "instances.csv", rows)
    return run_dir


def _write_run_manifest(run_dir: Path, manifest: dict) -> None:
    _atomic_write_text(run_dir / "run_manifest.json", json.dumps(manifest, indent=2, sort_keys=True))


def _build_run_manifest(
    *,
    direction: Direction,
    lm_root: Path,
    required_ns: Sequence[int],
    seed_modes: Sequence[str],
    total_instances: int,
    total_solves: int,
    resumed: bool,
    resumed_from: str | None,
) -> dict:
    budgets_payload: List[dict] = []
    for b in SOLVER_BUDGETS:
        solver_params = dict(getattr(b.solver, "params", {}) or {})
        budgets_payload.append(
            {
                "name": str(b.name),
                "solver_name": str(getattr(b.solver, "name", "kaeding")),
                "solver_params": solver_params,
                "seed_plan": dict(b.seed_plan.__dict__),
                "n_seed_keys": int(b.n_seed_keys),
            }
        )
    return {
        "kind": "bench_solve_periodic_columnar_kaeding",
        "version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "git_short": _git_short_hash(),
        "profile": str(BENCH_PROFILE),
        "resume": {
            "enabled": bool(resumed),
            "source": str(resumed_from or ""),
        },
        "script": str(Path(__file__).resolve().as_posix()),
        "repo_root": str(_repo_root().as_posix()),
        "direction": str(direction.value),
        "order": str(ORDER),
        "alphabet_size": int(ALPHABET_SIZE),
        "top_k": int(TOP_K),
        "random_keys_sanity": int(RANDOM_KEYS_SANITY),
        "preview_chars": int(PREVIEW_CHARS),
        "text_offsets": [int(x) for x in TEXT_OFFSETS],
        "key_seeds": [int(x) for x in KEY_SEEDS],
        "seed_modes": [str(x) for x in seed_modes],
        "tiers": [
            {"name": str(t.name), "period": int(t.period), "columns": int(t.columns), "length": int(t.length)}
            for t in TIERS
        ],
        "solver_budgets": budgets_payload,
        "tail_diverse": {
            "tail_count": int(TAIL_DIVERSE_TAIL_COUNT),
            "b_per_tail": int(TAIL_DIVERSE_B_PER_TAIL),
            "m_per_tail": int(TAIL_DIVERSE_M_PER_TAIL),
            "pool_mult": int(TAIL_DIVERSE_POOL_MULT),
            "e_tail": int(TAIL_DIVERSE_E_TAIL),
            "inner_batch": int(TAIL_DIVERSE_INNER_BATCH),
            "topk_diag": int(TAIL_DIVERSE_TOPK_DIAG),
        },
        "seed_pct_rerank": {
            "char_weights": dict(SEED_RERANK_CHAR_WEIGHTS),
            "wli_weights": dict(SEED_RERANK_WLI_WEIGHTS),
            "objective": "pct.logp.win10",
            "use_word_breaks": True,
        },
        "scoring": {
            "required_ns": [int(x) for x in required_ns],
            "raw_weights": {3: 0.5, 4: 0.5},
            "pct_weights": {3: 0.5, 4: 0.5},
            "wli1_weights": {1: 1.0},
            "wli2_weights": {2: 1.0},
            "lm_root": str(lm_root),
            "assets_models": ["char", "wli"],
        },
        "expected": {"instances": int(total_instances), "solves": int(total_solves)},
    }


def _row_id(row: dict) -> tuple[str, str, str, int, int]:
    return (
        str(row["tier"]),
        str(row["budget"]),
        str(row["mode"]),
        int(row["text_id"]),
        int(row["key_seed"]),
    )


def _load_resume_rows(run_dir: Path) -> List[dict]:
    p = run_dir / "instances.json"
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError(f"[bench_solve] resume file is not a row list: {p}")
    out: List[dict] = []
    for i, row in enumerate(data):
        if not isinstance(row, dict):
            raise RuntimeError(f"[bench_solve] resume row {i} is not an object")
        out.append(row)
    return out


def _atomic_write_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _compute_summary(rows: List[dict]) -> dict:
    # Summary: percentiles by (tier,budget,mode)
    summary: dict = {"tiers": {}}
    groups: Dict[Tuple[str, str, str], List[dict]] = {}
    for row in rows:
        groups.setdefault((row["tier"], row["budget"], row["mode"]), []).append(row)

    for (tier, budget, mode), items in groups.items():
        # Objective misalignment diagnostics: how often does the optimiser beat the oracle?
        pct_gap = [float(r["sol_pct"]) - float(r["oracle_pct"]) for r in items]
        raw_full_gap = [float(r["sol_raw_full"]) - float(r["oracle_raw_full"]) for r in items]
        raw_native_gap = [float(r["sol_raw_native"]) - float(r["oracle_raw_native"]) for r in items]
        seed_eq_arr = np.asarray([float(r.get("seed_pool_equal_raw", float("nan"))) for r in items], dtype=np.float64)
        seed_eq_arr = seed_eq_arr[np.isfinite(seed_eq_arr)]
        entry = dict(
            tier=tier,
            budget=budget,
            mode=mode,
            n=len(items),
            sol_raw_full=_percentiles([r["sol_raw_full"] for r in items]),
            sol_raw_native=_percentiles([r["sol_raw_native"] for r in items]),
            sol_pct=_percentiles([r["sol_pct"] for r in items]),
            match_ratio=_percentiles([r["match_ratio"] for r in items]),
            bestk_match_ratio=_percentiles([float(r.get("bestk_match_ratio", float("nan"))) for r in items]),
            pick_wli1_match_ratio=_percentiles([float(r.get("pick_wli1_match_ratio", float("nan"))) for r in items]),
            pick_wli2_full_match_ratio=_percentiles([float(r.get("pick_wli2_full_match_ratio", float("nan"))) for r in items]),
            pick_wli2_within_match_ratio=_percentiles([float(r.get("pick_wli2_within_match_ratio", float("nan"))) for r in items]),
            n_unique_tails_topk=_percentiles([float(r.get("n_unique_tails_topk", float("nan"))) for r in items]),
            n_unique_tails_topk_by_score=_percentiles([float(r.get("n_unique_tails_topk_by_score", float("nan"))) for r in items]),
            n_unique_tails_topk_by_match=_percentiles([float(r.get("n_unique_tails_topk_by_match", float("nan"))) for r in items]),
            n_unique_tails_initial_pool=_percentiles([float(r.get("n_unique_tails_initial_pool", float("nan"))) for r in items]),
            n_unique_tails_after_per_tail_retention=_percentiles([
                float(r.get("n_unique_tails_after_per_tail_retention", float("nan"))) for r in items
            ]),
            candidates=_percentiles([float(r.get("candidates", float("nan"))) for r in items]),
            stage2_seconds=_percentiles([float(r.get("stage2_seconds", float("nan"))) for r in items]),
            bestk_minus_best1=_percentiles([
                float(r.get("bestk_match_ratio", float("nan"))) - float(r.get("match_ratio", float("nan")))
                for r in items
            ]),
            wli2_full_minus_bestk=_percentiles([
                float(r.get("pick_wli2_full_match_ratio", float("nan"))) - float(r.get("bestk_match_ratio", float("nan")))
                for r in items
            ]),
            wli2_within_minus_bestk=_percentiles([
                float(r.get("pick_wli2_within_match_ratio", float("nan"))) - float(r.get("bestk_match_ratio", float("nan")))
                for r in items
            ]),
            corr_match_raw_full=_percentiles([float(r.get("corr_match_raw_full", float("nan"))) for r in items]),
            corr_match_pct=_percentiles([float(r.get("corr_match_pct", float("nan"))) for r in items]),
            corr_match_wli2_full=_percentiles([float(r.get("corr_match_wli2_full", float("nan"))) for r in items]),
            corr_match_wli2_within=_percentiles([float(r.get("corr_match_wli2_within", float("nan"))) for r in items]),
            evals=_percentiles([float(r.get("evals", 0) or 0) for r in items]),
            seconds=_percentiles([float(r.get("seconds", 0.0) or 0.0) for r in items]),
            oracle_gap_pct=_percentiles(pct_gap),
            oracle_gap_raw_full=_percentiles(raw_full_gap),
            oracle_gap_raw_native=_percentiles(raw_native_gap),
            rate_sol_gt_oracle_pct=float(np.mean(np.asarray(pct_gap, dtype=np.float64) > 0.0)),
            rate_sol_gt_oracle_raw_full=float(np.mean(np.asarray(raw_full_gap, dtype=np.float64) > 0.0)),
            rate_sol_gt_oracle_raw_native=float(np.mean(np.asarray(raw_native_gap, dtype=np.float64) > 0.0)),
            rate_seed_pool_equal_raw=(float(np.mean(seed_eq_arr)) if seed_eq_arr.size else float("nan")),
        )
        summary["tiers"].setdefault(tier, []).append(entry)

    return summary


def _checkpoint(run_dir: Path, *, rows: List[dict]) -> dict:
    # Rows are small (tens), so rewriting is cheap and avoids jsonl parsing.
    summary = _compute_summary(rows)
    _atomic_write_text(run_dir / "instances.json", json.dumps(rows, indent=2))
    _atomic_write_text(run_dir / "summary.json", json.dumps(summary, indent=2))
    _write_csv(run_dir / "instances.csv", rows)
    return summary


def _key_hash(key_like: Sequence[int] | np.ndarray) -> str:
    arr = np.asarray(list(key_like), dtype=np.int16).reshape(-1)
    return hashlib.sha1(arr.tobytes()).hexdigest()[:16]


def _pool_fingerprint(keys: Sequence[Sequence[int]]) -> str:
    h = hashlib.sha1()
    for k in keys:
        arr = np.asarray(list(k), dtype=np.int16).reshape(-1)
        h.update(arr.tobytes())
    return h.hexdigest()[:16]


def _safe_preview_latin(pt: Sequence[int] | np.ndarray, wli: Sequence[Sequence[int]] | None, *, limit: int = PREVIEW_CHARS) -> str:
    pt_i = np.asarray(pt, dtype=np.int64).reshape(-1).tolist()
    if not pt_i:
        return ""
    if wli is None:
        wli_i = [[i, len(pt_i)] for i in range(len(pt_i))]
    else:
        wli_i = [[int(a), int(b)] for a, b in wli]
        if len(wli_i) != len(pt_i):
            # Fallback: when lengths mismatch, degrade gracefully to one synthetic word.
            wli_i = [[i, len(pt_i)] for i in range(len(pt_i))]
    try:
        return Runeglish.to_rune_latin(pt_i, wli_i, limit=limit)
    except Exception:
        return ""


def _write_csv(path: Path, rows: List[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in keys})


def _require_assets(direction: Direction, *, ns: Tuple[int, ...], need_wli: bool) -> Path:
    # Reuse the strict test guard; if it's not importable, fail loudly.
    from tests.scoring._helpers.lm_test_guard import require_full_lm_assets
    models = ("char", "wli") if need_wli else ("char",)
    try:
        root, _ = require_full_lm_assets(
            models=models,
            modes=(direction.value,),
            poses=("nose",),
            ns=ns,
            ecdf_stats=("logp",),
        )
        return root
    except Exception as exc:
        raise RuntimeError(f"LM assets missing or incomplete: {exc}") from exc


def _encode_long_plaintext(direction: Direction) -> tuple[np.ndarray, np.ndarray]:
    pt_idx, wli, _runes = Runeglish.encode_english_to_runes(long_plaintext_string.strip(), direction=direction.value)
    pt_u8 = np.asarray(pt_idx, dtype=np.uint8)
    wli_u8 = np.asarray(wli, dtype=np.uint8)
    if wli_u8.ndim != 2 or wli_u8.shape[1] != 2 or wli_u8.shape[0] != pt_u8.size:
        raise RuntimeError("[bench_solve] Runeglish returned WLI with unexpected shape")
    return pt_u8, wli_u8


def _tile_stream(pt_base: np.ndarray, wli_base: np.ndarray, needed: int) -> tuple[np.ndarray, np.ndarray]:
    if pt_base.size == 0:
        raise ValueError("Encoded plaintext is empty")
    if wli_base.shape[0] != pt_base.size:
        raise ValueError("pt_base and wli_base length mismatch")
    if pt_base.size >= needed:
        return pt_base, wli_base
    reps = int(np.ceil(needed / pt_base.size))
    pt_t = np.tile(pt_base, reps)
    wli_t = np.tile(wli_base, (reps, 1))
    return np.ascontiguousarray(pt_t, dtype=np.uint8), np.ascontiguousarray(wli_t, dtype=np.uint8)


def _slice_word_aligned(
    pt_base: np.ndarray,
    wli_base: np.ndarray,
    *,
    length: int,
    offset_hint: int,
    max_scan: int = 50_000,
) -> tuple[np.ndarray, List[List[int]], int]:
    """
    Return a (pt_idx, wli_list, offset_used) slice of exact token length that starts and ends
    on word boundaries so WLI remains valid for the slice.

    This is a hard requirement for any benchmark that uses WLI scoring.
    """
    length = int(length)
    offset_hint = int(offset_hint)
    if length <= 0:
        raise ValueError("length must be > 0")
    if offset_hint < 0:
        raise ValueError("offset_hint must be >= 0")

    # Ensure we have room to scan without worrying about wrap.
    pt_t, wli_t = _tile_stream(pt_base, wli_base, needed=offset_hint + length + max_scan + 4)

    start_min = offset_hint
    start_max = offset_hint + max_scan
    L = int(pt_t.size)
    for s in range(start_min, min(start_max, L)):
        if int(wli_t[s, 0]) != 0:
            continue
        e = s + length - 1
        if e >= L:
            break
        pos_e = int(wli_t[e, 0])
        len_e = int(wli_t[e, 1])
        if pos_e != (len_e - 1):
            continue
        pt = np.ascontiguousarray(pt_t[s : s + length], dtype=np.uint8)
        wli = [[int(a), int(b)] for a, b in wli_t[s : s + length].tolist()]
        return pt, wli, int(s)

    raise RuntimeError(f"[bench_solve] could not find word-aligned slice length={length} near offset={offset_hint}")


def _word_spans_from_wli(wli: Sequence[Sequence[int]]) -> List[Tuple[int, int]]:
    """Return (start,end) spans (end exclusive) for each word based on wli pairs."""
    spans: List[Tuple[int, int]] = []
    start = 0
    for i, pair in enumerate(wli):
        pos = int(pair[0])
        ln = int(pair[1])
        if pos == 0:
            start = int(i)
        if pos == ln - 1:
            spans.append((start, int(i) + 1))
    return spans


class RawFulltextScorer:
    """
    Unwindowed avg logp over the *entire text* (Kaeding-style).

    Supports:
      - char n-grams via LMPrime model="char"
      - wli n-grams via LMPrime model="wli" (requires WLI stream)

    For WLI-2 we benchmark two definitions:
      - full-stream: score over the entire stream (includes cross-word n-grams)
      - within-word: score each word independently and average across within-word n-grams only
    """

    def __init__(
        self,
        *,
        lm: LanguageModelPrime,
        direction: Direction,
        model: str,
        weights: Dict[int, float],
        within_word: bool = False,
    ):
        self.direction = direction
        self.lm = lm
        self.model = str(model).lower()
        if self.model not in {"char", "wli"}:
            raise ValueError("model must be 'char' or 'wli'")
        self.within_word = bool(within_word)
        self.weights = {int(n): float(w) for n, w in weights.items() if int(n) > 0 and float(w) > 0.0}
        if not self.weights:
            raise ValueError("RawFulltextScorer requires at least one positive n-gram weight")

    def score(self, pt: np.ndarray, wli: Sequence[Sequence[int]] | None = None, *, word_spans: List[Tuple[int, int]] | None = None) -> float:
        pt_u8 = np.asarray(pt, dtype=np.uint8).reshape(-1)
        L = int(pt_u8.size)
        if L <= 0:
            return float("-inf")

        total_w = float(sum(self.weights.values()))
        acc = 0.0

        if self.model == "char":
            seq = pt_u8.tolist()
            for n, w in self.weights.items():
                n = int(n)
                total_eval = L - n + 1
                if total_eval <= 0:
                    return float("-inf")
                res = self.lm.score([seq], None, direction=self.direction.value, se="nose", n=n, model="char")[0]
                acc += float(w) * (float(res.logprob_sum) / float(total_eval))
            return acc / total_w

        # model == "wli"
        if wli is None:
            raise ValueError("wli is required when model='wli'")
        if len(wli) != L:
            raise ValueError("wli length must match plaintext length")

        if not self.within_word:
            seq = pt_u8.tolist()
            wli_sent = [[int(a), int(b)] for a, b in wli]
            for n, w in self.weights.items():
                n = int(n)
                total_eval = L - n + 1
                if total_eval <= 0:
                    return float("-inf")
                res = self.lm.score([seq], [wli_sent], direction=self.direction.value, se="nose", n=n, model="wli")[0]
                acc += float(w) * (float(res.logprob_sum) / float(total_eval))
            return acc / total_w

        # within-word scoring
        spans = word_spans if word_spans is not None else _word_spans_from_wli(wli)
        for n, w in self.weights.items():
            n = int(n)
            total_eval = 0
            total_logp = 0.0
            for s, e in spans:
                wlen = int(e - s)
                if wlen < n:
                    continue
                pt_word = pt_u8[s:e].tolist()
                wli_word = [[int(a), int(b)] for a, b in wli[s:e]]
                res = self.lm.score([pt_word], [wli_word], direction=self.direction.value, se="nose", n=n, model="wli")[0]
                total_logp += float(res.logprob_sum)
                total_eval += int(wlen - n + 1)
            if total_eval <= 0:
                return float("-inf")
            acc += float(w) * (total_logp / float(total_eval))
        return acc / total_w


def _pct_scorer(direction: Direction, *, model_root: Path, char_weights: Dict[int, float]) -> Any:
    cfg = ScoringConfig(
        model_root=model_root,
        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
        se_mode=SeMode.NOSE,
        encoding_dir=direction,
        include_char=True,
        use_word_breaks=False,
        char_weights=dict(char_weights),
        wli_weights={},
        impl=ScorerImpl.NUMPY,
    )
    dummy_cipher_cfg = CipherConfig(
        name="periodic_columnar",
        ciphertext=[],
        period=5,
        columns=7,
        alphabet_size=ALPHABET_SIZE,
        key_length=5 * ALPHABET_SIZE + 7,
        order=ORDER,
        encoding_dir=direction,
        wli_data=[],
        device=Device.CPU,
    )
    return build_scorer(dummy_cipher_cfg, cfg)


def _score_pt(pt: np.ndarray, *, raw_full_scorer: RawFulltextScorer, pct_scorer: Any) -> Tuple[float, float, float]:
    raw_full = float(raw_full_scorer.score(pt))
    pct, raw_native = pct_scorer.score_with_raw(pt, None)
    return raw_full, float(pct), float(raw_native)


def _preflight_known_key_roundtrip(
    *,
    cipher: PeriodicColumnarCipher,
    ct_idx: np.ndarray,
    key_true: np.ndarray,
    pt_true: np.ndarray,
    wli_list: Sequence[Sequence[int]],
    raw_full_scorer: RawFulltextScorer,
    pct_scorer: Any,
    tier_name: str,
    text_id: int,
    key_seed: int,
) -> dict:
    """
    Gate 0: prove this instance wiring before expensive search.
    """
    pt_check = cipher.decrypt_single(ciphertext=ct_idx, key=key_true)
    pt_true_u8 = np.asarray(pt_true, dtype=np.uint8).reshape(-1)
    pt_check_u8 = np.asarray(pt_check, dtype=np.uint8).reshape(-1)
    if pt_true_u8.size != pt_check_u8.size or not np.array_equal(pt_true_u8, pt_check_u8):
        raise RuntimeError(
            f"[bench_solve] preflight failure: known-key decrypt mismatch "
            f"(tier={tier_name} text={text_id} key_seed={key_seed})"
        )

    if int(len(wli_list)) != int(pt_true_u8.size):
        raise RuntimeError(
            f"[bench_solve] preflight failure: WLI length mismatch "
            f"(tier={tier_name} text={text_id} key_seed={key_seed})"
        )

    oracle_raw_full, oracle_pct, oracle_raw_native = _score_pt(
        pt_true_u8, raw_full_scorer=raw_full_scorer, pct_scorer=pct_scorer
    )
    check_raw_full, check_pct, check_raw_native = _score_pt(
        pt_check_u8, raw_full_scorer=raw_full_scorer, pct_scorer=pct_scorer
    )
    d_raw_full = float(check_raw_full - oracle_raw_full)
    d_pct = float(check_pct - oracle_pct)
    d_raw_native = float(check_raw_native - oracle_raw_native)
    eps = 1e-12
    if abs(d_raw_full) > eps or abs(d_pct) > eps or abs(d_raw_native) > eps:
        raise RuntimeError(
            f"[bench_solve] preflight failure: known-key score drift "
            f"(tier={tier_name} text={text_id} key_seed={key_seed} "
            f"d_raw_full={d_raw_full:.3e} d_pct={d_pct:.3e} d_raw_native={d_raw_native:.3e})"
        )

    return {
        "preflight_roundtrip_ok": 1,
        "preflight_score_delta_raw_full": d_raw_full,
        "preflight_score_delta_pct": d_pct,
        "preflight_score_delta_raw_native": d_raw_native,
    }


def _print_setup_snapshot(*, direction: Direction) -> None:
    print(
        f"[bench_solve] setup: profile={BENCH_PROFILE} direction={direction.value} "
        f"order={ORDER} A={ALPHABET_SIZE} top_k={TOP_K} random_sanity={RANDOM_KEYS_SANITY}",
        flush=True,
    )
    print(
        "[bench_solve] setup: tail_diverse "
        f"T={TAIL_DIVERSE_TAIL_COUNT} B={TAIL_DIVERSE_B_PER_TAIL} m={TAIL_DIVERSE_M_PER_TAIL} "
        f"pool_mult={TAIL_DIVERSE_POOL_MULT} E_tail={TAIL_DIVERSE_E_TAIL} "
        f"inner_batch={TAIL_DIVERSE_INNER_BATCH} topk_diag={TAIL_DIVERSE_TOPK_DIAG}",
        flush=True,
    )
    print(
        "[bench_solve] setup: seed_pct_rerank "
        f"char_weights={json.dumps(SEED_RERANK_CHAR_WEIGHTS, sort_keys=True)} "
        f"wli_weights={json.dumps(SEED_RERANK_WLI_WEIGHTS, sort_keys=True)}",
        flush=True,
    )
    tier_str = ", ".join([f"{t.name}(p{t.period},c{t.columns},L{t.length})" for t in TIERS])
    print(f"[bench_solve] setup: tiers={tier_str}", flush=True)
    for b in SOLVER_BUDGETS:
        params = dict(getattr(b.solver, "params", {}) or {})
        print(
            f"[bench_solve] setup: budget={b.name} solver={getattr(b.solver, 'name', 'kaeding')} "
            f"params={json.dumps(params, sort_keys=True)} seed_plan={json.dumps(dict(b.seed_plan.__dict__), sort_keys=True)} "
            f"n_seed_keys={b.n_seed_keys}",
            flush=True,
        )


def _match_ratio(a: Sequence[int], b: Sequence[int]) -> float:
    aa = np.asarray(a, dtype=np.int64).reshape(-1)
    bb = np.asarray(b, dtype=np.int64).reshape(-1)
    n = min(int(aa.size), int(bb.size))
    if n <= 0:
        return 0.0
    return float(np.mean(aa[:n] == bb[:n]))


def _percentiles(values: Iterable[float], pcts: Tuple[int, ...] = (10, 25, 50, 75, 90, 95)) -> Dict[str, float]:
    arr = np.asarray(list(values), dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {f"p{p}": float("nan") for p in pcts}
    out = {}
    for p in pcts:
        out[f"p{p}"] = float(np.percentile(arr, p))
    out["mean"] = float(np.mean(arr))
    out["std"] = float(np.std(arr))
    return out


def _oracle_vs_random_stats(oracle: float, random_scores: Sequence[float]) -> dict:
    """
    Return cheap discrimination stats.

    * oracle_pctile: fraction of random scores strictly below oracle (empirical CDF)
    * rand_mean/std: baseline distribution moments
    * sep_z: (oracle-mean)/std (nan when std==0)
    """
    arr = np.asarray(list(random_scores), dtype=np.float64).reshape(-1)
    if arr.size == 0:
        return {"oracle_pctile": float("nan"), "rand_mean": float("nan"), "rand_std": float("nan"), "sep_z": float("nan")}
    mean = float(np.mean(arr))
    std = float(np.std(arr))
    pctile = float(np.mean(arr < float(oracle)))
    sep_z = float((float(oracle) - mean) / std) if std > 0 else float("nan")
    return {"oracle_pctile": pctile, "rand_mean": mean, "rand_std": std, "sep_z": sep_z}


def _corrcoef_safe(x: Sequence[float], y: Sequence[float]) -> float:
    xa = np.asarray(list(x), dtype=np.float64).reshape(-1)
    ya = np.asarray(list(y), dtype=np.float64).reshape(-1)
    if xa.size != ya.size or xa.size < 2:
        return float("nan")
    if not np.isfinite(xa).all() or not np.isfinite(ya).all():
        return float("nan")
    if float(np.std(xa)) <= 0.0 or float(np.std(ya)) <= 0.0:
        return float("nan")
    return float(np.corrcoef(xa, ya)[0, 1])


def _spread(values: Sequence[float]) -> float:
    arr = np.asarray(list(values), dtype=np.float64).reshape(-1)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return float("nan")
    return float(np.max(arr) - np.min(arr))


def _std(values: Sequence[float]) -> float:
    arr = np.asarray(list(values), dtype=np.float64).reshape(-1)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return float("nan")
    return float(np.std(arr))


def _tail_id_from_key(key: Sequence[int], *, period: int, columns: int) -> tuple[int, ...]:
    sub_len = int(period) * ALPHABET_SIZE
    arr = np.asarray(list(key), dtype=np.int64).reshape(-1)
    return tuple(int(x) for x in arr[sub_len : sub_len + int(columns)].tolist())


def _dedupe_keys(keys: Sequence[Sequence[int]]) -> List[List[int]]:
    seen: set[tuple[int, ...]] = set()
    out: List[List[int]] = []
    for k in keys:
        t = tuple(int(x) for x in k)
        if t in seen:
            continue
        seen.add(t)
        out.append([int(x) for x in t])
    return out


def _build_tail_diverse_seed_pool(
    *,
    ct_idx: np.ndarray,
    tier: Tier,
    direction: Direction,
    seed: int,
    budget: Budget,
    seed_cfg: ScoringConfig,
) -> tuple[List[List[int]], dict]:
    """
    Build a seed pool that explicitly covers multiple tail basins.

    Steps:
      1) Broad initial pool from seed generator.
      2) Group by tail_id; select up to T tails.
      3) Per-tail short Stage-1 run (col_every=0) so each tail gets optimisation budget E_tail.
      4) Retain m per tail, merge and cap to n_seed_keys.
    """
    key_len = int(tier.period * ALPHABET_SIZE + tier.columns)
    rng = np.random.default_rng(int(seed) + 81173)
    n_target = int(budget.n_seed_keys)
    n_base = max(n_target * int(TAIL_DIVERSE_POOL_MULT), int(TAIL_DIVERSE_TAIL_COUNT * TAIL_DIVERSE_B_PER_TAIL))
    base_pool = generate_seed_keys_periodic_columnar(
        ct_idx,
        period=tier.period,
        columns=tier.columns,
        order=ORDER,
        direction=direction,
        seed=int(seed) + 1701,
        scoring_cfg=seed_cfg,
        n_keys=n_base,
        plan=budget.seed_plan,
        refine=True,
        rerank_cfg=None,
    )

    groups: Dict[tuple[int, ...], List[List[int]]] = {}
    for k in base_pool:
        tid = _tail_id_from_key(k, period=tier.period, columns=tier.columns)
        groups.setdefault(tid, []).append([int(x) for x in k])

    # If not enough distinct tails, inject synthetic tails by reusing best block part.
    if len(groups) < int(TAIL_DIVERSE_TAIL_COUNT) and int(tier.columns) > 1 and base_pool:
        block_anchor = [int(x) for x in base_pool[0][: int(tier.period * ALPHABET_SIZE)]]
        while len(groups) < int(TAIL_DIVERSE_TAIL_COUNT):
            tail = rng.permutation(int(tier.columns)).astype(np.int64).tolist()
            tid = tuple(int(x) for x in tail)
            if tid in groups:
                continue
            groups[tid] = [block_anchor + [int(x) for x in tail]]

    tail_ids = list(groups.keys())[: int(TAIL_DIVERSE_TAIL_COUNT)]
    n_unique_tails_initial_pool = int(len(tail_ids))
    if n_unique_tails_initial_pool == 0:
        return [], {
            "n_unique_tails_initial_pool": 0,
            "n_unique_tails_after_per_tail_retention": 0,
            "tail_diverse_tail_count_requested": int(TAIL_DIVERSE_TAIL_COUNT),
            "tail_diverse_e_tail": int(TAIL_DIVERSE_E_TAIL),
            "tail_diverse_mode_used": 1,
        }

    inner_batch = int(TAIL_DIVERSE_INNER_BATCH)
    steps = max(8, int(TAIL_DIVERSE_E_TAIL // max(1, inner_batch)))
    per_tail_retained: List[List[int]] = []

    cipher_spec = by_name.cipher(
        "periodic_columnar",
        period=tier.period,
        columns=tier.columns,
        alphabet_size=ALPHABET_SIZE,
        order=ORDER,
    )
    key_spec = KeySpec.periodic_columnar(
        period=tier.period,
        columns=tier.columns,
        alphabet_size=ALPHABET_SIZE,
    )
    scorer_params = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=False,
        char_weights=dict(seed_cfg.char_weights or {3: 0.5, 4: 0.5}),
        wli_weights={},
        encoding_dir=direction,
        impl=ScorerImpl.NUMPY,
    )

    for t_idx, tid in enumerate(tail_ids):
        init = groups.get(tid, [])[: int(TAIL_DIVERSE_B_PER_TAIL)]
        if not init:
            continue

        # Pad up to B per tail via small block swaps while preserving tail.
        while len(init) < int(TAIL_DIVERSE_B_PER_TAIL):
            k = np.asarray(init[-1], dtype=np.int16).copy()
            phase = int(rng.integers(0, int(tier.period)))
            a = int(rng.integers(0, ALPHABET_SIZE))
            b = int(rng.integers(0, ALPHABET_SIZE - 1))
            if b >= a:
                b += 1
            off = phase * ALPHABET_SIZE
            i1, i2 = off + a, off + b
            k[i1], k[i2] = k[i2], k[i1]
            init.append(k.astype(int).tolist())

        micro_solver = SolverSpec.kaeding(
            steps=steps,
            restarts=1,
            inner_batch=inner_batch,
            col_every=0,   # fixed-tail per-tail Stage-1
            col_batch=1,
            slip_every=0,
            slip_blocks=1,
            slip_policy="fixed",
            stall_rounds=steps * 2,
            stall_slip_limit=0,
            slip_swaps=1,
            use_raw_score=True,
            top_k=max(int(TAIL_DIVERSE_M_PER_TAIL), int(TAIL_DIVERSE_B_PER_TAIL)),
            progress_pct=0,
            print_progress=False,
            seed=int(seed) + 900000 + int(t_idx),
        )

        sol = run(
            text=ct_idx.tolist(),
            cipher=cipher_spec,
            key=key_spec,
            solver=micro_solver,
            device=Device.CPU,
            scorer_params=scorer_params,
            telemetry_on=True,
            encoding_dir=direction,
            force_no_wli=True,
            initial_keys=init,
        )

        cand_keys: List[List[int]] = []
        try:
            tel = getattr(sol, "meta", {}).get("telemetry", {}) if hasattr(sol, "meta") else {}
            km = tel.get("kaeding", {}) if isinstance(tel, dict) else {}
            top_keys = km.get("top_keys", None) if isinstance(km, dict) else None
            if isinstance(top_keys, list):
                cand_keys.extend([list(map(int, row)) for row in top_keys])
        except Exception:
            cand_keys = []
        try:
            if getattr(sol, "key", None) is not None:
                cand_keys.append(list(map(int, list(sol.key))))
        except Exception:
            pass
        if not cand_keys:
            cand_keys = [list(map(int, row)) for row in init]

        filtered = [k for k in _dedupe_keys(cand_keys) if _tail_id_from_key(k, period=tier.period, columns=tier.columns) == tid]
        if not filtered:
            filtered = [list(map(int, row)) for row in init[: int(TAIL_DIVERSE_M_PER_TAIL)]]
        per_tail_retained.extend(filtered[: int(TAIL_DIVERSE_M_PER_TAIL)])

    per_tail_retained = _dedupe_keys(per_tail_retained)
    n_unique_tails_after = len({
        _tail_id_from_key(k, period=tier.period, columns=tier.columns) for k in per_tail_retained
    })

    out = list(per_tail_retained)
    seen = {tuple(int(x) for x in k) for k in out}
    for k in base_pool:
        t = tuple(int(x) for x in k)
        if t in seen:
            continue
        out.append(list(map(int, k)))
        seen.add(t)
        if len(out) >= n_target:
            break

    # Hard fallback if still short.
    if len(out) < n_target:
        keyops = PeriodicStructuredMatrixKeyOps(K=key_len, period=tier.period, A=ALPHABET_SIZE, columns=tier.columns)
        while len(out) < n_target:
            k = keyops.random(rng).astype(np.int16, copy=False).astype(int).tolist()
            t = tuple(int(x) for x in k)
            if t in seen:
                continue
            out.append(k)
            seen.add(t)

    out = out[:n_target]
    return out, {
        "n_unique_tails_initial_pool": int(n_unique_tails_initial_pool),
        "n_unique_tails_after_per_tail_retention": int(n_unique_tails_after),
        "tail_diverse_tail_count_requested": int(TAIL_DIVERSE_TAIL_COUNT),
        "tail_diverse_e_tail": int(TAIL_DIVERSE_E_TAIL),
        "tail_diverse_mode_used": 1,
    }


def _format_seconds(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, sec = divmod(seconds, 60.0)
    if minutes < 60:
        return f"{int(minutes)}m{sec:04.1f}s"
    hours, minutes = divmod(minutes, 60.0)
    return f"{int(hours)}h{int(minutes):02d}m"


def _print_run_warnings(rows: List[dict]) -> None:
    if not rows:
        return

    # Warning 1: low tail diversity in top-K on columnar tiers.
    grouped: Dict[Tuple[str, str, str], List[dict]] = {}
    for r in rows:
        grouped.setdefault((str(r["tier"]), str(r["budget"]), str(r["mode"])), []).append(r)
    warned = False
    for (tier, budget, mode), items in sorted(grouped.items()):
        cols = int(items[0].get("columns", 0) or 0)
        if cols < 7:
            continue
        vals = np.asarray([float(it.get("n_unique_tails_topk", float("nan"))) for it in items], dtype=np.float64)
        vals = vals[np.isfinite(vals)]
        if vals.size == 0:
            continue
        med = float(np.median(vals))
        if med <= 1.0:
            warned = True
            print(
                f"[bench_solve][warn] low tail diversity: tier={tier} budget={budget} mode={mode} "
                f"columns={cols} median_unique_tails={med:.1f}",
                flush=True,
            )
    if not warned:
        print("[bench_solve] Tail diversity check: no low-diversity warnings for columns>=7.", flush=True)

    # Warning 2: seed_raw and seed_pct_rerank collapse to identical outcomes.
    pairs: Dict[Tuple[str, str, int, int], Dict[str, dict]] = {}
    for r in rows:
        key = (str(r["tier"]), str(r["budget"]), int(r["text_id"]), int(r["key_seed"]))
        pairs.setdefault(key, {})[str(r["mode"])] = r
    total_pairs = 0
    collapsed = 0
    for key, modes in pairs.items():
        if "seed_raw" not in modes or "seed_pct_rerank" not in modes:
            continue
        total_pairs += 1
        a = modes["seed_raw"]
        b = modes["seed_pct_rerank"]
        same = (
            abs(float(a.get("match_ratio", 0.0)) - float(b.get("match_ratio", 0.0))) <= 1e-12
            and abs(float(a.get("bestk_match_ratio", 0.0)) - float(b.get("bestk_match_ratio", 0.0))) <= 1e-12
            and abs(float(a.get("sol_pct", 0.0)) - float(b.get("sol_pct", 0.0))) <= 1e-12
            and abs(float(a.get("sol_raw_full", 0.0)) - float(b.get("sol_raw_full", 0.0))) <= 1e-12
            and abs(float(a.get("sol_raw_native", 0.0)) - float(b.get("sol_raw_native", 0.0))) <= 1e-12
        )
        if same:
            collapsed += 1
    if total_pairs > 0:
        rate = float(collapsed) / float(total_pairs)
        if rate >= 0.9:
            print(
                f"[bench_solve][warn] seed mode collapse: {collapsed}/{total_pairs} instances have "
                f"identical seed_raw vs seed_pct_rerank outcomes",
                flush=True,
            )
        else:
            print(
                f"[bench_solve] seed_raw vs seed_pct_rerank identical in {collapsed}/{total_pairs} instances.",
                flush=True,
            )


def main() -> None:
    direction = Direction.LTR
    raw_weights = {3: 0.5, 4: 0.5}
    pct_weights = {3: 0.5, 4: 0.5}
    wli1_weights = {1: 1.0}
    wli2_weights = {2: 1.0}

    required_ns = tuple(sorted({*raw_weights.keys(), *pct_weights.keys(), *wli1_weights.keys(), *wli2_weights.keys()}))
    lm_root = _require_assets(direction, ns=required_ns, need_wli=True)

    lm = LanguageModelPrime(
        lm_root=lm_root,
        smoothing="auto_gt",
        alpha=0.5,
        oov_policy="floor_min_seen",
        include_char=True,
    )
    raw_full_scorer = RawFulltextScorer(lm=lm, direction=direction, model="char", weights=raw_weights)
    wli1_scorer = RawFulltextScorer(lm=lm, direction=direction, model="wli", weights=wli1_weights, within_word=False)
    wli2_full_scorer = RawFulltextScorer(lm=lm, direction=direction, model="wli", weights=wli2_weights, within_word=False)
    wli2_within_scorer = RawFulltextScorer(lm=lm, direction=direction, model="wli", weights=wli2_weights, within_word=True)
    pct_scorer = _pct_scorer(direction, model_root=lm_root, char_weights=pct_weights)

    pt_base, wli_base = _encode_long_plaintext(direction)
    if pt_base.size == 0 or wli_base.size == 0:
        raise RuntimeError("[bench_solve] encoded plaintext is empty")
    _print_setup_snapshot(direction=direction)

    rows: List[dict] = []
    t0_all = time.time()

    # Each instance is solved in configured modes (profile-controlled).
    seed_modes = list(SEED_MODES)
    total_instances = len(TIERS) * len(TEXT_OFFSETS) * len(KEY_SEEDS) * len(SOLVER_BUDGETS)
    total_solves = total_instances * len(seed_modes)
    # Resume support (no CLI): continue only missing (tier,budget,mode,text_id,key_seed).
    if RESUME_FROM_RUN_DIR:
        run_dir = Path(RESUME_FROM_RUN_DIR)
        if not run_dir.is_absolute():
            run_dir = (_repo_root() / run_dir).resolve()
        run_dir.mkdir(parents=True, exist_ok=True)
        rows = _load_resume_rows(run_dir)
        completed = {_row_id(r) for r in rows}
        done_solves = len(completed)
        print(
            f"[bench_solve] Resuming from {run_dir.relative_to(_repo_root())} "
            f"with {done_solves}/{total_solves} completed solves",
            flush=True,
        )
        # Re-write summary/csv once on startup so files are consistent with loaded rows.
        _checkpoint(run_dir, rows=rows)
    else:
        done_solves = 0
        run_dir = _write_reports(rows=[], summary={"tiers": {}})
        completed = set()

    rel = run_dir.relative_to(_repo_root())
    manifest = _build_run_manifest(
        direction=direction,
        lm_root=lm_root,
        required_ns=required_ns,
        seed_modes=seed_modes,
        total_instances=total_instances,
        total_solves=total_solves,
        resumed=bool(RESUME_FROM_RUN_DIR),
        resumed_from=RESUME_FROM_RUN_DIR,
    )
    _write_run_manifest(run_dir, manifest)
    print(f"[bench_solve] Reports will be written to {rel}", flush=True)
    print(f"[bench_solve] Manifest written to {(run_dir / 'run_manifest.json').relative_to(_repo_root())}", flush=True)
    print(
        f"[bench_solve] Profile={BENCH_PROFILE} tiers={len(TIERS)} budgets={','.join(b.name for b in SOLVER_BUDGETS)} "
        f"text_offsets={TEXT_OFFSETS} key_seeds={KEY_SEEDS} modes={seed_modes}",
        flush=True,
    )
    print(
        "[bench_solve] seed_pct_rerank config: "
        f"objective=pct.logp.win10 use_word_breaks=1 "
        f"char_weights={json.dumps(SEED_RERANK_CHAR_WEIGHTS, sort_keys=True)} "
        f"wli_weights={json.dumps(SEED_RERANK_WLI_WEIGHTS, sort_keys=True)}",
        flush=True,
    )
    print(f"[bench_solve] Starting {total_solves} solves ({total_instances} instances x {len(seed_modes)} modes)", flush=True)

    for tier in TIERS:
        for text_id, offset in enumerate(TEXT_OFFSETS):
            pt_idx, wli_list, offset_used = _slice_word_aligned(
                pt_base,
                wli_base,
                length=tier.length,
                offset_hint=offset,
            )
            word_spans = _word_spans_from_wli(wli_list)
            for key_seed in KEY_SEEDS:
                # Skip expensive setup when this entire (tier,text,key_seed) instance is already complete.
                pending_instance = False
                for _budget in SOLVER_BUDGETS:
                    for _mode in seed_modes:
                        rid = (tier.name, _budget.name, _mode, int(text_id), int(key_seed))
                        if rid not in completed:
                            pending_instance = True
                            break
                    if pending_instance:
                        break
                if not pending_instance:
                    continue

                key_len = tier.period * ALPHABET_SIZE + tier.columns
                rng = np.random.default_rng(int(key_seed))
                keyops = PeriodicStructuredMatrixKeyOps(K=key_len, period=tier.period, A=ALPHABET_SIZE, columns=tier.columns)
                key_true = keyops.random(rng).astype(np.int16, copy=False)

                cipher_cfg = CipherConfig(
                    name="periodic_columnar",
                    ciphertext=[],
                    period=tier.period,
                    columns=tier.columns,
                    alphabet_size=ALPHABET_SIZE,
                    key_length=key_len,
                    order=ORDER,
                    encoding_dir=direction,
                    wli_data=[],
                    device=Device.CPU,
                )
                cipher = PeriodicColumnarCipher(cipher_cfg)
                ct_idx = cipher.encrypt_single(plaintext=pt_idx, key=key_true)

                preflight_meta = _preflight_known_key_roundtrip(
                    cipher=cipher,
                    ct_idx=ct_idx,
                    key_true=key_true,
                    pt_true=pt_idx,
                    wli_list=wli_list,
                    raw_full_scorer=raw_full_scorer,
                    pct_scorer=pct_scorer,
                    tier_name=tier.name,
                    text_id=int(text_id),
                    key_seed=int(key_seed),
                )
                print(
                    f"[bench_solve] gate0 ok tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"d_raw_full={preflight_meta['preflight_score_delta_raw_full']:.1e} "
                    f"d_pct={preflight_meta['preflight_score_delta_pct']:.1e}",
                    flush=True,
                )

                oracle_raw_full, oracle_pct, oracle_raw_native = _score_pt(pt_idx, raw_full_scorer=raw_full_scorer, pct_scorer=pct_scorer)
                oracle_wli1 = float(wli1_scorer.score(pt_idx, wli_list))
                oracle_wli2_full = float(wli2_full_scorer.score(pt_idx, wli_list))
                oracle_wli2_within = float(wli2_within_scorer.score(pt_idx, wli_list, word_spans=word_spans))

                # Quick sanity: oracle should beat random under all primary metrics.
                random_raw_full = []
                random_pct = []
                random_raw_native = []
                random_wli1 = []
                random_wli2_full = []
                random_wli2_within = []
                for _ in range(RANDOM_KEYS_SANITY):
                    k = keyops.random(rng).astype(np.int16, copy=False)
                    pt_rand = cipher.decrypt_single(ciphertext=ct_idx, key=k)
                    r_full, r_pct, r_nat = _score_pt(pt_rand, raw_full_scorer=raw_full_scorer, pct_scorer=pct_scorer)
                    random_raw_full.append(r_full)
                    random_pct.append(r_pct)
                    random_raw_native.append(r_nat)
                    random_wli1.append(float(wli1_scorer.score(pt_rand, wli_list)))
                    random_wli2_full.append(float(wli2_full_scorer.score(pt_rand, wli_list)))
                    random_wli2_within.append(float(wli2_within_scorer.score(pt_rand, wli_list, word_spans=word_spans)))
                if not (oracle_raw_full > float(np.max(random_raw_full))):
                    raise RuntimeError("[bench_solve] sanity failure: oracle_raw_fulltext <= best_random_raw_fulltext")
                if not (oracle_pct > float(np.max(random_pct))):
                    raise RuntimeError("[bench_solve] sanity failure: oracle_pct <= best_random_pct")
                if not (oracle_raw_native > float(np.max(random_raw_native))):
                    raise RuntimeError("[bench_solve] sanity failure: oracle_raw_native <= best_random_raw_native")
                if not (oracle_wli1 > float(np.max(random_wli1))):
                    raise RuntimeError("[bench_solve] sanity failure: oracle_wli1 <= best_random_wli1 (WLI wiring likely wrong)")

                disc_char = _oracle_vs_random_stats(oracle_raw_full, random_raw_full)
                disc_wli1 = _oracle_vs_random_stats(oracle_wli1, random_wli1)
                disc_wli2_full = _oracle_vs_random_stats(oracle_wli2_full, random_wli2_full)
                disc_wli2_within = _oracle_vs_random_stats(oracle_wli2_within, random_wli2_within)

                for budget in SOLVER_BUDGETS:
                    budget_pending = any(
                        (tier.name, budget.name, m, int(text_id), int(key_seed)) not in completed for m in seed_modes
                    )
                    if not budget_pending:
                        continue

                    # Seed generator configs (for the two seed modes)
                    seed_cfg = ScoringConfig(
                        model_root=lm_root,
                        encoding_dir=direction,
                        include_char=True,
                        use_word_breaks=False,
                        char_weights=dict(raw_weights),
                        wli_weights={},
                        impl=ScorerImpl.NUMPY,
                    )
                    # Seed rerank uses a sharper mixed objective (char+WLI 1..4)
                    # to reduce char-only false attractors before Stage-1 solve.
                    rerank_cfg = ScoringConfig(
                        model_root=lm_root,
                        encoding_dir=direction,
                        include_char=True,
                        use_word_breaks=True,
                        char_weights=dict(SEED_RERANK_CHAR_WEIGHTS),
                        wli_weights=dict(SEED_RERANK_WLI_WEIGHTS),
                        impl=ScorerImpl.NUMPY,
                        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
                    )

                    seed_pool_raw = None
                    seed_pool_pct = None
                    seed_pool_tail_diverse = None
                    seed_pool_tail_meta = None

                    for mode in seed_modes:
                        row_id = (tier.name, budget.name, mode, int(text_id), int(key_seed))
                        if row_id in completed:
                            continue

                        t0 = time.time()
                        seed_keys = None
                        if mode == "seed_raw":
                            if seed_pool_raw is None:
                                seed_pool_raw = generate_seed_keys_periodic_columnar(
                                    ct_idx,
                                    period=tier.period,
                                    columns=tier.columns,
                                    order=ORDER,
                                    direction=direction,
                                    seed=2026 + int(key_seed),
                                    scoring_cfg=seed_cfg,
                                    n_keys=budget.n_seed_keys,
                                    plan=budget.seed_plan,
                                    refine=True,
                                    rerank_cfg=None,
                                )
                            seed_keys = seed_pool_raw
                        elif mode == "seed_pct_rerank":
                            if seed_pool_pct is None:
                                seed_pool_pct = generate_seed_keys_periodic_columnar(
                                    ct_idx,
                                    period=tier.period,
                                    columns=tier.columns,
                                    order=ORDER,
                                    direction=direction,
                                    seed=2026 + int(key_seed),
                                    scoring_cfg=seed_cfg,
                                    wli_data=wli_list,
                                    n_keys=budget.n_seed_keys,
                                    plan=budget.seed_plan,
                                    refine=True,
                                    rerank_cfg=rerank_cfg,
                                )
                            seed_keys = seed_pool_pct
                        elif mode == "seed_tail_diverse":
                            if seed_pool_tail_diverse is None:
                                seed_pool_tail_diverse, seed_pool_tail_meta = _build_tail_diverse_seed_pool(
                                    ct_idx=ct_idx,
                                    tier=tier,
                                    direction=direction,
                                    seed=2026 + int(key_seed),
                                    budget=budget,
                                    seed_cfg=seed_cfg,
                                )
                            seed_keys = seed_pool_tail_diverse

                        solver_params = dict(getattr(budget.solver, "params", {}) or {})
                        if mode == "seed_pct_rerank":
                            solver_params["seed_selection_metric"] = "pct"
                            seed_selection_policy = "pct_aligned"
                        elif mode in {"seed_raw", "seed_tail_diverse"}:
                            solver_params["seed_selection_metric"] = "raw"
                            seed_selection_policy = "raw_aligned"
                        else:
                            seed_selection_policy = "baseline"
                        if seed_keys is not None:
                            if int(solver_params.get("seed_restarts", 0) or 0) <= 0:
                                solver_params["seed_restarts"] = int(
                                    min(
                                        int(solver_params.get("restarts", 1) or 1),
                                        int(len(seed_keys)),
                                    )
                                )
                        solver_spec = SolverSpec(
                            name=str(getattr(budget.solver, "name", "kaeding")),
                            params=solver_params,
                            seed=getattr(budget.solver, "seed", None),
                        )

                        seed_rerank_applied = bool(mode == "seed_pct_rerank")
                        n_unique_tails_initial_pool = float("nan")
                        n_unique_tails_after_per_tail_retention = float("nan")
                        tail_diverse_mode_used = 0
                        tail_diverse_tail_count_requested = float("nan")
                        tail_diverse_e_tail = float("nan")
                        seed_pool_size = 0
                        seed_pool_hash = ""
                        seed_pool_top1_hash = ""
                        seed_pool_equal_raw = float("nan")
                        seed_pool_overlap_with_raw = float("nan")
                        if seed_keys is not None:
                            seed_pool_size = int(len(seed_keys))
                            seed_pool_hash = _pool_fingerprint(seed_keys)
                            if seed_pool_size > 0:
                                seed_pool_top1_hash = _key_hash(seed_keys[0])
                            if seed_pool_raw is not None and mode == "seed_pct_rerank":
                                seed_pool_equal_raw = float(seed_keys == seed_pool_raw)
                                raw_set = {tuple(int(x) for x in row) for row in seed_pool_raw}
                                this_set = {tuple(int(x) for x in row) for row in seed_keys}
                                seed_pool_overlap_with_raw = float(len(raw_set & this_set)) / float(max(1, len(this_set)))
                            if seed_pool_raw is not None and mode == "seed_tail_diverse":
                                seed_pool_equal_raw = float(seed_keys == seed_pool_raw)
                                raw_set = {tuple(int(x) for x in row) for row in seed_pool_raw}
                                this_set = {tuple(int(x) for x in row) for row in seed_keys}
                                seed_pool_overlap_with_raw = float(len(raw_set & this_set)) / float(max(1, len(this_set)))
                        if mode == "seed_tail_diverse" and isinstance(seed_pool_tail_meta, dict):
                            n_unique_tails_initial_pool = float(seed_pool_tail_meta.get("n_unique_tails_initial_pool", float("nan")))
                            n_unique_tails_after_per_tail_retention = float(
                                seed_pool_tail_meta.get("n_unique_tails_after_per_tail_retention", float("nan"))
                            )
                            tail_diverse_mode_used = int(seed_pool_tail_meta.get("tail_diverse_mode_used", 0) or 0)
                            tail_diverse_tail_count_requested = float(
                                seed_pool_tail_meta.get("tail_diverse_tail_count_requested", float("nan"))
                            )
                            tail_diverse_e_tail = float(seed_pool_tail_meta.get("tail_diverse_e_tail", float("nan")))

                        scorer_params = dict(
                            objective="pct.logp.win10",
                            include_char=True,
                            use_word_breaks=False,
                            char_weights=dict(pct_weights),
                            wli_weights={},
                            encoding_dir=direction,
                            impl=ScorerImpl.NUMPY,
                        )

                        cipher_spec = by_name.cipher(
                            "periodic_columnar",
                            period=tier.period,
                            columns=tier.columns,
                            alphabet_size=ALPHABET_SIZE,
                            order=ORDER,
                        )
                        key_spec = KeySpec.periodic_columnar(
                            period=tier.period,
                            columns=tier.columns,
                            alphabet_size=ALPHABET_SIZE,
                        )

                        sol = run(
                            text=ct_idx.tolist(),
                            cipher=cipher_spec,
                            key=key_spec,
                            solver=solver_spec,
                            device=Device.CPU,
                            scorer_params=scorer_params,
                            telemetry_on=True,
                            encoding_dir=direction,
                            force_no_wli=True,
                            **({} if seed_keys is None else {"initial_keys": seed_keys}),
                        )

                        pt_sol = np.asarray(getattr(sol, "plaintext_idx", []) or [], dtype=np.uint8).reshape(-1)
                        sol_raw_full, sol_pct, sol_raw_native = _score_pt(pt_sol, raw_full_scorer=raw_full_scorer, pct_scorer=pct_scorer)
                        match = _match_ratio(pt_sol.tolist(), pt_idx.tolist())

                        tel = getattr(sol, "meta", {}).get("telemetry", {}) if hasattr(sol, "meta") else {}
                        work = getattr(sol, "meta", {}).get("work", {}) if hasattr(sol, "meta") else {}

                        # ---------------- Stage-2 diagnostics: candidate retention + WLI rerank ----------------
                        stage2_t0 = time.time()

                        cand_keys: List[List[int]] = []
                        k_meta: Dict[str, Any] = {}
                        try:
                            k_meta = tel.get("kaeding", {}) if isinstance(tel, dict) else {}
                            top_keys = k_meta.get("top_keys", None) if isinstance(k_meta, dict) else None
                            if isinstance(top_keys, list):
                                cand_keys.extend([list(map(int, row)) for row in top_keys])
                        except Exception:
                            cand_keys = []
                        try:
                            k_best = getattr(sol, "key", None)
                            if k_best is not None:
                                cand_keys.append(list(map(int, list(k_best))))
                        except Exception:
                            pass

                        # Stable de-dup while preserving order.
                        seen: set[tuple[int, ...]] = set()
                        cand_keys_u: List[List[int]] = []
                        for k in cand_keys:
                            t = tuple(int(x) for x in k)
                            if t in seen:
                                continue
                            seen.add(t)
                            cand_keys_u.append(list(k))
                        cand_keys = cand_keys_u[:TOP_K]

                        # Persist candidate set for auditability / recomputation.
                        cand_dir = run_dir / "candidates"
                        cand_dir.mkdir(parents=True, exist_ok=True)
                        cand_name = f"{tier.name}__{budget.name}__{mode}__text{text_id}__seed{key_seed}.json"
                        cand_path = cand_dir / cand_name
                        _atomic_write_text(cand_path, json.dumps({"keys": cand_keys}, indent=2))

                        sub_len = int(tier.period * ALPHABET_SIZE)
                        tails = [tuple(int(x) for x in k[sub_len:sub_len + int(tier.columns)]) for k in cand_keys]
                        n_unique_tails_topk = int(len(set(tails))) if tails else 0
                        k_diag = int(min(len(cand_keys), int(TAIL_DIVERSE_TOPK_DIAG)))
                        n_unique_tails_topk_by_score = int(len(set(tails[:k_diag]))) if k_diag > 0 else 0
                        n_unique_tails_topk_by_match = n_unique_tails_topk_by_score

                        bestk_match = float(match)
                        pick_wli1_match = float(match)
                        pick_wli2_full_match = float(match)
                        pick_wli2_within_match = float(match)
                        bestk_key_hash = ""
                        pick_wli1_key_hash = ""
                        pick_wli2_full_key_hash = ""
                        pick_wli2_within_key_hash = ""

                        corr_match_raw_full = float("nan")
                        corr_match_pct = float("nan")
                        corr_match_wli2_full = float("nan")
                        corr_match_wli2_within = float("nan")
                        cand_raw_full_spread = float("nan")
                        cand_pct_spread = float("nan")
                        cand_raw_native_spread = float("nan")
                        cand_wli2_full_spread = float("nan")
                        cand_wli2_within_spread = float("nan")
                        cand_raw_full_std = float("nan")
                        cand_pct_std = float("nan")
                        cand_raw_native_std = float("nan")
                        cand_wli2_full_std = float("nan")
                        cand_wli2_within_std = float("nan")

                        preview_oracle = _safe_preview_latin(pt_idx, wli_list)
                        preview_solver_best = _safe_preview_latin(pt_sol, wli_list)
                        preview_bestk_match = preview_solver_best
                        preview_pick_wli1 = preview_solver_best
                        preview_pick_wli2_full = preview_solver_best
                        preview_pick_wli2_within = preview_solver_best

                        if cand_keys:
                            bestk_match = 0.0
                            cand_matches: List[float] = []
                            cand_raw_full: List[float] = []
                            cand_pct: List[float] = []
                            cand_raw_native: List[float] = []
                            cand_wli2_full: List[float] = []
                            cand_wli2_within: List[float] = []
                            cand_pts: List[np.ndarray] = []
                            best_idx_match = None

                            best_idx_wli1 = None
                            best_idx_wli2_full = None
                            best_idx_wli2_within = None
                            best_score_wli1 = float("-inf")
                            best_score_wli2_full = float("-inf")
                            best_score_wli2_within = float("-inf")

                            for i, k_list in enumerate(cand_keys):
                                k_arr = np.asarray(k_list, dtype=np.int16)
                                pt_c = cipher.decrypt_single(ciphertext=ct_idx, key=k_arr)
                                cand_pts.append(np.asarray(pt_c, dtype=np.uint8))
                                m = float(_match_ratio(pt_c.tolist(), pt_idx.tolist()))
                                cand_matches.append(m)
                                if m > bestk_match:
                                    bestk_match = m
                                    best_idx_match = i

                                c_raw_full, c_pct, c_raw_native = _score_pt(pt_c, raw_full_scorer=raw_full_scorer, pct_scorer=pct_scorer)
                                cand_raw_full.append(float(c_raw_full))
                                cand_pct.append(float(c_pct))
                                cand_raw_native.append(float(c_raw_native))

                                s1 = float(wli1_scorer.score(pt_c, wli_list))
                                s2f = float(wli2_full_scorer.score(pt_c, wli_list))
                                s2w = float(wli2_within_scorer.score(pt_c, wli_list, word_spans=word_spans))
                                cand_wli2_full.append(float(s2f))
                                cand_wli2_within.append(float(s2w))
                                if s1 > best_score_wli1:
                                    best_score_wli1 = s1
                                    best_idx_wli1 = i
                                if s2f > best_score_wli2_full:
                                    best_score_wli2_full = s2f
                                    best_idx_wli2_full = i
                                if s2w > best_score_wli2_within:
                                    best_score_wli2_within = s2w
                                    best_idx_wli2_within = i

                            if best_idx_match is not None:
                                bestk_key_hash = _key_hash(cand_keys[best_idx_match])
                                preview_bestk_match = _safe_preview_latin(cand_pts[best_idx_match], wli_list)
                            if best_idx_wli1 is not None:
                                pick_wli1_match = float(cand_matches[best_idx_wli1])
                                pick_wli1_key_hash = _key_hash(cand_keys[best_idx_wli1])
                                preview_pick_wli1 = _safe_preview_latin(cand_pts[best_idx_wli1], wli_list)
                            if best_idx_wli2_full is not None:
                                pick_wli2_full_match = float(cand_matches[best_idx_wli2_full])
                                pick_wli2_full_key_hash = _key_hash(cand_keys[best_idx_wli2_full])
                                preview_pick_wli2_full = _safe_preview_latin(cand_pts[best_idx_wli2_full], wli_list)
                            if best_idx_wli2_within is not None:
                                pick_wli2_within_match = float(cand_matches[best_idx_wli2_within])
                                pick_wli2_within_key_hash = _key_hash(cand_keys[best_idx_wli2_within])
                                preview_pick_wli2_within = _safe_preview_latin(cand_pts[best_idx_wli2_within], wli_list)

                            corr_match_raw_full = _corrcoef_safe(cand_raw_full, cand_matches)
                            corr_match_pct = _corrcoef_safe(cand_pct, cand_matches)
                            corr_match_wli2_full = _corrcoef_safe(cand_wli2_full, cand_matches)
                            corr_match_wli2_within = _corrcoef_safe(cand_wli2_within, cand_matches)
                            cand_raw_full_spread = _spread(cand_raw_full)
                            cand_pct_spread = _spread(cand_pct)
                            cand_raw_native_spread = _spread(cand_raw_native)
                            cand_wli2_full_spread = _spread(cand_wli2_full)
                            cand_wli2_within_spread = _spread(cand_wli2_within)
                            cand_raw_full_std = _std(cand_raw_full)
                            cand_pct_std = _std(cand_pct)
                            cand_raw_native_std = _std(cand_raw_native)
                            cand_wli2_full_std = _std(cand_wli2_full)
                            cand_wli2_within_std = _std(cand_wli2_within)
                            if k_diag > 0 and tails:
                                order = np.argsort(np.asarray(cand_matches, dtype=np.float64))[::-1][:k_diag]
                                n_unique_tails_topk_by_match = int(len({tails[int(i)] for i in order}))

                        seed_selected_idx = int(k_meta.get("seed_selected_index", -1)) if isinstance(k_meta, dict) else -1
                        seed_selected_hash = str(k_meta.get("seed_selected_hash", "")) if isinstance(k_meta, dict) else ""
                        seed_selected_source = str(k_meta.get("seed_selected_source", "")) if isinstance(k_meta, dict) else ""
                        seed_selected_metric = str(k_meta.get("seed_selection_metric", "")) if isinstance(k_meta, dict) else ""
                        seed_selected_raw = float(k_meta.get("seed_selected_raw", float("nan"))) if isinstance(k_meta, dict) else float("nan")
                        seed_selected_pct = float(k_meta.get("seed_selected_pct", float("nan"))) if isinstance(k_meta, dict) else float("nan")
                        block_accept_count = int(k_meta.get("block_accept_count", -1)) if isinstance(k_meta, dict) else -1
                        col_accept_count = int(k_meta.get("col_accept_count", -1)) if isinstance(k_meta, dict) else -1
                        slip_count = int(k_meta.get("slip_count", -1)) if isinstance(k_meta, dict) else -1
                        tail_accept_ratio = (
                            float(col_accept_count) / float(max(1, block_accept_count + col_accept_count))
                            if (block_accept_count >= 0 and col_accept_count >= 0)
                            else float("nan")
                        )

                        stage2_seconds = float(time.time() - stage2_t0)

                        dt = time.time() - t0
                        rows.append(
                            dict(
                                tier=tier.name,
                                budget=budget.name,
                                mode=mode,
                                period=tier.period,
                                columns=tier.columns,
                                length=tier.length,
                                text_id=int(text_id),
                                offset_hint=int(offset),
                                offset_used=int(offset_used),
                                key_seed=int(key_seed),
                                preflight_roundtrip_ok=int(preflight_meta.get("preflight_roundtrip_ok", 0)),
                                preflight_score_delta_raw_full=float(preflight_meta.get("preflight_score_delta_raw_full", float("nan"))),
                                preflight_score_delta_pct=float(preflight_meta.get("preflight_score_delta_pct", float("nan"))),
                                preflight_score_delta_raw_native=float(preflight_meta.get("preflight_score_delta_raw_native", float("nan"))),
                                oracle_raw_full=oracle_raw_full,
                                oracle_raw_native=oracle_raw_native,
                                oracle_pct=oracle_pct,
                                oracle_wli1=oracle_wli1,
                                oracle_wli2_full=oracle_wli2_full,
                                oracle_wli2_within=oracle_wli2_within,
                                best_random_raw_full=float(np.max(random_raw_full)),
                                best_random_pct=float(np.max(random_pct)),
                                best_random_raw_native=float(np.max(random_raw_native)),
                                best_random_wli1=float(np.max(random_wli1)),
                                best_random_wli2_full=float(np.max(random_wli2_full)),
                                best_random_wli2_within=float(np.max(random_wli2_within)),
                                disc_char_oracle_pctile=float(disc_char["oracle_pctile"]),
                                disc_char_sep_z=float(disc_char["sep_z"]),
                                disc_wli1_oracle_pctile=float(disc_wli1["oracle_pctile"]),
                                disc_wli1_sep_z=float(disc_wli1["sep_z"]),
                                disc_wli2_full_oracle_pctile=float(disc_wli2_full["oracle_pctile"]),
                                disc_wli2_full_sep_z=float(disc_wli2_full["sep_z"]),
                                disc_wli2_within_oracle_pctile=float(disc_wli2_within["oracle_pctile"]),
                                disc_wli2_within_sep_z=float(disc_wli2_within["sep_z"]),
                                sol_score=float(getattr(sol, "score", float("nan"))),
                                sol_raw_full=sol_raw_full,
                                sol_raw_native=sol_raw_native,
                                sol_pct=sol_pct,
                                match_ratio=match,
                                bestk_match_ratio=bestk_match,
                                pick_wli1_match_ratio=pick_wli1_match,
                                pick_wli2_full_match_ratio=pick_wli2_full_match,
                                pick_wli2_within_match_ratio=pick_wli2_within_match,
                                n_unique_tails_topk=n_unique_tails_topk,
                                n_unique_tails_topk_by_score=n_unique_tails_topk_by_score,
                                n_unique_tails_topk_by_match=n_unique_tails_topk_by_match,
                                n_unique_tails_initial_pool=n_unique_tails_initial_pool,
                                n_unique_tails_after_per_tail_retention=n_unique_tails_after_per_tail_retention,
                                corr_match_raw_full=corr_match_raw_full,
                                corr_match_pct=corr_match_pct,
                                corr_match_wli2_full=corr_match_wli2_full,
                                corr_match_wli2_within=corr_match_wli2_within,
                                cand_raw_full_spread=cand_raw_full_spread,
                                cand_pct_spread=cand_pct_spread,
                                cand_raw_native_spread=cand_raw_native_spread,
                                cand_wli2_full_spread=cand_wli2_full_spread,
                                cand_wli2_within_spread=cand_wli2_within_spread,
                                cand_raw_full_std=cand_raw_full_std,
                                cand_pct_std=cand_pct_std,
                                cand_raw_native_std=cand_raw_native_std,
                                cand_wli2_full_std=cand_wli2_full_std,
                                cand_wli2_within_std=cand_wli2_within_std,
                                seed_selection_policy=seed_selection_policy,
                                seed_rerank_applied=int(seed_rerank_applied),
                                seed_selection_metric_requested=str(solver_params.get("seed_selection_metric", "auto")),
                                seed_restarts_requested=int(solver_params.get("seed_restarts", 0) or 0),
                                seed_rerank_objective="pct.logp.win10",
                                seed_rerank_use_word_breaks=1,
                                seed_rerank_char_weights=json.dumps(SEED_RERANK_CHAR_WEIGHTS, sort_keys=True),
                                seed_rerank_wli_weights=json.dumps(SEED_RERANK_WLI_WEIGHTS, sort_keys=True),
                                seed_pool_size=seed_pool_size,
                                seed_pool_hash=seed_pool_hash,
                                seed_pool_top1_hash=seed_pool_top1_hash,
                                seed_pool_equal_raw=seed_pool_equal_raw,
                                seed_pool_overlap_with_raw=seed_pool_overlap_with_raw,
                                tail_diverse_mode_used=tail_diverse_mode_used,
                                tail_diverse_tail_count_requested=tail_diverse_tail_count_requested,
                                tail_diverse_e_tail=tail_diverse_e_tail,
                                seed_selected_source=seed_selected_source,
                                seed_selected_metric=seed_selected_metric,
                                seed_selected_index=seed_selected_idx,
                                seed_selected_hash=seed_selected_hash,
                                seed_selected_raw=seed_selected_raw,
                                seed_selected_pct=seed_selected_pct,
                                block_accept_count=block_accept_count,
                                col_accept_count=col_accept_count,
                                slip_count=slip_count,
                                tail_accept_ratio=tail_accept_ratio,
                                bestk_key_hash=bestk_key_hash,
                                pick_wli1_key_hash=pick_wli1_key_hash,
                                pick_wli2_full_key_hash=pick_wli2_full_key_hash,
                                pick_wli2_within_key_hash=pick_wli2_within_key_hash,
                                preview_oracle_latin=preview_oracle,
                                preview_solver_best_latin=preview_solver_best,
                                preview_bestk_match_latin=preview_bestk_match,
                                preview_pick_wli1_latin=preview_pick_wli1,
                                preview_pick_wli2_full_latin=preview_pick_wli2_full,
                                preview_pick_wli2_within_latin=preview_pick_wli2_within,
                                evals=int(work.get("evals", 0) or 0),
                                tokens=int(work.get("tokens", 0) or 0),
                                seconds=round(dt, 3),
                                stage2_seconds=round(stage2_seconds, 3),
                                candidates=int(len(cand_keys)),
                                candidate_file=str(cand_path.relative_to(run_dir)).replace("\\", "/"),
                            )
                        )
                        completed.add(row_id)

                        done_solves += 1
                        elapsed = time.time() - t0_all
                        avg = elapsed / float(done_solves) if done_solves else 0.0
                        eta = avg * float(total_solves - done_solves)
                        _checkpoint(run_dir, rows=rows)
                        print(
                            f"[bench_solve] {done_solves}/{total_solves} "
                            f"tier={tier.name} budget={budget.name} mode={mode} "
                            f"text={text_id} key_seed={key_seed} "
                            f"run={_format_seconds(dt)} elapsed={_format_seconds(elapsed)} eta={_format_seconds(eta)}"
                            , flush=True
                        )

    summary = _checkpoint(run_dir, rows=rows)
    total = time.time() - t0_all
    print(f"[bench_solve] Completed in {total:.1f}s. Reports written to {rel}", flush=True)
    print("\n[bench_solve] Summary (p50) by tier/budget/mode")
    for tier, entries in summary.get("tiers", {}).items():
        print(f"\nTier: {tier}")
        for e in entries:
            print(
                f"  Budget={e['budget']} Mode={e['mode']} N={e['n']} "
                f"raw_full_p50={e['sol_raw_full']['p50']:.4f} "
                f"raw_native_p50={e['sol_raw_native']['p50']:.4f} "
                f"pct_p50={e['sol_pct']['p50']:.4f} "
                f"match_p50={e['match_ratio']['p50']:.3f} "
                f"bestk_match_p50={e['bestk_match_ratio']['p50']:.3f} "
                f"unique_tails_p50={e['n_unique_tails_topk']['p50']:.1f} "
                f"unique_tail_scoreK_p50={e['n_unique_tails_topk_by_score']['p50']:.1f} "
                f"unique_tail_matchK_p50={e['n_unique_tails_topk_by_match']['p50']:.1f} "
                f"pick_wli2_full_p50={e['pick_wli2_full_match_ratio']['p50']:.3f} "
                f"pick_wli2_within_p50={e['pick_wli2_within_match_ratio']['p50']:.3f} "
                f"wli2full-bestk_p50={e['wli2_full_minus_bestk']['p50']:.3f} "
                f"rate_pct>oracle={e['rate_sol_gt_oracle_pct']:.2f} "
                f"seedpool_eq_raw={e['rate_seed_pool_equal_raw']:.2f} "
                f"evals_p50={e['evals']['p50']:.0f}"
            )

    _print_run_warnings(rows)


if __name__ == "__main__":
    main()
