from __future__ import annotations

"""
Practical staged solve benchmark (no cribs) for periodic-columnar.

Goal:
- use the known effective staged solve shape (substitution -> columnar -> full refine)
- stop per instance when solved (match_ratio >= threshold) or stalled
- keep append-only history for proven solves

Scoring used:
- Stage 1 (`stage1_sub`): `pct.logp.win10`, char unigram only (`char_weights={1:1.0}`),
  no WLI (`force_no_wli=True`).
- Stage 2/3: `pct.logp.win10`, mixed char+WLI (`char 3/4`, `wli 3/4`), WLI enabled.
- Stage 2 exact tail search is used for small columns (`C<=7`) to preserve proven
  solve behaviour from existing tutorials.

This is intentionally tutorial-aligned for practical solve progress, not a pure
raw-fulltext optimisation benchmark.
"""

import csv
import json
import subprocess
import sys
import time
from itertools import permutations
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import Direction, KeySpec, SolverSpec, by_name, run
from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.ciphers.periodic_substitution_cipher import PeriodicSubstitutionCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Device
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps
from rune_decrypter_prime.utils.seed_utils import make_periodic_seed_pool

from tools.benchmarks import bench_solve_periodic_columnar_kaeding as base

ALPHABET_SIZE = 29
ORDER = "col_then_sub"
PROFILE = "pipeline_fulltext_v1"
PIPELINE_RUN_MODE = "focus_p10_fast"  # "full" | "focus_p5_p7" | "focus_p10_fast" | "smoke"

SOLVE_MATCH_THRESHOLD = 0.90
STALL_DELTA = 0.002
STALL_STAGE_LIMIT = 1
HEARTBEAT_SECONDS = 1200  # human-facing checkpoint (~3 updates/hour on long runs)
PREVIEW_CHARS = 240

TEXT_OFFSETS = [0]
KEY_SEEDS = [111]
STAGE1_SUB_CANDIDATES = 16
STAGE3_INITIAL_KEYS = 24
STAGE1_SUB_CANDIDATES_BY_COLUMNS = {1: 6, 3: 10, 5: 12, 7: 14}
STAGE3_INITIAL_KEYS_BY_COLUMNS = {1: 8, 3: 12, 5: 16, 7: 20}
STAGE2_EXACT_MAX_COLUMNS = 7
STAGE2_EXACT_SUB_CANDIDATES = 2
STAGE2_EXACT_TWO_PASS = True
STAGE2_EXACT_PASS1_TOP_TAILS = 256
STAGE2_EXACT_EARLY_SOLVE_BREAK = True
STAGE2_FAST_CHAR_WEIGHTS = {3: 0.5, 4: 0.5}
STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS = {3: 4, 5: 3, 7: 2}
STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS = {3: 72, 5: 128, 7: 192}
STAGE1_USE_ORACLE_GUIDE_STOP = True
STAGE1_ORACLE_STOP_MARGIN = 0.005
STAGE3_USE_ORACLE_GUIDE_STOP = False
STAGE3_ORACLE_STOP_MARGIN = 0.002
STAGE3_ORACLE_STOP_RELAX_FRACTION = 0.0  # 0.10 => accept 10% below oracle objective
STAGE1_SEED_RESTARTS = 64
STAGE1_SEED_N_BLOCKS = 18
STAGE1_SEED_TOTAL = 256
STAGE1_SEED_SWAPS = 3

# Stage-3 dynamic budget based on stage2 objective gap to oracle objective (same scorer).
# Lower gap => lighter stage3; higher gap => heavier stage3.
STAGE3_DYNAMIC_BANDS = [
    dict(name="very_close", max_gap=0.010, steps=1800, restarts=1, plateau_rounds=220, col_batch=96, inner_batch=128),
    dict(name="close", max_gap=0.030, steps=3200, restarts=1, plateau_rounds=320, col_batch=112, inner_batch=128),
    dict(name="mid", max_gap=0.080, steps=4800, restarts=2, plateau_rounds=420, col_batch=128, inner_batch=128),
    dict(name="far", max_gap=1e9, steps=7200, restarts=2, plateau_rounds=560, col_batch=128, inner_batch=128),
]

SCORER_STAGE1 = dict(objective="pct.logp.win10", include_char=True, use_word_breaks=False, char_weights={1: 1.0}, wli_weights={})
SCORER_FULL = dict(objective="pct.logp.win10", include_char=True, use_word_breaks=True, char_weights={3: 0.3, 4: 0.7}, wli_weights={3: 0.4, 4: 0.6})

SOLVER_STAGE1 = dict(
    steps=9000, restarts=5, inner_batch=256, slip_every=0, slip_blocks=1, slip_policy="stall",
    stall_rounds=250, stall_slip_limit=3, slip_swaps=24, stall_stop_on_limit=True,
    block_schedule="round_robin", col_every=0, col_batch=0,
    use_raw_score=False, raw_accept_min_delta=1e-6, pct_plateau_min_delta=1e-4,
    plateau_rounds=900, plateau_min_delta=5e-4,
    delta_window=200, top_k=64, progress_pct=2, print_progress=True, seed=2026,
    seed_restarts=64,
)

SOLVER_STAGE2 = dict(
    use_beam=True, beam_width=96, rounds=6, expand_mode="sample", sample_per_parent=64, top_parents_factor=0.4,
    progress_pct=10, print_progress=True,
    ga=dict(pop_size=160, generations=120, elite_frac=0.1, cx_frac=0.85, mut_prob=0.30, tournament_k=3, plateau_rounds=24, stop_score=1.0, print_progress=True),
    sa=dict(sa_iters=4000, sa_init_temp=0.95, sa_min_temp=1e-4, sa_cooling=0.997, plateau_rounds=400, local_improve_on_accept=True, stop_score=1.0, print_progress=True),
    seed=2026, verbose=True, log_interval=10, stop_score=1.0,
)

SOLVER_STAGE3 = dict(
    steps=20000, restarts=4, inner_batch=256, col_every=1, col_batch=256, slip_every=80, slip_blocks=1, slip_policy="stall",
    stall_rounds=220, stall_slip_limit=4, slip_swaps=50, use_raw_score=False, raw_accept_min_delta=1e-6,
    pct_plateau_min_delta=1e-4, plateau_rounds=1800, plateau_min_delta=2e-4,
    delta_window=200, top_k=32, progress_pct=5, print_progress=True, seed=2026,
)


@dataclass(frozen=True)
class Tier:
    name: str
    period: int
    columns: int
    length: int


TIERS = [
    Tier("proof_p5_c1_l2376", 5, 1, 2376),
    Tier("proof_p5_c3_l2376", 5, 3, 2376),
    Tier("proof_p5_c5_l2376", 5, 5, 2376),
    Tier("proof_p5_c9_l2376", 5, 9, 2376),
    Tier("proof_p10_c1_l2376", 10, 1, 2376),
    Tier("proof_p10_c3_l2376", 10, 3, 2376),
    Tier("proof_p10_c7_l2376", 10, 7, 2376),
    Tier("proof_p10_c10_l2376", 10, 10, 2376),
    Tier("proof_p13_c1_l2376", 13, 1, 2376),
    Tier("proof_p13_c3_l2376", 13, 3, 2376),
    Tier("proof_p13_c9_l2376", 13, 9, 2376),
    Tier("proof_p13_c13_l2376", 13, 13, 2376),
]


def _apply_run_mode() -> None:
    global PROFILE, HEARTBEAT_SECONDS, TIERS, TEXT_OFFSETS, KEY_SEEDS, STAGE1_SUB_CANDIDATES, STAGE3_INITIAL_KEYS
    global STAGE2_EXACT_SUB_CANDIDATES, STAGE1_SEED_RESTARTS
    global STAGE2_EXACT_PASS1_TOP_TAILS, STAGE2_EXACT_TWO_PASS, STAGE2_EXACT_EARLY_SOLVE_BREAK
    global STAGE1_SEED_N_BLOCKS, STAGE1_SEED_TOTAL, STAGE1_SEED_SWAPS
    global STAGE1_SUB_CANDIDATES_BY_COLUMNS, STAGE3_INITIAL_KEYS_BY_COLUMNS, STAGE3_DYNAMIC_BANDS
    global STAGE3_USE_ORACLE_GUIDE_STOP, STAGE3_ORACLE_STOP_MARGIN, STAGE3_ORACLE_STOP_RELAX_FRACTION
    if PIPELINE_RUN_MODE == "full":
        return
    if PIPELINE_RUN_MODE == "focus_p5_p7":
        PROFILE = "pipeline_focus_p5_p7_v1"
        HEARTBEAT_SECONDS = 900
        TIERS = [
            Tier("focus_p5_c1_l2376", 5, 1, 2376),
            Tier("focus_p5_c3_l2376", 5, 3, 2376),
            Tier("focus_p5_c5_l2376", 5, 5, 2376),
            Tier("focus_p5_c7_l2376", 5, 7, 2376),
            Tier("focus_p7_c1_l2376", 7, 1, 2376),
            Tier("focus_p7_c3_l2376", 7, 3, 2376),
            Tier("focus_p7_c5_l2376", 7, 5, 2376),
            Tier("focus_p7_c7_l2376", 7, 7, 2376),
        ]
        TEXT_OFFSETS = [0]
        KEY_SEEDS = [111]
        STAGE1_SUB_CANDIDATES = 16
        STAGE3_INITIAL_KEYS = 16
        STAGE2_EXACT_SUB_CANDIDATES = 3
        STAGE2_EXACT_PASS1_TOP_TAILS = 256
        STAGE2_EXACT_TWO_PASS = True
        STAGE2_EXACT_EARLY_SOLVE_BREAK = True
        STAGE1_SEED_RESTARTS = 96
        STAGE1_SEED_N_BLOCKS = 18
        STAGE1_SEED_TOTAL = 256
        STAGE1_SEED_SWAPS = 3

        SOLVER_STAGE1.update(
            steps=2600,
            restarts=2,
            inner_batch=128,
            top_k=24,
            seed_restarts=96,
            plateau_rounds=360,
            plateau_min_delta=5e-4,
            progress_pct=10,
            print_progress=True,
        )
        SOLVER_STAGE2.update(
            beam_width=72,
            rounds=4,
            sample_per_parent=48,
            top_parents_factor=0.4,
            progress_pct=10,
            print_progress=True,
        )
        SOLVER_STAGE2["ga"].update(
            pop_size=120,
            generations=72,
            plateau_rounds=18,
            print_progress=True,
        )
        SOLVER_STAGE2["sa"].update(
            sa_iters=2600,
            plateau_rounds=280,
            print_progress=True,
        )
        SOLVER_STAGE3.update(
            steps=5200,
            restarts=2,
            inner_batch=128,
            col_every=1,
            col_batch=128,
            top_k=24,
            plateau_rounds=520,
            plateau_min_delta=2e-4,
            progress_pct=10,
            print_progress=True,
        )
        return
    if PIPELINE_RUN_MODE == "focus_p10_fast":
        PROFILE = "pipeline_focus_p10_fast_v1"
        HEARTBEAT_SECONDS = 900
        TIERS = [
            Tier("focus_p10_c1_l2376", 10, 1, 2376),
            Tier("focus_p10_c3_l2376", 10, 3, 2376),
            Tier("focus_p10_c5_l2376", 10, 5, 2376),
            Tier("focus_p10_c7_l2376", 10, 7, 2376),
            Tier("focus_p10_c10_l2376", 10, 10, 2376),
        ]
        TEXT_OFFSETS = [0]
        KEY_SEEDS = [111]

        STAGE1_SUB_CANDIDATES = 14
        STAGE1_SUB_CANDIDATES_BY_COLUMNS = {1: 6, 3: 9, 5: 11, 7: 12, 10: 12}
        STAGE3_INITIAL_KEYS = 14
        STAGE3_INITIAL_KEYS_BY_COLUMNS = {1: 8, 3: 10, 5: 12, 7: 16, 10: 18}

        STAGE2_EXACT_SUB_CANDIDATES = 3
        STAGE2_EXACT_PASS1_TOP_TAILS = 160
        STAGE2_EXACT_TWO_PASS = True
        STAGE2_EXACT_EARLY_SOLVE_BREAK = True
        STAGE1_SEED_RESTARTS = 96
        STAGE1_SEED_N_BLOCKS = 16
        STAGE1_SEED_TOTAL = 224
        STAGE1_SEED_SWAPS = 3

        STAGE3_DYNAMIC_BANDS = [
            dict(name="very_close", max_gap=0.010, steps=900, restarts=1, plateau_rounds=140, col_batch=96, inner_batch=128),
            dict(name="close", max_gap=0.030, steps=1600, restarts=1, plateau_rounds=200, col_batch=96, inner_batch=128),
            dict(name="mid", max_gap=0.080, steps=2600, restarts=1, plateau_rounds=260, col_batch=112, inner_batch=128),
            dict(name="far", max_gap=1e9, steps=4000, restarts=1, plateau_rounds=320, col_batch=112, inner_batch=128),
        ]
        STAGE3_USE_ORACLE_GUIDE_STOP = True
        STAGE3_ORACLE_STOP_MARGIN = 0.0
        STAGE3_ORACLE_STOP_RELAX_FRACTION = 0.10

        SOLVER_STAGE1.update(
            steps=2400,
            restarts=2,
            inner_batch=128,
            top_k=22,
            seed_restarts=96,
            plateau_rounds=320,
            plateau_min_delta=5e-4,
            progress_pct=5,
            print_progress=True,
        )
        SOLVER_STAGE2.update(
            beam_width=64,
            rounds=4,
            sample_per_parent=40,
            top_parents_factor=0.4,
            progress_pct=10,
            print_progress=True,
        )
        SOLVER_STAGE2["ga"].update(
            pop_size=96,
            generations=60,
            plateau_rounds=16,
            print_progress=True,
        )
        SOLVER_STAGE2["sa"].update(
            sa_iters=2200,
            plateau_rounds=240,
            print_progress=True,
        )
        SOLVER_STAGE3.update(
            steps=4000,
            restarts=1,
            inner_batch=128,
            col_every=1,
            col_batch=112,
            top_k=20,
            plateau_rounds=320,
            plateau_min_delta=4e-4,
            progress_pct=1,
            print_progress=True,
        )
        return
    if PIPELINE_RUN_MODE == "smoke":
        PROFILE = "pipeline_smoke_v1"
        HEARTBEAT_SECONDS = 120
        TIERS = [
            Tier("smoke_p5_c1_l400", 5, 1, 400),
            Tier("smoke_p5_c3_l400", 5, 3, 400),
        ]
        TEXT_OFFSETS = [0]
        KEY_SEEDS = [111]
        STAGE1_SUB_CANDIDATES = 1
        STAGE3_INITIAL_KEYS = 6
        STAGE2_EXACT_SUB_CANDIDATES = 1
        STAGE2_EXACT_PASS1_TOP_TAILS = 48
        STAGE2_EXACT_TWO_PASS = True
        STAGE2_EXACT_EARLY_SOLVE_BREAK = True
        STAGE1_SEED_RESTARTS = 8
        STAGE1_SEED_N_BLOCKS = 8
        STAGE1_SEED_TOTAL = 64
        STAGE1_SEED_SWAPS = 2

        SOLVER_STAGE1.update(
            steps=80,
            restarts=1,
            inner_batch=64,
            top_k=8,
            seed_restarts=8,
            plateau_rounds=40,
            plateau_min_delta=1e-3,
            progress_pct=20,
            print_progress=True,
        )
        SOLVER_STAGE2.update(
            beam_width=24,
            rounds=2,
            sample_per_parent=16,
            top_parents_factor=0.5,
            progress_pct=20,
            print_progress=True,
        )
        SOLVER_STAGE2["ga"].update(
            pop_size=48,
            generations=20,
            plateau_rounds=8,
            print_progress=True,
        )
        SOLVER_STAGE2["sa"].update(
            sa_iters=800,
            plateau_rounds=120,
            print_progress=True,
        )
        SOLVER_STAGE3.update(
            steps=120,
            restarts=1,
            inner_batch=64,
            col_batch=24,
            top_k=8,
            plateau_rounds=60,
            plateau_min_delta=1e-3,
            progress_pct=20,
            print_progress=True,
        )
        return
    raise ValueError(
        f"Unknown PIPELINE_RUN_MODE={PIPELINE_RUN_MODE!r}; "
        "expected 'full', 'focus_p5_p7', 'focus_p10_fast', or 'smoke'"
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_short() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=_repo_root()).decode().strip() or "nogit"
    except Exception:
        return "nogit"


def _extract_top_keys(sol: Any, limit: int) -> List[List[int]]:
    out: List[List[int]] = []
    try:
        tel = getattr(sol, "meta", {}).get("telemetry", {})
        km = tel.get("kaeding", {}) if isinstance(tel, dict) else {}
        top = km.get("top_keys", None) if isinstance(km, dict) else None
        if isinstance(top, list):
            out.extend([list(map(int, row)) for row in top])
    except Exception:
        pass
    try:
        if getattr(sol, "key", None) is not None:
            out.append(list(map(int, list(sol.key))))
    except Exception:
        pass
    seen: set[tuple[int, ...]] = set()
    dedup: List[List[int]] = []
    for k in out:
        t = tuple(int(x) for x in k)
        if t in seen:
            continue
        seen.add(t)
        dedup.append(list(k))
        if len(dedup) >= int(limit):
            break
    return dedup


def _mutate_full_key(base_key: Sequence[int], *, period: int, columns: int, seed: int, n: int) -> List[List[int]]:
    rng = np.random.default_rng(int(seed))
    base = np.asarray(base_key, dtype=np.int16).copy()
    out = [base.astype(int).tolist()]
    sub_len = int(period) * ALPHABET_SIZE
    while len(out) < int(n):
        k = base.copy()
        ph = int(rng.integers(0, int(period)))
        a = int(rng.integers(0, ALPHABET_SIZE))
        b = int(rng.integers(0, ALPHABET_SIZE - 1))
        if b >= a:
            b += 1
        i1, i2 = int(ph * ALPHABET_SIZE + a), int(ph * ALPHABET_SIZE + b)
        k[i1], k[i2] = k[i2], k[i1]
        if int(columns) > 1:
            a = int(rng.integers(0, int(columns)))
            b = int(rng.integers(0, int(columns - 1)))
            if b >= a:
                b += 1
            t1, t2 = int(sub_len + a), int(sub_len + b)
            k[t1], k[t2] = k[t2], k[t1]
        out.append(k.astype(int).tolist())
    return out[: int(n)]


def _preview_latin(pt: Sequence[int], wli: Sequence[Sequence[int]]) -> str:
    return base._safe_preview_latin(pt, wli, limit=PREVIEW_CHARS)


def _print_stage_preview(
    *,
    label: str,
    pt: Sequence[int],
    wli: Sequence[Sequence[int]],
    scorer_wli: bool,
    match_ratio: float | None = None,
) -> None:
    txt = _preview_latin(pt, wli)
    mr_txt = ""
    if match_ratio is not None and np.isfinite(float(match_ratio)):
        mr_txt = f" match_ratio={float(match_ratio):.3f}"
    print(
        f"[pipeline] preview {label} scorer_wli={'on' if scorer_wli else 'off'} "
        f"len={len(pt)} words={len(wli)}{mr_txt} text=\"{txt}\"",
        flush=True,
    )


def _objective_text(obj: Any) -> str:
    family = str(getattr(obj, "family", "unknown"))
    stat = str(getattr(obj, "stat", "unknown"))
    win = getattr(obj, "win", None)
    fam_txt = family.split(".")[-1].lower()
    stat_txt = stat.split(".")[-1].lower()
    return f"{fam_txt}.{stat_txt}.win{int(win) if win is not None else 'na'}"


def _weights_text(weights: Dict[int, float]) -> str:
    if not weights:
        return "{}"
    parts = [f"{int(k)}:{float(v):g}" for k, v in sorted(weights.items(), key=lambda kv: int(kv[0]))]
    return "{" + ",".join(parts) + "}"


def _select_stage3_band(gap_to_oracle: float) -> Dict[str, Any]:
    gap = float(gap_to_oracle)
    for band in STAGE3_DYNAMIC_BANDS:
        if gap <= float(band.get("max_gap", 1e9)):
            return dict(band)
    return dict(STAGE3_DYNAMIC_BANDS[-1])


def _oracle_score_for_stage(
    *,
    pt_idx: np.ndarray,
    wli: Sequence[Sequence[int]],
    cipher_cfg: CipherConfig,
    scorer_params: Dict[str, Any],
) -> Tuple[float, float, str]:
    s_cfg = ScoringConfig(**scorer_params)
    scorer = build_scorer(cipher_cfg, s_cfg)
    use_wli = bool(getattr(s_cfg, "use_word_breaks", False))
    wli_arg = wli if use_wli else None
    score, raw = scorer.score_with_raw(pt_idx, wli_arg)
    return float(score), float(raw), _objective_text(getattr(s_cfg, "objective", None))


def _write_csv_rows(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames: List[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key in seen:
                continue
            seen.add(key)
            fieldnames.append(str(key))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def main() -> None:
    _apply_run_mode()
    direction = Direction.LTR
    print("[pipeline] bootstrap: checking LM assets...", flush=True)
    base._require_assets(direction, ns=(1, 3, 4), need_wli=True)
    pt_base, wli_base = base._encode_long_plaintext(direction)

    root = _repo_root()
    out_root = root / "output" / "tools" / "benchmarks"
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / f"{stamp}__bench_solve_pipeline__{_git_short()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"[pipeline] setup: profile={PROFILE} mode={PIPELINE_RUN_MODE} "
        f"direction={direction.value} order={ORDER} A={ALPHABET_SIZE}",
        flush=True,
    )
    print(f"[pipeline] setup: threshold={SOLVE_MATCH_THRESHOLD:.3f} stall_delta={STALL_DELTA:.4f} stall_limit={STALL_STAGE_LIMIT}", flush=True)
    print(
        "[pipeline] setup: objective=pct.logp.win10 "
        "stage1=(char1,wli_off) stage2/3=(char34+wli34,wli_on)",
        flush=True,
    )
    print(
        "[pipeline] setup: stop guards "
        f"stage1_plateau=(rounds={SOLVER_STAGE1.get('plateau_rounds')},delta={SOLVER_STAGE1.get('plateau_min_delta')}) "
        f"stage3_plateau=(rounds={SOLVER_STAGE3.get('plateau_rounds')},delta={SOLVER_STAGE3.get('plateau_min_delta')}) "
        f"stage1_oracle_stop={'on' if STAGE1_USE_ORACLE_GUIDE_STOP else 'off'} "
        f"stage3_oracle_stop={'on' if STAGE3_USE_ORACLE_GUIDE_STOP else 'off'} "
        f"stage3_oracle_relax={float(STAGE3_ORACLE_STOP_RELAX_FRACTION):.3f}",
        flush=True,
    )
    print(
        "[pipeline] setup: search knobs "
        f"stage1_seed_restarts={STAGE1_SEED_RESTARTS} "
        f"stage1_seed_plan=(blocks={STAGE1_SEED_N_BLOCKS},total={STAGE1_SEED_TOTAL},swaps={STAGE1_SEED_SWAPS}) "
        f"stage1_sub_candidates={STAGE1_SUB_CANDIDATES} "
        f"stage1_sub_by_c={json.dumps(STAGE1_SUB_CANDIDATES_BY_COLUMNS, separators=(',', ':'))} "
        f"stage3_init_keys={STAGE3_INITIAL_KEYS} "
        f"stage3_init_by_c={json.dumps(STAGE3_INITIAL_KEYS_BY_COLUMNS, separators=(',', ':'))} "
        f"stage2_exact_max_columns={STAGE2_EXACT_MAX_COLUMNS} "
        f"stage2_exact_sub_candidates={STAGE2_EXACT_SUB_CANDIDATES} "
        f"stage2_exact_sub_by_c={json.dumps(STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS, separators=(',', ':'))} "
        f"stage2_two_pass={int(bool(STAGE2_EXACT_TWO_PASS))} "
        f"stage2_pass1_top_tails={STAGE2_EXACT_PASS1_TOP_TAILS} "
        f"stage2_pass1_top_by_c={json.dumps(STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS, separators=(',', ':'))} "
        f"stage2_early_solve_break={int(bool(STAGE2_EXACT_EARLY_SOLVE_BREAK))}",
        flush=True,
    )
    print(
        "[pipeline] setup: stage3_dynamic_bands="
        + json.dumps(
            [
                dict(
                    name=str(b.get("name", "")),
                    max_gap=float(b.get("max_gap", 0.0)),
                    steps=int(b.get("steps", 0)),
                    restarts=int(b.get("restarts", 0)),
                    plateau_rounds=int(b.get("plateau_rounds", 0)),
                    col_batch=int(b.get("col_batch", 0)),
                    inner_batch=int(b.get("inner_batch", 0)),
                )
                for b in STAGE3_DYNAMIC_BANDS
            ],
            separators=(",", ":"),
        ),
        flush=True,
    )
    print(f"[pipeline] setup: tiers={len(TIERS)} text_offsets={TEXT_OFFSETS} key_seeds={KEY_SEEDS}", flush=True)
    print(f"[pipeline] reports: {run_dir.relative_to(root)}", flush=True)

    stages: List[dict] = []
    instances: List[dict] = []
    total = len(TIERS) * len(TEXT_OFFSETS) * len(KEY_SEEDS)
    done = 0
    t0_all = time.time()
    last_hb = float(t0_all)
    best_global = {
        "match": float("-inf"),
        "tier": "",
        "text_id": -1,
        "key_seed": -1,
        "stage": "",
        "preview": "",
    }

    for tier in TIERS:
        for text_id, off in enumerate(TEXT_OFFSETS):
            pt_idx, wli, offset_used = base._slice_word_aligned(pt_base, wli_base, length=tier.length, offset_hint=int(off))
            for key_seed in KEY_SEEDS:
                t0_i = time.time()
                key_len = int(tier.period * ALPHABET_SIZE + tier.columns)
                rng = np.random.default_rng(int(key_seed))
                keyops = PeriodicStructuredMatrixKeyOps(K=key_len, period=tier.period, A=ALPHABET_SIZE, columns=tier.columns)
                key_true = keyops.random(rng).astype(np.int16, copy=False)

                cfg_full = CipherConfig(name="periodic_columnar", ciphertext=[], period=tier.period, columns=tier.columns, alphabet_size=ALPHABET_SIZE, key_length=key_len, order=ORDER, encoding_dir=direction, wli_data=[], device=Device.CPU)
                cfg_sub = CipherConfig(name="periodic_substitution", ciphertext=[], period=tier.period, alphabet_size=ALPHABET_SIZE, key_length=tier.period * ALPHABET_SIZE, encoding_dir=direction, wli_data=[], device=Device.CPU)
                full_cipher = PeriodicColumnarCipher(cfg_full)
                sub_cipher = PeriodicSubstitutionCipher(cfg_sub)
                ct_idx = full_cipher.encrypt_single(plaintext=pt_idx, key=key_true)
                sub_len = int(tier.period * ALPHABET_SIZE)
                true_sub = key_true[:sub_len].astype(np.int16, copy=False)
                pt_stage1_oracle = np.asarray(sub_cipher.decrypt_single(ciphertext=ct_idx, key=true_sub), dtype=np.uint8).reshape(-1)
                scorer_stage1 = dict(SCORER_STAGE1, encoding_dir=direction)
                scorer_full = dict(SCORER_FULL, encoding_dir=direction)
                print(
                    f"[pipeline] objective tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"stage1={scorer_stage1['objective']} "
                    f"stage23={scorer_full['objective']}",
                    flush=True,
                )
                scorer_full_runtime = build_scorer(cfg_full, ScoringConfig(**scorer_full))
                scorer_stage2_fast_runtime = None
                if int(tier.columns) <= int(STAGE2_EXACT_MAX_COLUMNS) and bool(STAGE2_EXACT_TWO_PASS):
                    scorer_stage2_fast = dict(
                        objective="pct.logp.win10",
                        include_char=True,
                        use_word_breaks=False,
                        char_weights=dict(STAGE2_FAST_CHAR_WEIGHTS),
                        wli_weights={},
                        encoding_dir=direction,
                    )
                    scorer_stage2_fast_runtime = build_scorer(cfg_full, ScoringConfig(**scorer_stage2_fast))
                oracle_s1, oracle_s1_raw, s1_obj = _oracle_score_for_stage(
                    pt_idx=pt_stage1_oracle,
                    wli=wli,
                    cipher_cfg=cfg_sub,
                    scorer_params=scorer_stage1,
                )
                oracle_s23, oracle_s23_raw, s23_obj = _oracle_score_for_stage(
                    pt_idx=pt_idx,
                    wli=wli,
                    cipher_cfg=cfg_full,
                    scorer_params=scorer_full,
                )
                print(
                    "[pipeline] oracle-score "
                    f"stage=stage1_sub model={s1_obj} "
                    f"(char={_weights_text(dict(SCORER_STAGE1.get('char_weights', {})))},"
                    f"wli={_weights_text(dict(SCORER_STAGE1.get('wli_weights', {})))},wb=0) "
                    f"score={oracle_s1:.6f} raw={oracle_s1_raw:.6f}",
                    flush=True,
                )
                print(
                    "[pipeline] oracle-score "
                    f"stage=stage2_3 model={s23_obj} "
                    f"(char={_weights_text(dict(SCORER_FULL.get('char_weights', {})))},"
                    f"wli={_weights_text(dict(SCORER_FULL.get('wli_weights', {})))},wb=1) "
                    f"score={oracle_s23:.6f} raw={oracle_s23_raw:.6f}",
                    flush=True,
                )
                if not np.array_equal(np.asarray(full_cipher.decrypt_single(ciphertext=ct_idx, key=key_true), dtype=np.uint8), np.asarray(pt_idx, dtype=np.uint8)):
                    raise RuntimeError(f"[pipeline] gate0 roundtrip failed tier={tier.name} text={text_id} key_seed={key_seed}")
                _print_stage_preview(label="oracle", pt=pt_idx.tolist(), wli=wli, scorer_wli=True, match_ratio=1.0)

                # Stage 1
                t_s1 = time.time()
                solver_stage1_cfg = dict(SOLVER_STAGE1)
                stage1_sub_limit = int(STAGE1_SUB_CANDIDATES_BY_COLUMNS.get(int(tier.columns), STAGE1_SUB_CANDIDATES))
                if STAGE1_USE_ORACLE_GUIDE_STOP:
                    s1_stop = min(0.999999, float(oracle_s1) + float(STAGE1_ORACLE_STOP_MARGIN))
                    solver_stage1_cfg["stop_score"] = float(s1_stop)
                print(
                    f"[pipeline] stage1-stop tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"stop_score={solver_stage1_cfg.get('stop_score', 'none')} "
                    f"plateau_rounds={solver_stage1_cfg.get('plateau_rounds')} "
                    f"plateau_min_delta={solver_stage1_cfg.get('plateau_min_delta')}",
                    flush=True,
                )
                s1_seeds = make_periodic_seed_pool(
                    ct_idx,
                    period=tier.period,
                    direction=direction.value,
                    seed=2026 + int(key_seed),
                    n_block_seeds=int(STAGE1_SEED_N_BLOCKS),
                    total_seeds=int(STAGE1_SEED_TOTAL),
                    swaps_per_block=int(STAGE1_SEED_SWAPS),
                    alphabet_size=ALPHABET_SIZE,
                )
                sol1 = run(text=ct_idx.tolist(), cipher=by_name.cipher("periodic_substitution", period=tier.period, alphabet_size=ALPHABET_SIZE), key=KeySpec.periodic_substitution(period=tier.period, alphabet_size=ALPHABET_SIZE), solver=SolverSpec.kaeding(**solver_stage1_cfg), scorer_params=scorer_stage1, wli_data=wli, encoding_dir=direction, telemetry_on=True, initial_keys=s1_seeds, force_no_wli=True)
                dt1 = float(time.time() - t_s1)
                ev1 = int((getattr(sol1, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
                sub_best = np.asarray(getattr(sol1, "key", []) or [], dtype=np.int16).reshape(-1)
                sub_key_match = base._match_ratio(sub_best.tolist(), true_sub.tolist())
                sub_candidates = _extract_top_keys(sol1, limit=stage1_sub_limit) or [sub_best.astype(int).tolist()]
                try:
                    pt1 = np.asarray(getattr(sol1, "plaintext_idx", []) or [], dtype=np.uint8).reshape(-1)
                    if pt1.size > 0:
                        m1 = base._match_ratio(pt1.tolist(), pt_idx.tolist())
                        _print_stage_preview(label="stage1_sub", pt=pt1.tolist(), wli=wli, scorer_wli=False, match_ratio=float(m1))
                except Exception:
                    pass
                stages.append(dict(tier=tier.name, text_id=int(text_id), key_seed=int(key_seed), stage="stage1_sub", score=float(getattr(sol1, "score", float("nan"))), sub_key_match=float(sub_key_match), seconds=round(dt1, 3), evals=ev1, candidates=len(sub_candidates)))
                print(
                    f"[pipeline] stage1-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"score={float(getattr(sol1, 'score', float('nan'))):.6f} sub_key_match={float(sub_key_match):.3f} "
                    f"evals={ev1} seconds={dt1:.1f} candidates={len(sub_candidates)}",
                    flush=True,
                )

                # Stage 2
                best2_match, best2_score, best2_key, best2_preview, best2_secs, best2_evals = float("-inf"), float("-inf"), None, "", 0.0, 0
                stage2_evals_total = 0
                exact_sub_limit = int(STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS.get(int(tier.columns), STAGE2_EXACT_SUB_CANDIDATES))
                pass1_top_tails = int(STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS.get(int(tier.columns), STAGE2_EXACT_PASS1_TOP_TAILS))
                if int(tier.columns) <= 1:
                    for i, sub_key in enumerate(sub_candidates):
                        sub_arr = np.asarray(sub_key, dtype=np.int16)
                        full_key = np.concatenate([sub_arr, np.asarray([0], dtype=np.int16)], axis=0)
                        pt2 = np.asarray(full_cipher.decrypt_single(ciphertext=ct_idx, key=full_key), dtype=np.uint8).reshape(-1)
                        m2 = base._match_ratio(pt2.tolist(), pt_idx.tolist())
                        sc2 = float(scorer_full_runtime.score(pt2, wli))
                        stage2_evals_total += 1
                        stages.append(
                            dict(
                                tier=tier.name,
                                text_id=int(text_id),
                                key_seed=int(key_seed),
                                stage=f"stage2_identity_attempt_{i+1}",
                                score=sc2,
                                match_ratio=float(m2),
                                seconds=0.0,
                                evals=0,
                            )
                        )
                        if (m2 > best2_match) or (abs(m2 - best2_match) <= 1e-12 and sc2 > best2_score):
                            best2_match, best2_score = float(m2), float(sc2)
                            best2_key = full_key.astype(int).tolist()
                            best2_preview = base._safe_preview_latin(pt2, wli)
                            best2_secs, best2_evals = 0.0, 0
                            _print_stage_preview(label=f"stage2_identity_best_{i+1}", pt=pt2.tolist(), wli=wli, scorer_wli=True, match_ratio=float(m2))
                elif int(tier.columns) <= int(STAGE2_EXACT_MAX_COLUMNS):
                    exact_subs = sub_candidates[: max(1, int(exact_sub_limit))]
                    exact_early_stop = False
                    for i, sub_key in enumerate(exact_subs):
                        sub_arr = np.asarray(sub_key, dtype=np.int16)
                        pass1_evals = 0
                        pass2_evals = 0
                        shortlist_tails: List[Tuple[int, ...]] = []

                        if bool(STAGE2_EXACT_TWO_PASS) and scorer_stage2_fast_runtime is not None:
                            pass1_ranked: List[Tuple[float, Tuple[int, ...]]] = []
                            for tail in permutations(range(int(tier.columns))):
                                col_key = np.asarray(tail, dtype=np.int16)
                                full_key = np.concatenate([sub_arr, col_key], axis=0)
                                pt2 = np.asarray(full_cipher.decrypt_single(ciphertext=ct_idx, key=full_key), dtype=np.uint8).reshape(-1)
                                fast_sc = float(scorer_stage2_fast_runtime.score(pt2, None))
                                pass1_ranked.append((fast_sc, tuple(int(x) for x in tail)))
                                pass1_evals += 1
                                stage2_evals_total += 1
                                if bool(STAGE2_EXACT_EARLY_SOLVE_BREAK):
                                    m2 = base._match_ratio(pt2.tolist(), pt_idx.tolist())
                                    if float(m2) >= float(SOLVE_MATCH_THRESHOLD):
                                        sc2 = float(scorer_full_runtime.score(pt2, wli))
                                        pass2_evals += 1
                                        stage2_evals_total += 1
                                        if (m2 > best2_match) or (abs(m2 - best2_match) <= 1e-12 and sc2 > best2_score):
                                            best2_match, best2_score = float(m2), float(sc2)
                                            best2_key = full_key.astype(int).tolist()
                                            best2_preview = base._safe_preview_latin(pt2, wli)
                                            best2_secs = 0.0
                                            best2_evals = int(stage2_evals_total)
                                            _print_stage_preview(label=f"stage2_exact_best_sub{i+1}", pt=pt2.tolist(), wli=wli, scorer_wli=True, match_ratio=float(m2))
                                        exact_early_stop = True
                                        break
                            if not exact_early_stop:
                                pass1_ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
                                k_short = min(int(pass1_top_tails), len(pass1_ranked))
                                shortlist_tails = [tail for _s, tail in pass1_ranked[:k_short]]
                        else:
                            shortlist_tails = [tuple(int(x) for x in tail) for tail in permutations(range(int(tier.columns)))]

                        if not exact_early_stop:
                            for tail in shortlist_tails:
                                col_key = np.asarray(tail, dtype=np.int16)
                                full_key = np.concatenate([sub_arr, col_key], axis=0)
                                pt2 = np.asarray(full_cipher.decrypt_single(ciphertext=ct_idx, key=full_key), dtype=np.uint8).reshape(-1)
                                m2 = base._match_ratio(pt2.tolist(), pt_idx.tolist())
                                sc2 = float(scorer_full_runtime.score(pt2, wli))
                                pass2_evals += 1
                                stage2_evals_total += 1
                                if (m2 > best2_match) or (abs(m2 - best2_match) <= 1e-12 and sc2 > best2_score):
                                    best2_match, best2_score = float(m2), float(sc2)
                                    best2_key = full_key.astype(int).tolist()
                                    best2_preview = base._safe_preview_latin(pt2, wli)
                                    best2_secs = 0.0
                                    best2_evals = int(stage2_evals_total)
                                    _print_stage_preview(label=f"stage2_exact_best_sub{i+1}", pt=pt2.tolist(), wli=wli, scorer_wli=True, match_ratio=float(m2))
                                if bool(STAGE2_EXACT_EARLY_SOLVE_BREAK) and float(m2) >= float(SOLVE_MATCH_THRESHOLD):
                                    exact_early_stop = True
                                    break
                        stages.append(
                            dict(
                                tier=tier.name,
                                text_id=int(text_id),
                                key_seed=int(key_seed),
                                stage=f"stage2_exact_attempt_{i+1}",
                                score=float(best2_score),
                                match_ratio=float(best2_match),
                                seconds=0.0,
                                evals=int(stage2_evals_total),
                                pass1_evals=int(pass1_evals),
                                pass2_evals=int(pass2_evals),
                                pass2_shortlist=int(len(shortlist_tails)),
                                pass1_top_cap=int(pass1_top_tails),
                                exact_sub_limit=int(exact_sub_limit),
                                early_stop=int(bool(exact_early_stop)),
                            )
                        )
                        if exact_early_stop:
                            break
                    print(
                        f"[pipeline] stage2-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"mode=exact best_match={float(best2_match):.3f} best_score={float(best2_score):.6f} "
                        f"evals={int(stage2_evals_total)}",
                        flush=True,
                    )
                else:
                    for i, sub_key in enumerate(sub_candidates):
                        t_s2 = time.time()
                        inter = sub_cipher.decrypt_single(ciphertext=ct_idx, key=np.asarray(sub_key, dtype=np.int16))
                        sol2 = run(text=np.asarray(inter, dtype=np.uint8).tolist(), cipher=by_name.cipher("columnar", key_length=tier.columns), key=KeySpec.permutation(len=tier.columns), solver=SolverSpec.hybrid(**dict(SOLVER_STAGE2)), scorer_params=scorer_full, wli_data=wli, encoding_dir=direction, telemetry_on=True, force_no_wli=False)
                        dt2 = float(time.time() - t_s2)
                        ev2 = int((getattr(sol2, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
                        stage2_evals_total += int(ev2)
                        col_key = np.asarray(getattr(sol2, "key", []) or [], dtype=np.int16).reshape(-1)
                        if col_key.size != int(tier.columns):
                            continue
                        full_key = np.concatenate([np.asarray(sub_key, dtype=np.int16), col_key], axis=0)
                        pt2 = np.asarray(full_cipher.decrypt_single(ciphertext=ct_idx, key=full_key), dtype=np.uint8).reshape(-1)
                        m2 = base._match_ratio(pt2.tolist(), pt_idx.tolist())
                        sc2 = float(getattr(sol2, "score", float("nan")))
                        stages.append(dict(tier=tier.name, text_id=int(text_id), key_seed=int(key_seed), stage=f"stage2_col_attempt_{i+1}", score=sc2, match_ratio=float(m2), seconds=round(dt2, 3), evals=ev2))
                        if (m2 > best2_match) or (abs(m2 - best2_match) <= 1e-12 and sc2 > best2_score):
                            best2_match, best2_score = float(m2), float(sc2)
                            best2_key = full_key.astype(int).tolist()
                            best2_preview = base._safe_preview_latin(pt2, wli)
                            best2_secs, best2_evals = float(dt2), int(ev2)
                            _print_stage_preview(label=f"stage2_best_attempt_{i+1}", pt=pt2.tolist(), wli=wli, scorer_wli=True, match_ratio=float(m2))
                    print(
                        f"[pipeline] stage2-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"mode=hybrid best_match={float(best2_match):.3f} best_score={float(best2_score):.6f} "
                        f"evals={int(stage2_evals_total)}",
                        flush=True,
                    )

                best_preview = str(best2_preview)

                # Stage 3
                best3_match, best3_score, stop_reason = float("nan"), float("nan"), "completed_pipeline"
                ev3 = 0
                stage2_gap_to_oracle = float("nan")
                stage3_band_name = ""
                if np.isfinite(best2_match) and best2_match >= SOLVE_MATCH_THRESHOLD:
                    stop_reason = "solved_stage2"
                elif best2_key is not None:
                    t_s3 = time.time()
                    init3_n = int(STAGE3_INITIAL_KEYS_BY_COLUMNS.get(int(tier.columns), STAGE3_INITIAL_KEYS))
                    init3 = _mutate_full_key(best2_key, period=tier.period, columns=tier.columns, seed=7000 + int(key_seed), n=init3_n)
                    solver_stage3_cfg = dict(SOLVER_STAGE3)
                    if np.isfinite(best2_score) and np.isfinite(oracle_s23):
                        stage2_gap_to_oracle = max(0.0, float(oracle_s23) - float(best2_score))
                    else:
                        stage2_gap_to_oracle = float("inf")
                    band = _select_stage3_band(stage2_gap_to_oracle)
                    stage3_band_name = str(band.get("name", ""))
                    solver_stage3_cfg.update(
                        steps=int(band.get("steps", solver_stage3_cfg.get("steps", 0))),
                        restarts=int(band.get("restarts", solver_stage3_cfg.get("restarts", 0))),
                        plateau_rounds=int(band.get("plateau_rounds", solver_stage3_cfg.get("plateau_rounds", 0))),
                        col_batch=int(band.get("col_batch", solver_stage3_cfg.get("col_batch", 0))),
                        inner_batch=int(band.get("inner_batch", solver_stage3_cfg.get("inner_batch", 0))),
                    )
                    if STAGE3_USE_ORACLE_GUIDE_STOP:
                        relax = max(0.0, min(0.95, float(STAGE3_ORACLE_STOP_RELAX_FRACTION)))
                        s3_stop = float(oracle_s23) - (abs(float(oracle_s23)) * relax) + float(STAGE3_ORACLE_STOP_MARGIN)
                        s3_stop = min(0.999999, float(s3_stop))
                        solver_stage3_cfg["stop_score"] = float(s3_stop)
                    print(
                        f"[pipeline] stage3-stop tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"band={stage3_band_name} "
                        f"gap_to_oracle={stage2_gap_to_oracle:.6f} "
                        f"oracle_relax={float(STAGE3_ORACLE_STOP_RELAX_FRACTION):.3f} "
                        f"init_keys={init3_n} "
                        f"steps={solver_stage3_cfg.get('steps')} restarts={solver_stage3_cfg.get('restarts')} "
                        f"col_batch={solver_stage3_cfg.get('col_batch')} inner_batch={solver_stage3_cfg.get('inner_batch')} "
                        f"stop_score={solver_stage3_cfg.get('stop_score', 'none')} "
                        f"plateau_rounds={solver_stage3_cfg.get('plateau_rounds')} "
                        f"plateau_min_delta={solver_stage3_cfg.get('plateau_min_delta')}",
                        flush=True,
                    )
                    sol3 = run(text=ct_idx.tolist(), cipher=by_name.cipher("periodic_columnar", period=tier.period, columns=tier.columns, order=ORDER, alphabet_size=ALPHABET_SIZE), key=KeySpec.periodic_columnar(period=tier.period, columns=tier.columns, alphabet_size=ALPHABET_SIZE), solver=SolverSpec.kaeding(**solver_stage3_cfg), scorer_params=scorer_full, wli_data=wli, encoding_dir=direction, telemetry_on=True, force_no_wli=False, initial_keys=init3)
                    dt3 = float(time.time() - t_s3)
                    ev3 = int((getattr(sol3, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
                    pt3 = np.asarray(getattr(sol3, "plaintext_idx", []) or [], dtype=np.uint8).reshape(-1)
                    best3_match = base._match_ratio(pt3.tolist(), pt_idx.tolist())
                    best3_score = float(getattr(sol3, "score", float("nan")))
                    stages.append(
                        dict(
                            tier=tier.name,
                            text_id=int(text_id),
                            key_seed=int(key_seed),
                            stage="stage3_full_refine",
                            score=best3_score,
                            match_ratio=float(best3_match),
                            seconds=round(dt3, 3),
                            evals=ev3,
                            stage3_band=stage3_band_name,
                            stage2_gap_to_oracle=float(stage2_gap_to_oracle),
                        )
                    )
                    if pt3.size > 0:
                        pt3_preview = _preview_latin(pt3.tolist(), wli)
                        _print_stage_preview(label="stage3_full_refine", pt=pt3.tolist(), wli=wli, scorer_wli=True, match_ratio=float(best3_match))
                        if (not np.isfinite(best2_match)) or (best3_match >= best2_match):
                            best_preview = str(pt3_preview)
                    if np.isfinite(best3_match) and best3_match >= SOLVE_MATCH_THRESHOLD:
                        stop_reason = "solved_stage3"
                    elif (best3_match - best2_match) <= STALL_DELTA:
                        stop_reason = "stalled_no_improve"
                    print(
                        f"[pipeline] stage3-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"band={stage3_band_name} match={float(best3_match):.3f} score={float(best3_score):.6f} "
                        f"evals={ev3} stop={stop_reason}",
                        flush=True,
                    )

                best_match = max(float(best2_match if np.isfinite(best2_match) else 0.0), float(best3_match if np.isfinite(best3_match) else 0.0))
                best_stage = "stage3_full_refine" if np.isfinite(best3_match) and best3_match >= best2_match else "stage2_search"
                status = "solved" if best_match >= SOLVE_MATCH_THRESHOLD else ("stalled" if stop_reason == "stalled_no_improve" else "unsolved")
                dt_i = float(time.time() - t0_i)
                total_evals = int(ev1 + int(stage2_evals_total) + int(ev3))
                instances.append(dict(
                    tier=tier.name, period=tier.period, columns=tier.columns, length=tier.length, text_id=int(text_id),
                    key_seed=int(key_seed), offset_hint=int(off), offset_used=int(offset_used), status=status, stop_reason=stop_reason,
                    solve_threshold=float(SOLVE_MATCH_THRESHOLD), best_stage=best_stage, best_match_ratio=float(best_match),
                    stage1_sub_key_match=float(sub_key_match), stage2_match_ratio=float(best2_match if np.isfinite(best2_match) else np.nan),
                    stage3_match_ratio=float(best3_match if np.isfinite(best3_match) else np.nan),
                    stage2_gap_to_oracle=float(stage2_gap_to_oracle),
                    stage3_band=str(stage3_band_name),
                    total_seconds=round(dt_i, 3), total_evals=total_evals, preview_best_latin=best_preview,
                ))

                if best_match > float(best_global["match"]):
                    best_global["match"] = float(best_match)
                    best_global["tier"] = str(tier.name)
                    best_global["text_id"] = int(text_id)
                    best_global["key_seed"] = int(key_seed)
                    best_global["stage"] = str(best_stage)
                    best_global["preview"] = str(best_preview)

                done += 1
                elapsed = time.time() - t0_all
                eta = (elapsed / float(done)) * float(total - done) if done else 0.0
                print(f"[pipeline] {done}/{total} tier={tier.name} status={status} best_match={best_match:.3f} run={base._format_seconds(dt_i)} elapsed={base._format_seconds(elapsed)} eta={base._format_seconds(eta)}", flush=True)
                if best_preview:
                    print(f"[pipeline] best-instance-preview tier={tier.name} text={text_id} key_seed={key_seed} text=\"{best_preview}\"", flush=True)
                now = time.time()
                if (now - last_hb) >= float(HEARTBEAT_SECONDS):
                    print(
                        f"[pipeline] heartbeat elapsed={base._format_seconds(now - t0_all)} "
                        f"done={done}/{total} "
                        f"global_best_match={float(best_global['match']):.3f} "
                        f"tier={best_global['tier']} text={best_global['text_id']} key_seed={best_global['key_seed']} "
                        f"stage={best_global['stage']} preview=\"{best_global['preview']}\"",
                        flush=True,
                    )
                    last_hb = now

    summary: Dict[str, Any] = {"tiers": {}}
    for t in TIERS:
        rs = [r for r in instances if r["tier"] == t.name]
        if not rs:
            continue
        arr = np.asarray([float(r["best_match_ratio"]) for r in rs], dtype=np.float64)
        summary["tiers"][t.name] = dict(n=len(rs), solved_rate=float(np.mean(arr >= SOLVE_MATCH_THRESHOLD)), best_match_p50=float(np.percentile(arr, 50)), best_match_p90=float(np.percentile(arr, 90)))

    (run_dir / "instances.json").write_text(json.dumps(instances, indent=2), encoding="utf-8")
    (run_dir / "stages.json").write_text(json.dumps(stages, indent=2), encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_csv_rows(run_dir / "instances.csv", instances)
    _write_csv_rows(run_dir / "stages.csv", stages)

    hist = root / "tools" / "benchmarks" / "solve_proof" / "proven_solve_pipeline_log.csv"
    hist.parent.mkdir(parents=True, exist_ok=True)
    hist_rows = []
    now = datetime.now(timezone.utc).isoformat()
    for r in instances:
        hist_rows.append(dict(timestamp_utc=now, run_id=run_dir.name, profile_id=PROFILE, fixture_id=r["tier"], text_id=r["text_id"], key_seed=r["key_seed"], period=r["period"], columns=r["columns"], length=r["length"], status=r["status"], solve_threshold=r["solve_threshold"], best_match_ratio=r["best_match_ratio"], best_stage=r["best_stage"], stage1_sub_key_match=r["stage1_sub_key_match"], stage2_match_ratio=r["stage2_match_ratio"], stage3_match_ratio=r["stage3_match_ratio"], total_seconds=r["total_seconds"], total_evals=r["total_evals"], notes=r["stop_reason"]))
    cols = list(hist_rows[0].keys()) if hist_rows else []
    write_header = (not hist.exists()) or hist.stat().st_size == 0
    if hist_rows:
        with hist.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            if write_header:
                w.writeheader()
            w.writerows(hist_rows)

    print(f"[pipeline] completed in {base._format_seconds(time.time() - t0_all)}", flush=True)
    print(f"[pipeline] reports: {run_dir.relative_to(root)}", flush=True)
    print(f"[pipeline] history: {hist.relative_to(root)} rows={len(hist_rows)}", flush=True)


if __name__ == "__main__":
    main()
