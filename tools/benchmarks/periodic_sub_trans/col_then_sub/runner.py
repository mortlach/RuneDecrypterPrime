from __future__ import annotations

"""
Practical staged solve benchmark (no cribs) for periodic-columnar (col_then_sub).

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



This variant exists to keep *separate* solve-proof history and solved JSONL logs for the col_then_sub order.
It is functionally identical to bench_solve_periodic_columnar_pipeline.py, but writes to:
- tools/benchmarks/solve_proof/proven_solve_pipeline_col_then_sub_log.csv
- tools/benchmarks/solve_proof/proven_solve_pipeline_col_then_sub_solved.jsonl

Run controls (hardcoded at top of this file):
- FORCE_RERUN_PROVEN
- KEY_SEEDS_OVERRIDE
- TIERS_REGEX_OVERRIDE
- AVOID_REPEAT_FAIL
- FAILED_RETRY_SEED_DELTA
"""

import csv
import hashlib
import json
import re
import subprocess
import sys
import time
from itertools import permutations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np

_ROOT = Path(__file__).resolve().parents[4]
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
from rune_decrypter_prime.core.types import Device, ScorerImpl
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps
from tools.benchmarks.periodic_sub_trans.common.seed_utils_periodic_columnar_col_then_sub import (
    make_periodic_seed_pool_col_then_sub,
    make_tail_seed_pool,
)
from tools.benchmarks.periodic_sub_trans.common.core_enums import BenchmarkOrder
from tools.benchmarks.periodic_sub_trans.common.batch_eval import (
    decrypt_and_score_keys_chunked,
    score_plaintexts_chunked,
)

from tools.benchmarks.periodic_sub_trans.common import bench_solve_periodic_columnar_kaeding as base
from tools.benchmarks.periodic_sub_trans.common.io_reports import (
    append_csv_row as _append_csv_row_common,
    write_json,
    write_pipeline_snapshot_files,
)
from tools.benchmarks.periodic_sub_trans.common.paths import make_flavor_run_dir
from tools.benchmarks.periodic_sub_trans.common.runner_types import Tier

ALPHABET_SIZE = 29  # Rune alphabet size used by periodic substitution/key layout.
ORDER = BenchmarkOrder.COL_THEN_SUB.value  # Cipher composition order benchmarked by this script.
PROFILE = "pipeline_col_then_sub_v1"  # Human-readable profile id written to logs/history.
PIPELINE_RUN_MODE = "focus_p10_fast_resume"  # Active preset selector.
# Allowed: "full" | "focus_p5_p7" | "focus_p10_fast" | "focus_p10_fast_resume" | "smoke"
SCORER_IMPL = ScorerImpl.TORCH.value  # Use true batch scorer path for performance-focused benchmark runs.
BATCH_EVAL_CHUNK_SIZE = 256  # Shared chunk size for decrypt+score batching in runner-level loops.
REQUIRE_BATCH_SCORING = True  # Fail fast if scorer can't execute true batch path in perf profiles.

SOLVE_MATCH_THRESHOLD = 0.90  # Match ratio considered solved.
STALL_DELTA = 0.002  # Minimum global-best gain required to avoid "stalled" status.
STALL_STAGE_LIMIT = 1  # Number of consecutive stalled stages before instance is stalled.
HEARTBEAT_SECONDS = 1200  # Progress heartbeat cadence.
PREVIEW_CHARS = 240  # Preview snippet length for plaintext logging.
AUTOSKIP_PROVEN = True  # Skip instances already proven in solve-proof history.
AUTOSKIP_PROVEN_MIN_MATCH = SOLVE_MATCH_THRESHOLD  # Proven threshold for autoskip index.
FORCE_RERUN_PROVEN = True  # Override autoskip and rerun proven instances.
AVOID_REPEAT_FAIL = True  # Diversify search seed if same config failed previously.
FAILED_RETRY_SEED_DELTA = 1  # Per-failure increment applied to search-seed offset.
FAILED_RETRY_SEED_STRIDE = 104729  # Large stride multiplier to decorrelate retry seeds.

TEXT_OFFSETS = [0]  # Plaintext slice offset hints for fixture generation.
KEY_SEEDS = [111]  # Baseline synthetic key seeds for this run mode.
# Community defaults: run the full profile-defined matrix unless explicitly narrowed.
KEY_SEEDS_OVERRIDE: List[int] | None = [111, 211, 311]  # Optional hard override for key-seed list.
TIERS_REGEX_OVERRIDE: str | None = r"^focus_p10_c10_l2376$"  # Narrow run to p10/c10 compare.
TIERS_PERIOD_SWEEP: str = "p10_only"  # "none" | "p10_only" | "p13_only" (flip to p13_only for the next sweep)
TIERS_MIN_COLUMNS: int | None = None  # Keep only tiers with columns >= this value (None disables).
STAGE1_SUB_CANDIDATES = 16  # Default Stage-1 substitution candidates kept.
STAGE3_INITIAL_KEYS = 24  # Default Stage-3 init key count (mutated from Stage-2).
STAGE1_SUB_CANDIDATES_BY_COLUMNS = {1: 6, 3: 10, 5: 12, 7: 14}  # Stage-1 keep count by columns.
STAGE3_INITIAL_KEYS_BY_COLUMNS = {1: 8, 3: 12, 5: 16, 7: 20}  # Stage-3 init count by columns.
STAGE2_EXACT_MAX_COLUMNS = 7  # Use exact tail enumeration when columns <= this value.
STAGE2_EXACT_SUB_CANDIDATES = 2  # Default Stage-1 sub candidates sent to exact Stage-2.
STAGE2_EXACT_TWO_PASS = True  # Enable exact-tail pass1 rank + pass2 deep eval.
STAGE2_EXACT_PASS1_TOP_TAILS = 256  # Default pass1 shortlist size for exact Stage-2.
STAGE2_EXACT_EARLY_SOLVE_BREAK = True  # Break exact search immediately on solved match.
STAGE2_FAST_CHAR_WEIGHTS = {3: 0.2, 4: 0.8}  # Fast pass1 char scorer weights.
STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS = {3: 4, 5: 3, 7: 2}  # Exact Stage-2 sub count by columns.
STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS = {3: 72, 5: 128, 7: 192}  # Exact pass1 shortlist by columns.
STAGE2_HYBRID_SUB_CANDIDATES = 12  # Default sub candidates sent to hybrid Stage-2.
STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS = {10: 12, 13: 12}  # Hybrid Stage-2 sub cap by columns.
STAGE2_TAIL_SEEDS_TOTAL = 256  # Default tail seed pool size for Stage-2 hybrid.
STAGE2_TAIL_SEEDS_TOTAL_BY_COLUMNS = {10: 1024, 13: 2048}  # Wider tail pool for hard columns.
STAGE2_TAIL_STRUCTURED_SWAPS = 96  # Default structured tail swaps.
STAGE2_TAIL_STRUCTURED_SWAPS_BY_COLUMNS = {10: 160, 13: 224}  # More structured diversity on hard columns.
STAGE2_TAIL_RANDOM_FRACTION = 0.50  # Random tail-share of total seeds.
STAGE1_USE_ORACLE_GUIDE_STOP = True  # Enable Stage-1 oracle-guided stop score.
STAGE1_ORACLE_STOP_MARGIN = 0.005  # Margin added to Stage-1 oracle stop score.
STAGE3_USE_ORACLE_GUIDE_STOP = False  # Enable Stage-3 oracle-guided stop score.
STAGE3_ORACLE_STOP_MARGIN = 0.002  # Margin added to Stage-3 oracle stop score.
STAGE3_ORACLE_STOP_RELAX_FRACTION = 0.0  # Relaxation of oracle stop score (fraction of |oracle|).
STAGE3_FULL_ENTRY_SCORE: float | None = None  # Full Stage-3 budget gate (None disables).
STAGE3_FULL_ENTRY_SCORE_BY_COLUMNS: Dict[int, float] = {}  # Per-column overrides for full gate.
STAGE3_PROBE_ENTRY_SCORE: float | None = None  # Probe/medium Stage-3 gate (None disables).
STAGE3_PROBE_ENTRY_SCORE_BY_COLUMNS: Dict[int, float] = {}  # Per-column overrides for probe gate.
STAGE1_SEED_RESTARTS = 64  # Seed-pool restarts used to generate Stage-1 starts.
STAGE1_SEED_N_BLOCKS = 18  # Number of periodic blocks sampled per seed-pool generation.
STAGE1_SEED_TOTAL = 256  # Total seed-pool size for Stage-1.
STAGE1_SEED_SWAPS = 3  # Swap depth when mutating Stage-1 seed-pool keys.
STAGE1_SEED_GLOBAL_SHRINK_DEFAULT = 0.0  # Default phase histogram shrinkage.
STAGE1_SEED_GLOBAL_SHRINK_BY_PERIOD = {13: 0.30}  # Stabilise p13 stage-1 seeding.
STAGE1_SEED_PHASE_LEN_TARGET_DEFAULT = 160  # Default effective per-phase target length.
STAGE1_SEED_PHASE_LEN_TARGET_BY_PERIOD = {13: 192}  # p13-specific phase target.
STAGE1_SEED_RESTART_MULT_BY_PERIOD = {13: 1.50}  # p13-only scout restart multiplier.
STAGE12_SCOUT_RUNS = 1  # Number of Stage-1 scout searches before archive selection.
STAGE12_ARCHIVE_KEEP = 1  # Archive size retained from Stage-1/2 candidate pool.
STAGE12_PROMOTE_TOP = 1  # Number of archived candidates promoted to Stage-3.
STAGE1_SCOUT_STEP_SCALE = 1.0  # Multiplicative reduction for scout steps after scout 1.
STAGE1_SCOUT_RESTART_SCALE = 1.0  # Multiplicative reduction for scout restarts after scout 1.
STAGE1_SCOUT_MIN_STEPS = 600  # Lower bound for scout steps after scaling.
STAGE1_SCOUT_MIN_RESTARTS = 1  # Lower bound for scout restarts after scaling.
STAGE1_SCOUT_NO_IMPROVE_DELTA = 1e-6  # Scout score-gain threshold for plateau detection.
STAGE1_SCOUT_NO_IMPROVE_PATIENCE = 2  # Consecutive plateau scouts before early stop.
STAGE1_SCOUT_MIN_NEW_ARCHIVE = 2  # Minimum new archived keys required to avoid plateau stop.
STAGE1_C1_MAX_SCOUTS = 2  # Extra guard: max scout runs when columns==1.
STAGE1_C1_FORCE_ORACLE_STOP = True  # Force oracle stop-score for columns==1.
STAGE1_C1_ORACLE_STOP_MARGIN = 0.0  # Additional margin for c1 oracle stop.
STAGE1_C1_EARLY_BREAK_ON_SOLVED_MATCH = True  # Break Stage-1 c1 if solved match appears.
STAGE3_HARD_COLUMNS = {10, 13}  # Columns considered hard for far-band override.
STAGE3_HARD_FAR_OVERRIDE = dict(steps=7200, restarts=3, plateau_rounds=520, col_batch=192)

# Stage-3 dynamic budget based on stage2 objective gap to oracle objective (same scorer).
# Lower gap => lighter stage3; higher gap => heavier stage3.
STAGE3_DYNAMIC_BANDS = [
    dict(name="very_close", max_gap=0.010, steps=1800, restarts=1, plateau_rounds=220, col_batch=96, inner_batch=128),
    dict(name="close", max_gap=0.030, steps=3200, restarts=1, plateau_rounds=320, col_batch=112, inner_batch=128),
    dict(name="mid", max_gap=0.080, steps=4800, restarts=2, plateau_rounds=420, col_batch=128, inner_batch=128),
    dict(name="far", max_gap=1e9, steps=7200, restarts=2, plateau_rounds=560, col_batch=128, inner_batch=128),
]

SCORER_STAGE1 = dict(
    objective="pct.logp.win10",
    include_char=True,
    use_word_breaks=False,
    char_weights={1: 1.0},
    wli_weights={},
    impl=SCORER_IMPL,
)
SCORER_STAGE1_HARD_RERANK = dict(
    objective="pct.logp.win10",
    include_char=True,
    use_word_breaks=False,
    char_weights={3: 0.2, 4: 0.8},
    wli_weights={},
    impl=SCORER_IMPL,
)
SCORER_FULL = dict(
    objective="pct.logp.win10",
    include_char=False,
    use_word_breaks=True,
    char_weights={},
    wli_weights={2: 0.3, 4: 0.7},
    impl=SCORER_IMPL,
)
STAGE1_C1_USE_FULL_SCORER = False
STAGE1_HARD_RERANK_ENABLED = True  # Re-rank stage1 archive with char34 (no WLI) on hard columns.
STAGE1_HARD_RERANK_COLUMNS = {10, 13}  # Columns where stage1 hard rerank is applied.

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
    global STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS, STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS
    global STAGE2_HYBRID_SUB_CANDIDATES, STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS
    global STAGE1_SEED_N_BLOCKS, STAGE1_SEED_TOTAL, STAGE1_SEED_SWAPS
    global STAGE1_SUB_CANDIDATES_BY_COLUMNS, STAGE3_INITIAL_KEYS_BY_COLUMNS, STAGE3_DYNAMIC_BANDS
    global STAGE1_USE_ORACLE_GUIDE_STOP, STAGE3_USE_ORACLE_GUIDE_STOP, STAGE3_ORACLE_STOP_MARGIN, STAGE3_ORACLE_STOP_RELAX_FRACTION
    global STAGE3_FULL_ENTRY_SCORE, STAGE3_FULL_ENTRY_SCORE_BY_COLUMNS, STAGE3_PROBE_ENTRY_SCORE, STAGE3_PROBE_ENTRY_SCORE_BY_COLUMNS
    global STAGE1_C1_USE_FULL_SCORER
    global STAGE12_SCOUT_RUNS, STAGE12_ARCHIVE_KEEP, STAGE12_PROMOTE_TOP
    global STAGE1_SCOUT_STEP_SCALE, STAGE1_SCOUT_RESTART_SCALE, STAGE1_SCOUT_MIN_STEPS, STAGE1_SCOUT_MIN_RESTARTS
    global STAGE1_SCOUT_NO_IMPROVE_DELTA, STAGE1_SCOUT_NO_IMPROVE_PATIENCE, STAGE1_SCOUT_MIN_NEW_ARCHIVE
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
        KEY_SEEDS = [111, 211, 311]
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
        STAGE3_FULL_ENTRY_SCORE = None
        STAGE3_FULL_ENTRY_SCORE_BY_COLUMNS = {}
        STAGE3_PROBE_ENTRY_SCORE = None
        STAGE3_PROBE_ENTRY_SCORE_BY_COLUMNS = {}
        STAGE12_SCOUT_RUNS = 2
        STAGE12_ARCHIVE_KEEP = 6
        STAGE12_PROMOTE_TOP = 3
        STAGE1_SCOUT_STEP_SCALE = 0.55
        STAGE1_SCOUT_RESTART_SCALE = 0.70
        STAGE1_SCOUT_MIN_STEPS = 900
        STAGE1_SCOUT_MIN_RESTARTS = 1
        STAGE1_SCOUT_NO_IMPROVE_DELTA = 1e-6
        STAGE1_SCOUT_NO_IMPROVE_PATIENCE = 2
        STAGE1_SCOUT_MIN_NEW_ARCHIVE = 2

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

        STAGE1_SUB_CANDIDATES = 20
        STAGE1_SUB_CANDIDATES_BY_COLUMNS = {1: 8, 3: 12, 5: 14, 7: 16, 10: 16}
        STAGE3_INITIAL_KEYS = 14
        STAGE3_INITIAL_KEYS_BY_COLUMNS = {1: 8, 3: 18, 5: 24, 7: 28, 10: 32}

        STAGE2_EXACT_SUB_CANDIDATES = 3
        STAGE2_EXACT_PASS1_TOP_TAILS = 160
        STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS = {3: 12, 5: 8, 7: 3}
        STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS = {3: 6, 5: 120, 7: 192}
        STAGE2_EXACT_TWO_PASS = True
        STAGE2_EXACT_EARLY_SOLVE_BREAK = True
        STAGE1_SEED_RESTARTS = 128
        STAGE1_SEED_N_BLOCKS = 20
        STAGE1_SEED_TOTAL = 320
        STAGE1_SEED_SWAPS = 3

        STAGE3_DYNAMIC_BANDS = [
            dict(name="very_close", max_gap=0.010, steps=900, restarts=1, plateau_rounds=140, col_batch=96, inner_batch=128),
            dict(name="close", max_gap=0.030, steps=1600, restarts=1, plateau_rounds=200, col_batch=96, inner_batch=128),
            dict(name="mid", max_gap=0.080, steps=2400, restarts=2, plateau_rounds=260, col_batch=112, inner_batch=128),
            dict(name="far", max_gap=1e9, steps=3200, restarts=2, plateau_rounds=320, col_batch=112, inner_batch=128),
        ]
        # For p10, stage1 objective can over-rate wrong basins; disable oracle-guided stop there.
        STAGE1_USE_ORACLE_GUIDE_STOP = False
        STAGE3_USE_ORACLE_GUIDE_STOP = True
        STAGE3_ORACLE_STOP_MARGIN = 0.0
        STAGE3_ORACLE_STOP_RELAX_FRACTION = 0.10
        STAGE3_FULL_ENTRY_SCORE = 0.10
        STAGE3_FULL_ENTRY_SCORE_BY_COLUMNS = {3: 0.10, 5: 0.10, 7: 0.10, 10: 0.10}
        STAGE3_PROBE_ENTRY_SCORE = 0.06
        STAGE3_PROBE_ENTRY_SCORE_BY_COLUMNS = {3: 0.06, 5: 0.06, 7: 0.06, 10: 0.06}
        STAGE1_C1_USE_FULL_SCORER = True
        STAGE12_SCOUT_RUNS = 6
        STAGE12_ARCHIVE_KEEP = 16
        STAGE12_PROMOTE_TOP = 6
        STAGE1_SCOUT_STEP_SCALE = 0.45
        STAGE1_SCOUT_RESTART_SCALE = 0.67
        STAGE1_SCOUT_MIN_STEPS = 900
        STAGE1_SCOUT_MIN_RESTARTS = 1
        STAGE1_SCOUT_NO_IMPROVE_DELTA = 1e-6
        STAGE1_SCOUT_NO_IMPROVE_PATIENCE = 2
        STAGE1_SCOUT_MIN_NEW_ARCHIVE = 2

        SOLVER_STAGE1.update(
            steps=3400,
            restarts=3,
            inner_batch=128,
            top_k=28,
            seed_restarts=128,
            plateau_rounds=420,
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
            steps=3200,
            restarts=2,
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
    if PIPELINE_RUN_MODE == "focus_p10_fast_resume":
        PROFILE = "pipeline_focus_p10_p13_hard_basin_v2"
        HEARTBEAT_SECONDS = 900
        TIERS = [
            Tier("focus_p10_c1_l2376", 10, 1, 2376),
            Tier("focus_p10_c3_l2376", 10, 3, 2376),
            Tier("focus_p10_c5_l2376", 10, 5, 2376),
            Tier("focus_p10_c7_l2376", 10, 7, 2376),
            Tier("focus_p10_c10_l2376", 10, 10, 2376),
            Tier("focus_p10_c13_l2376", 10, 13, 2376),
            Tier("focus_p13_c1_l2376", 13, 1, 2376),
            Tier("focus_p13_c3_l2376", 13, 3, 2376),
            Tier("focus_p13_c5_l2376", 13, 5, 2376),
            Tier("focus_p13_c7_l2376", 13, 7, 2376),
            Tier("focus_p13_c10_l2376", 13, 10, 2376),
            Tier("focus_p13_c13_l2376", 13, 13, 2376),
        ]
        TEXT_OFFSETS = [0]
        KEY_SEEDS = [111]

        STAGE1_SUB_CANDIDATES = 24
        STAGE1_SUB_CANDIDATES_BY_COLUMNS = {1: 8, 3: 32, 5: 24, 7: 24, 10: 32, 13: 32}
        STAGE3_INITIAL_KEYS = 18
        STAGE3_INITIAL_KEYS_BY_COLUMNS = {1: 8, 3: 36, 5: 30, 7: 40, 10: 40, 13: 48}

        STAGE2_EXACT_SUB_CANDIDATES = 4
        STAGE2_EXACT_PASS1_TOP_TAILS = 160
        # c7 remains the hardest p10 basin: widen exact-stage coverage there.
        STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS = {3: 24, 5: 12, 7: 12}
        STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS = {3: 6, 5: 120, 7: 768}
        STAGE2_HYBRID_SUB_CANDIDATES = 12
        STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS = {10: 12, 13: 12}
        STAGE2_EXACT_TWO_PASS = True
        STAGE2_EXACT_EARLY_SOLVE_BREAK = True
        STAGE1_SEED_RESTARTS = 128
        STAGE1_SEED_N_BLOCKS = 20
        STAGE1_SEED_TOTAL = 320
        STAGE1_SEED_SWAPS = 3

        STAGE3_DYNAMIC_BANDS = [
            dict(name="very_close", max_gap=0.010, steps=900, restarts=1, plateau_rounds=140, col_batch=96, inner_batch=128),
            dict(name="close", max_gap=0.030, steps=1600, restarts=1, plateau_rounds=200, col_batch=96, inner_batch=128),
            dict(name="mid", max_gap=0.080, steps=2400, restarts=2, plateau_rounds=260, col_batch=112, inner_batch=128),
            dict(name="far", max_gap=1e9, steps=3200, restarts=2, plateau_rounds=320, col_batch=112, inner_batch=128),
        ]
        STAGE1_USE_ORACLE_GUIDE_STOP = False
        STAGE3_USE_ORACLE_GUIDE_STOP = True
        STAGE3_ORACLE_STOP_MARGIN = 0.0
        STAGE3_ORACLE_STOP_RELAX_FRACTION = 0.10
        # Hard-basin profile: always run full Stage-3 band budget (no probe gate).
        STAGE3_FULL_ENTRY_SCORE = None
        STAGE3_FULL_ENTRY_SCORE_BY_COLUMNS = {}
        STAGE3_PROBE_ENTRY_SCORE = None
        STAGE3_PROBE_ENTRY_SCORE_BY_COLUMNS = {}
        STAGE1_C1_USE_FULL_SCORER = True
        STAGE12_SCOUT_RUNS = 6
        STAGE12_ARCHIVE_KEEP = 48
        STAGE12_PROMOTE_TOP = 24
        STAGE1_SCOUT_STEP_SCALE = 0.28
        STAGE1_SCOUT_RESTART_SCALE = 0.25
        STAGE1_SCOUT_MIN_STEPS = 900
        STAGE1_SCOUT_MIN_RESTARTS = 1
        STAGE1_SCOUT_NO_IMPROVE_DELTA = 1e-6
        STAGE1_SCOUT_NO_IMPROVE_PATIENCE = 1
        STAGE1_SCOUT_MIN_NEW_ARCHIVE = 4

        SOLVER_STAGE1.update(
            steps=2600,
            restarts=2,
            inner_batch=128,
            top_k=28,
            seed_restarts=96,
            plateau_rounds=420,
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
            steps=3200,
            restarts=2,
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
        STAGE3_FULL_ENTRY_SCORE = None
        STAGE3_FULL_ENTRY_SCORE_BY_COLUMNS = {}
        STAGE3_PROBE_ENTRY_SCORE = None
        STAGE3_PROBE_ENTRY_SCORE_BY_COLUMNS = {}
        STAGE12_SCOUT_RUNS = 1
        STAGE12_ARCHIVE_KEEP = 1
        STAGE12_PROMOTE_TOP = 1
        STAGE1_SCOUT_STEP_SCALE = 1.0
        STAGE1_SCOUT_RESTART_SCALE = 1.0
        STAGE1_SCOUT_MIN_STEPS = 60
        STAGE1_SCOUT_MIN_RESTARTS = 1
        STAGE1_SCOUT_NO_IMPROVE_DELTA = 1e-6
        STAGE1_SCOUT_NO_IMPROVE_PATIENCE = 1
        STAGE1_SCOUT_MIN_NEW_ARCHIVE = 0

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
        "expected 'full', 'focus_p5_p7', 'focus_p10_fast', 'focus_p10_fast_resume', or 'smoke'"
    )


def _apply_runtime_overrides() -> None:
    global KEY_SEEDS, TIERS
    if KEY_SEEDS_OVERRIDE is not None:
        vals = [int(x) for x in KEY_SEEDS_OVERRIDE]
        if vals:
            seen: set[int] = set()
            KEY_SEEDS = [int(x) for x in vals if not (int(x) in seen or seen.add(int(x)))]
    if TIERS_REGEX_OVERRIDE:
        rx = re.compile(str(TIERS_REGEX_OVERRIDE))
        TIERS = [t for t in TIERS if rx.search(str(t.name))]
        if not TIERS:
            raise ValueError(
                f"TIERS_REGEX_OVERRIDE={TIERS_REGEX_OVERRIDE!r} matched zero tiers"
            )
    sweep = str(TIERS_PERIOD_SWEEP).strip().lower()
    if sweep not in {"none", "p10_only", "p13_only"}:
        raise ValueError(
            f"TIERS_PERIOD_SWEEP={TIERS_PERIOD_SWEEP!r} must be one of: none, p10_only, p13_only"
        )
    if sweep == "p10_only":
        TIERS = [t for t in TIERS if int(t.period) == 10]
    elif sweep == "p13_only":
        TIERS = [t for t in TIERS if int(t.period) == 13]
    if TIERS_MIN_COLUMNS is not None:
        cmin = int(TIERS_MIN_COLUMNS)
        TIERS = [t for t in TIERS if int(t.columns) >= cmin]
    if not TIERS:
        raise ValueError(
            "Tier selection is empty after overrides; adjust TIERS_REGEX_OVERRIDE / "
            "TIERS_PERIOD_SWEEP / TIERS_MIN_COLUMNS"
        )


def _apply_scorer_impl_override(impl: str) -> None:
    """Keep scorer impl wiring consistent across this runner's scorer dicts."""
    global SCORER_IMPL
    resolved = str(impl).strip()
    if not resolved:
        return
    SCORER_IMPL = resolved
    for cfg in (SCORER_STAGE1, SCORER_STAGE1_HARD_RERANK, SCORER_FULL):
        if isinstance(cfg, dict):
            cfg["impl"] = resolved


def configure_campaign_run(
    *,
    run_seed: int,
    period: int,
    columns: int,
    length: int,
    tier_name: str,
    run_mode: str,
    profile_name: str,
    heartbeat_seconds: int,
    autoskip_proven: bool,
    force_rerun_proven: bool,
    avoid_repeat_fail: bool,
    text_offsets: Sequence[int],
    tiers_regex_override: str | None,
    scorer_impl: str | None = None,
    scorer_stage3_impl_avg_fulltext: str | None = None,  # kept for cross-runner signature parity
) -> None:
    """Apply campaign job settings through one explicit runner entrypoint."""

    del scorer_stage3_impl_avg_fulltext

    global AUTOSKIP_PROVEN, FORCE_RERUN_PROVEN, AVOID_REPEAT_FAIL
    global TIERS_REGEX_OVERRIDE, TIERS_PERIOD_SWEEP, TIERS_MIN_COLUMNS
    global KEY_SEEDS_OVERRIDE, KEY_SEEDS, TEXT_OFFSETS
    global PIPELINE_RUN_MODE, PROFILE, HEARTBEAT_SECONDS, TIERS

    AUTOSKIP_PROVEN = bool(autoskip_proven)
    FORCE_RERUN_PROVEN = bool(force_rerun_proven)
    AVOID_REPEAT_FAIL = bool(avoid_repeat_fail)
    TIERS_REGEX_OVERRIDE = (
        None
        if tiers_regex_override is None or str(tiers_regex_override).strip() == ""
        else str(tiers_regex_override)
    )
    # Campaign jobs pin one explicit (period, columns, length) tier.
    # Disable local sweep/min-column filters so non-p10 cells are not dropped.
    TIERS_PERIOD_SWEEP = "none"
    TIERS_MIN_COLUMNS = None
    KEY_SEEDS_OVERRIDE = [int(run_seed)]
    KEY_SEEDS = [int(run_seed)]
    TEXT_OFFSETS = [int(x) for x in text_offsets]
    PIPELINE_RUN_MODE = str(run_mode)
    PROFILE = str(profile_name)
    HEARTBEAT_SECONDS = int(heartbeat_seconds)
    TIERS = [Tier(str(tier_name), int(period), int(columns), int(length))]

    if scorer_impl is not None:
        _apply_scorer_impl_override(str(scorer_impl))


def _repo_root() -> Path:
    return _ROOT


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
        f"[colsub] preview {label} scorer_wli={'on' if scorer_wli else 'off'} "
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


def _chunk_sequence(seq: Sequence[Any], chunk_size: int) -> Iterable[Sequence[Any]]:
    chunk = max(1, int(chunk_size))
    for lo in range(0, len(seq), chunk):
        yield seq[lo : lo + chunk]


def _select_stage3_band(gap_to_oracle: float) -> Dict[str, Any]:
    gap = float(gap_to_oracle)
    for band in STAGE3_DYNAMIC_BANDS:
        if gap <= float(band.get("max_gap", 1e9)):
            return dict(band)
    return dict(STAGE3_DYNAMIC_BANDS[-1])


def _stage3_full_entry_score(columns: int) -> float | None:
    c = int(columns)
    if c in STAGE3_FULL_ENTRY_SCORE_BY_COLUMNS:
        return float(STAGE3_FULL_ENTRY_SCORE_BY_COLUMNS[c])
    if STAGE3_FULL_ENTRY_SCORE is None:
        return None
    return float(STAGE3_FULL_ENTRY_SCORE)


def _stage3_probe_entry_score(columns: int) -> float | None:
    c = int(columns)
    if c in STAGE3_PROBE_ENTRY_SCORE_BY_COLUMNS:
        return float(STAGE3_PROBE_ENTRY_SCORE_BY_COLUMNS[c])
    if STAGE3_PROBE_ENTRY_SCORE is None:
        return None
    return float(STAGE3_PROBE_ENTRY_SCORE)


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


def _to_int_list(values: Sequence[int] | np.ndarray) -> List[int]:
    return [int(x) for x in values]


def _build_summary(tiers: Sequence[Tier], instances: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {"tiers": {}}
    for t in tiers:
        rs = [r for r in instances if r["tier"] == t.name]
        if not rs:
            continue
        arr = np.asarray([float(r["best_match_ratio"]) for r in rs], dtype=np.float64)
        summary["tiers"][t.name] = dict(
            n=len(rs),
            solved_rate=float(np.mean(arr >= SOLVE_MATCH_THRESHOLD)),
            best_match_p50=float(np.percentile(arr, 50)),
            best_match_p90=float(np.percentile(arr, 90)),
        )
    return summary


def _load_proven_solved_index(path: Path, *, min_match: float) -> Dict[Tuple[str, int, int], Dict[str, Any]]:
    out: Dict[Tuple[str, int, int], Dict[str, Any]] = {}
    if not path.exists():
        return out
    try:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if str(row.get("status", "")).strip().lower() != "solved":
                    continue
                fixture = str(row.get("fixture_id", "")).strip()
                if not fixture:
                    continue
                try:
                    text_id = int(str(row.get("text_id", "")).strip())
                    key_seed = int(str(row.get("key_seed", "")).strip())
                except Exception:
                    continue
                try:
                    best_match = float(str(row.get("best_match_ratio", "nan")).strip())
                except Exception:
                    best_match = float("nan")
                if not np.isfinite(best_match) or best_match < float(min_match):
                    continue
                ts = str(row.get("timestamp_utc", "")).strip()
                key = (fixture, int(text_id), int(key_seed))
                prev = out.get(key)
                if (prev is None) or (ts >= str(prev.get("timestamp_utc", ""))):
                    out[key] = dict(
                        timestamp_utc=ts,
                        run_id=str(row.get("run_id", "")).strip(),
                        best_match_ratio=float(best_match),
                        best_stage=str(row.get("best_stage", "")).strip(),
                        total_seconds=str(row.get("total_seconds", "")).strip(),
                        total_evals=str(row.get("total_evals", "")).strip(),
                    )
    except Exception:
        return {}
    return out


def _config_fingerprint(payload: Dict[str, Any]) -> str:
    try:
        canon = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except Exception:
        canon = str(payload)
    return hashlib.sha1(canon.encode("utf-8")).hexdigest()[:12]


def _parse_notes_kv(notes: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for part in re.split(r"[;|]", str(notes or "")):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        key = str(k).strip()
        if not key:
            continue
        out[key] = str(v).strip()
    return out


def _load_failed_attempt_index(
    path: Path,
    *,
    profile_id: str,
    config_fingerprint: str,
) -> Dict[Tuple[str, int, int], int]:
    out: Dict[Tuple[str, int, int], int] = {}
    if not path.exists():
        return out
    try:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                status = str(row.get("status", "")).strip().lower()
                if status not in {"unsolved", "stalled"}:
                    continue
                fixture = str(row.get("fixture_id", "")).strip()
                if not fixture:
                    continue
                try:
                    text_id = int(str(row.get("text_id", "")).strip())
                    key_seed = int(str(row.get("key_seed", "")).strip())
                except Exception:
                    continue
                row_profile = str(row.get("profile_id", "")).strip()
                if row_profile and row_profile != str(profile_id):
                    continue
                row_cfg = str(row.get("config_fingerprint", "")).strip()
                if not row_cfg:
                    row_cfg = _parse_notes_kv(str(row.get("notes", ""))).get("cfg", "")
                if row_cfg and row_cfg != str(config_fingerprint):
                    continue
                k = (fixture, int(text_id), int(key_seed))
                out[k] = int(out.get(k, 0)) + 1
    except Exception:
        return {}
    return out


def main() -> None:
    _apply_run_mode()
    _apply_runtime_overrides()
    direction = Direction.LTR
    print("[colsub] bootstrap: checking LM assets...", flush=True)
    base._require_assets(direction, ns=(1, 3, 4), need_wli=True)
    pt_base, wli_base = base._encode_long_plaintext(direction)

    root = _repo_root()
    run_dir = make_flavor_run_dir(flavor="col_then_sub", run_prefix="bench_solve_col_then_sub_pipeline")
    best_dir = run_dir / "best"
    best_dir.mkdir(parents=True, exist_ok=True)
    final_dir = run_dir / "final_instances"
    final_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"[colsub] setup: profile={PROFILE} mode={PIPELINE_RUN_MODE} "
        f"direction={direction.value} order={ORDER} A={ALPHABET_SIZE}",
        flush=True,
    )
    print(f"[colsub] setup: threshold={SOLVE_MATCH_THRESHOLD:.3f} stall_delta={STALL_DELTA:.4f} stall_limit={STALL_STAGE_LIMIT}", flush=True)
    print(
        "[colsub] setup: objective=pct.logp.win10 "
        f"impl={getattr(SCORER_IMPL, 'value', SCORER_IMPL)} "
        f"stage1=(char1,wli_off{' | c1->char34+wli34' if STAGE1_C1_USE_FULL_SCORER else ''}) "
        "stage2/3=(char34+wli34,wli_on)",
        flush=True,
    )
    print(
        "[colsub] setup: stop guards "
        f"stage1_plateau=(rounds={SOLVER_STAGE1.get('plateau_rounds')},delta={SOLVER_STAGE1.get('plateau_min_delta')}) "
        f"stage3_plateau=(rounds={SOLVER_STAGE3.get('plateau_rounds')},delta={SOLVER_STAGE3.get('plateau_min_delta')}) "
        f"stage1_oracle_stop={'on' if STAGE1_USE_ORACLE_GUIDE_STOP else 'off'} "
        f"stage3_oracle_stop={'on' if STAGE3_USE_ORACLE_GUIDE_STOP else 'off'} "
        f"stage3_oracle_relax={float(STAGE3_ORACLE_STOP_RELAX_FRACTION):.3f} "
        f"stage3_entry_full={STAGE3_FULL_ENTRY_SCORE if STAGE3_FULL_ENTRY_SCORE is not None else 'none'} "
        f"stage3_entry_full_by_c={json.dumps(STAGE3_FULL_ENTRY_SCORE_BY_COLUMNS, separators=(',', ':'))} "
        f"stage3_entry_probe={STAGE3_PROBE_ENTRY_SCORE if STAGE3_PROBE_ENTRY_SCORE is not None else 'none'} "
        f"stage3_entry_probe_by_c={json.dumps(STAGE3_PROBE_ENTRY_SCORE_BY_COLUMNS, separators=(',', ':'))}",
        flush=True,
    )
    print(
        "[colsub] setup: search knobs "
        f"stage1_seed_restarts={STAGE1_SEED_RESTARTS} "
        f"stage1_seed_plan=(blocks={STAGE1_SEED_N_BLOCKS},total={STAGE1_SEED_TOTAL},swaps={STAGE1_SEED_SWAPS}) "
        f"stage1_seed_restart_mult_by_period={json.dumps(STAGE1_SEED_RESTART_MULT_BY_PERIOD, separators=(',', ':'))} "
        f"stage1_seed_shrink_by_period={json.dumps(STAGE1_SEED_GLOBAL_SHRINK_BY_PERIOD, separators=(',', ':'))} "
        f"stage1_seed_phase_target_by_period={json.dumps(STAGE1_SEED_PHASE_LEN_TARGET_BY_PERIOD, separators=(',', ':'))} "
        f"stage12_scout_runs={int(STAGE12_SCOUT_RUNS)} "
        f"stage12_archive_keep={int(STAGE12_ARCHIVE_KEEP)} "
        f"stage12_promote_top={int(STAGE12_PROMOTE_TOP)} "
        f"stage1_scout_scale=(steps={float(STAGE1_SCOUT_STEP_SCALE):.2f},restarts={float(STAGE1_SCOUT_RESTART_SCALE):.2f}) "
        f"stage1_scout_mins=(steps={int(STAGE1_SCOUT_MIN_STEPS)},restarts={int(STAGE1_SCOUT_MIN_RESTARTS)}) "
        f"stage1_scout_plateau=(delta={float(STAGE1_SCOUT_NO_IMPROVE_DELTA):.1e},"
        f"patience={int(STAGE1_SCOUT_NO_IMPROVE_PATIENCE)},"
        f"min_new_archive={int(STAGE1_SCOUT_MIN_NEW_ARCHIVE)}) "
        f"stage1_c1_guards=(max_scouts={int(STAGE1_C1_MAX_SCOUTS)},"
        f"force_oracle_stop={int(bool(STAGE1_C1_FORCE_ORACLE_STOP))},"
        f"early_break_match={int(bool(STAGE1_C1_EARLY_BREAK_ON_SOLVED_MATCH))}) "
        f"stage1_sub_candidates={STAGE1_SUB_CANDIDATES} "
        f"stage1_sub_by_c={json.dumps(STAGE1_SUB_CANDIDATES_BY_COLUMNS, separators=(',', ':'))} "
        f"stage1_hard_rerank=(enabled={int(bool(STAGE1_HARD_RERANK_ENABLED))},"
        f"columns={sorted(int(x) for x in STAGE1_HARD_RERANK_COLUMNS)},"
        f"char={_weights_text(dict(SCORER_STAGE1_HARD_RERANK.get('char_weights', {})))}) "
        f"stage3_init_keys={STAGE3_INITIAL_KEYS} "
        f"stage3_init_by_c={json.dumps(STAGE3_INITIAL_KEYS_BY_COLUMNS, separators=(',', ':'))} "
        f"stage2_exact_max_columns={STAGE2_EXACT_MAX_COLUMNS} "
        f"stage2_exact_sub_candidates={STAGE2_EXACT_SUB_CANDIDATES} "
        f"stage2_exact_sub_by_c={json.dumps(STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS, separators=(',', ':'))} "
        f"stage2_hybrid_sub_candidates={STAGE2_HYBRID_SUB_CANDIDATES} "
        f"stage2_hybrid_sub_by_c={json.dumps(STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS, separators=(',', ':'))} "
        f"stage2_tail_total={STAGE2_TAIL_SEEDS_TOTAL} "
        f"stage2_tail_total_by_c={json.dumps(STAGE2_TAIL_SEEDS_TOTAL_BY_COLUMNS, separators=(',', ':'))} "
        f"stage2_tail_swaps={STAGE2_TAIL_STRUCTURED_SWAPS} "
        f"stage2_tail_swaps_by_c={json.dumps(STAGE2_TAIL_STRUCTURED_SWAPS_BY_COLUMNS, separators=(',', ':'))} "
        f"stage2_tail_random_fraction={float(STAGE2_TAIL_RANDOM_FRACTION):.2f} "
        f"stage2_two_pass={int(bool(STAGE2_EXACT_TWO_PASS))} "
        f"stage2_pass1_top_tails={STAGE2_EXACT_PASS1_TOP_TAILS} "
        f"stage2_pass1_top_by_c={json.dumps(STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS, separators=(',', ':'))} "
        f"stage2_early_solve_break={int(bool(STAGE2_EXACT_EARLY_SOLVE_BREAK))}",
        flush=True,
    )
    print(
        "[colsub] setup: stage3_dynamic_bands="
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
    print(
        "[colsub] setup: stage3_hard_far_override "
        f"hard_columns={sorted(int(x) for x in STAGE3_HARD_COLUMNS)} "
        f"override={json.dumps(STAGE3_HARD_FAR_OVERRIDE, separators=(',', ':'))}",
        flush=True,
    )
    print(f"[colsub] setup: tiers={len(TIERS)} text_offsets={TEXT_OFFSETS} key_seeds={KEY_SEEDS}", flush=True)
    if KEY_SEEDS_OVERRIDE or TIERS_REGEX_OVERRIDE or TIERS_PERIOD_SWEEP != "none" or TIERS_MIN_COLUMNS is not None:
        print(
            "[colsub] setup: runtime_overrides "
            f"key_seeds_override={KEY_SEEDS_OVERRIDE if KEY_SEEDS_OVERRIDE is not None else 'none'} "
            f"tiers_regex_override={TIERS_REGEX_OVERRIDE or 'none'} "
            f"tiers_period_sweep={TIERS_PERIOD_SWEEP} "
            f"tiers_min_columns={TIERS_MIN_COLUMNS if TIERS_MIN_COLUMNS is not None else 'none'}",
            flush=True,
        )
    print(f"[colsub] reports: {run_dir.relative_to(root)}", flush=True)

    hist = root / "tools" / "benchmarks" / "solve_proof" / "proven_solve_pipeline_col_then_sub_log.csv"
    hist.parent.mkdir(parents=True, exist_ok=True)
    autoskip_effective = bool(AUTOSKIP_PROVEN) and (not bool(FORCE_RERUN_PROVEN))
    proven_index = (
        _load_proven_solved_index(hist, min_match=float(AUTOSKIP_PROVEN_MIN_MATCH))
        if autoskip_effective
        else {}
    )
    print(
        "[colsub] setup: autoskip_proven="
        f"{'on' if autoskip_effective else 'off'} "
        f"(requested={'on' if AUTOSKIP_PROVEN else 'off'}, force_rerun={'on' if FORCE_RERUN_PROVEN else 'off'}) "
        f"min_match={float(AUTOSKIP_PROVEN_MIN_MATCH):.3f} "
        f"known={len(proven_index)} "
        f"source={hist.relative_to(root)}",
        flush=True,
    )
    solved_jsonl = root / "tools" / "benchmarks" / "solve_proof" / "proven_solve_pipeline_col_then_sub_solved.jsonl"
    solved_jsonl.parent.mkdir(parents=True, exist_ok=True)
    proven_dir = run_dir / "proven_instances"
    proven_dir.mkdir(parents=True, exist_ok=True)

    stages: List[dict] = []
    instances: List[dict] = []
    total = len(TIERS) * len(TEXT_OFFSETS) * len(KEY_SEEDS)
    done = 0
    t0_all = time.time()
    last_hb = float(t0_all)
    history_rows_written = 0
    solved_rows_written = 0
    run_config = dict(
        profile=PROFILE,
        mode=PIPELINE_RUN_MODE,
        direction=direction.value,
        order=ORDER,
        alphabet_size=int(ALPHABET_SIZE),
        solve_threshold=float(SOLVE_MATCH_THRESHOLD),
        stall_delta=float(STALL_DELTA),
        autoskip_proven=bool(autoskip_effective),
        autoskip_proven_requested=bool(AUTOSKIP_PROVEN),
        force_rerun_proven=bool(FORCE_RERUN_PROVEN),
        autoskip_proven_min_match=float(AUTOSKIP_PROVEN_MIN_MATCH),
        stage1_use_oracle_stop=bool(STAGE1_USE_ORACLE_GUIDE_STOP),
        stage3_use_oracle_stop=bool(STAGE3_USE_ORACLE_GUIDE_STOP),
        stage3_oracle_stop_relax=float(STAGE3_ORACLE_STOP_RELAX_FRACTION),
        stage3_full_entry_score=(None if STAGE3_FULL_ENTRY_SCORE is None else float(STAGE3_FULL_ENTRY_SCORE)),
        stage3_full_entry_by_c=dict(STAGE3_FULL_ENTRY_SCORE_BY_COLUMNS),
        stage3_probe_entry_score=(None if STAGE3_PROBE_ENTRY_SCORE is None else float(STAGE3_PROBE_ENTRY_SCORE)),
        stage3_probe_entry_by_c=dict(STAGE3_PROBE_ENTRY_SCORE_BY_COLUMNS),
        stage1_seed_plan=dict(
            seed_restarts=int(STAGE1_SEED_RESTARTS),
            n_blocks=int(STAGE1_SEED_N_BLOCKS),
            total=int(STAGE1_SEED_TOTAL),
            swaps=int(STAGE1_SEED_SWAPS),
            restart_mult_by_period=dict(STAGE1_SEED_RESTART_MULT_BY_PERIOD),
            global_shrink_default=float(STAGE1_SEED_GLOBAL_SHRINK_DEFAULT),
            global_shrink_by_period=dict(STAGE1_SEED_GLOBAL_SHRINK_BY_PERIOD),
            phase_len_target_default=int(STAGE1_SEED_PHASE_LEN_TARGET_DEFAULT),
            phase_len_target_by_period=dict(STAGE1_SEED_PHASE_LEN_TARGET_BY_PERIOD),
        ),
        stage12_scout=dict(
            runs=int(STAGE12_SCOUT_RUNS),
            archive_keep=int(STAGE12_ARCHIVE_KEEP),
            promote_top=int(STAGE12_PROMOTE_TOP),
            step_scale=float(STAGE1_SCOUT_STEP_SCALE),
            restart_scale=float(STAGE1_SCOUT_RESTART_SCALE),
            min_steps=int(STAGE1_SCOUT_MIN_STEPS),
            min_restarts=int(STAGE1_SCOUT_MIN_RESTARTS),
            no_improve_delta=float(STAGE1_SCOUT_NO_IMPROVE_DELTA),
            no_improve_patience=int(STAGE1_SCOUT_NO_IMPROVE_PATIENCE),
            min_new_archive=int(STAGE1_SCOUT_MIN_NEW_ARCHIVE),
        ),
        stage1_c1_guards=dict(
            max_scouts=int(STAGE1_C1_MAX_SCOUTS),
            force_oracle_stop=bool(STAGE1_C1_FORCE_ORACLE_STOP),
            oracle_stop_margin=float(STAGE1_C1_ORACLE_STOP_MARGIN),
            early_break_on_solved_match=bool(STAGE1_C1_EARLY_BREAK_ON_SOLVED_MATCH),
        ),
        stage1_sub_candidates=int(STAGE1_SUB_CANDIDATES),
        stage1_sub_by_c=dict(STAGE1_SUB_CANDIDATES_BY_COLUMNS),
        stage1_hard_rerank=dict(
            enabled=bool(STAGE1_HARD_RERANK_ENABLED),
            columns=sorted(int(x) for x in STAGE1_HARD_RERANK_COLUMNS),
            scorer=dict(SCORER_STAGE1_HARD_RERANK),
        ),
        stage2_exact_sub_by_c=dict(STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS),
        stage2_pass1_top_by_c=dict(STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS),
        stage2_hybrid_sub_candidates=int(STAGE2_HYBRID_SUB_CANDIDATES),
        stage2_hybrid_sub_by_c=dict(STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS),
        stage2_tail_seed_pool=dict(
            total=int(STAGE2_TAIL_SEEDS_TOTAL),
            total_by_c=dict(STAGE2_TAIL_SEEDS_TOTAL_BY_COLUMNS),
            structured_swaps=int(STAGE2_TAIL_STRUCTURED_SWAPS),
            structured_swaps_by_c=dict(STAGE2_TAIL_STRUCTURED_SWAPS_BY_COLUMNS),
            random_fraction=float(STAGE2_TAIL_RANDOM_FRACTION),
        ),
        stage3_init_by_c=dict(STAGE3_INITIAL_KEYS_BY_COLUMNS),
        stage3_dynamic_bands=[dict(b) for b in STAGE3_DYNAMIC_BANDS],
        stage3_hard_far_override=dict(
            hard_columns=sorted(int(x) for x in STAGE3_HARD_COLUMNS),
            override=dict(STAGE3_HARD_FAR_OVERRIDE),
        ),
        scorer_stage1=dict(SCORER_STAGE1),
        scorer_stage23=dict(SCORER_FULL),
        solver_stage1=dict(SOLVER_STAGE1),
        solver_stage2=dict(SOLVER_STAGE2),
        solver_stage3=dict(SOLVER_STAGE3),
        runtime_overrides=dict(
            key_seeds_override=(
                [int(x) for x in KEY_SEEDS_OVERRIDE]
                if KEY_SEEDS_OVERRIDE is not None
                else None
            ),
            tiers_regex_override=(
                None if TIERS_REGEX_OVERRIDE in (None, "") else str(TIERS_REGEX_OVERRIDE)
            ),
            tiers_period_sweep=str(TIERS_PERIOD_SWEEP),
            tiers_min_columns=(
                None if TIERS_MIN_COLUMNS is None else int(TIERS_MIN_COLUMNS)
            ),
        ),
        failed_repeat_avoid=dict(
            enabled=bool(AVOID_REPEAT_FAIL),
            retry_seed_delta=int(FAILED_RETRY_SEED_DELTA),
            retry_seed_stride=int(FAILED_RETRY_SEED_STRIDE),
        ),
    )
    config_fingerprint = _config_fingerprint(run_config)
    failed_attempt_index = (
        _load_failed_attempt_index(
            hist,
            profile_id=str(PROFILE),
            config_fingerprint=str(config_fingerprint),
        )
        if bool(AVOID_REPEAT_FAIL)
        else {}
    )
    run_config["config_fingerprint"] = str(config_fingerprint)
    run_config["failed_repeat_avoid"] = dict(
        enabled=bool(AVOID_REPEAT_FAIL),
        retry_seed_delta=int(FAILED_RETRY_SEED_DELTA),
        retry_seed_stride=int(FAILED_RETRY_SEED_STRIDE),
        known_failed=len(failed_attempt_index),
    )
    write_json(run_dir / "run_config.json", run_config)
    print(
        "[colsub] setup: failed_repeat_avoid="
        f"{'on' if AVOID_REPEAT_FAIL else 'off'} "
        f"retry_seed_delta={int(FAILED_RETRY_SEED_DELTA)} "
        f"known_failed={len(failed_attempt_index)} "
        f"config_fingerprint={config_fingerprint}",
        flush=True,
    )
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
                proven_key = (str(tier.name), int(text_id), int(key_seed))
                repeat_attempt = int(failed_attempt_index.get(proven_key, 0)) if bool(AVOID_REPEAT_FAIL) else 0
                search_seed_offset = int(repeat_attempt * int(FAILED_RETRY_SEED_DELTA))
                search_seed_shift = int(search_seed_offset * int(FAILED_RETRY_SEED_STRIDE))
                if bool(autoskip_effective) and (proven_key in proven_index):
                    src = dict(proven_index.get(proven_key, {}))
                    src_run = str(src.get("run_id", "") or "")
                    src_ts = str(src.get("timestamp_utc", "") or "")
                    src_match = float(src.get("best_match_ratio", float("nan")))
                    src_stage = str(src.get("best_stage", "") or "proven_history")
                    stop_reason = (
                        f"autoskip_proven:source_run={src_run}" if src_run else "autoskip_proven"
                    )
                    preview_txt = (
                        f"[autoskip] source_run={src_run}" if src_run else "[autoskip] proven history"
                    )
                    instances.append(
                        dict(
                            tier=tier.name,
                            period=tier.period,
                            columns=tier.columns,
                            length=tier.length,
                            text_id=int(text_id),
                            key_seed=int(key_seed),
                            offset_hint=int(off),
                            offset_used=int(offset_used),
                            status="skipped_proven",
                            stop_reason=stop_reason,
                            solve_threshold=float(SOLVE_MATCH_THRESHOLD),
                            best_stage=src_stage,
                            best_match_ratio=float(src_match if np.isfinite(src_match) else np.nan),
                            best_objective_score=np.nan,
                            stage1_sub_key_match=np.nan,
                            stage2_match_ratio=np.nan,
                            stage3_match_ratio=np.nan,
                            stage2_gap_to_oracle=np.nan,
                            stage3_entry_mode="autoskip",
                            stage3_entry_full_score=np.nan,
                            stage3_entry_probe_score=np.nan,
                            stage3_band="autoskip",
                            total_seconds=0.0,
                            total_evals=0,
                            preview_best_latin=preview_txt,
                            retry_attempt=int(repeat_attempt),
                            search_seed_offset=int(search_seed_offset),
                            config_fingerprint=str(config_fingerprint),
                        )
                    )
                    stages.append(
                        dict(
                            tier=tier.name,
                            text_id=int(text_id),
                            key_seed=int(key_seed),
                            stage="skip_proven",
                            score=np.nan,
                            match_ratio=float(src_match if np.isfinite(src_match) else np.nan),
                            seconds=0.0,
                            evals=0,
                            source_run_id=src_run,
                            source_timestamp=src_ts,
                        )
                    )

                    inst_row = dict(instances[-1])

                    if np.isfinite(float(inst_row.get("best_match_ratio", np.nan))) and float(inst_row["best_match_ratio"]) > float(best_global["match"]):
                        best_global["match"] = float(inst_row["best_match_ratio"])
                        best_global["tier"] = str(tier.name)
                        best_global["text_id"] = int(text_id)
                        best_global["key_seed"] = int(key_seed)
                        best_global["stage"] = str(inst_row.get("best_stage", "autoskip"))
                        best_global["preview"] = str(preview_txt)

                    summary_ckpt = _build_summary(TIERS, instances)
                    write_pipeline_snapshot_files(
                        run_dir=run_dir,
                        instances=instances,
                        stages=stages,
                        summary=summary_ckpt,
                    )

                    stage_rows_instance = [
                        dict(s)
                        for s in stages
                        if s.get("tier") == tier.name
                        and int(s.get("text_id", -1)) == int(text_id)
                        and int(s.get("key_seed", -1)) == int(key_seed)
                    ]
                    artifact_payload = dict(
                        profile=PROFILE,
                        mode=PIPELINE_RUN_MODE,
                        config_fingerprint=str(config_fingerprint),
                        instance=inst_row,
                        stages=stage_rows_instance,
                        io=dict(
                            ciphertext_idx=[],
                            target_plaintext_idx=_to_int_list(pt_idx),
                            final_best_key_idx=[],
                            final_best_plaintext_idx=[],
                        ),
                    )
                    artifact_name = (
                        f"{tier.name}__text{int(text_id)}__seed{int(key_seed)}.json"
                    )
                    final_dir.mkdir(parents=True, exist_ok=True)
                    write_json(final_dir / artifact_name, artifact_payload)

                    hist_row = dict(
                        timestamp_utc=datetime.now(timezone.utc).isoformat(),
                        run_id=run_dir.name,
                        profile_id=PROFILE,
                        fixture_id=inst_row["tier"],
                        text_id=inst_row["text_id"],
                        key_seed=inst_row["key_seed"],
                        period=inst_row["period"],
                        columns=inst_row["columns"],
                        length=inst_row["length"],
                        status=inst_row["status"],
                        solve_threshold=inst_row["solve_threshold"],
                        best_match_ratio=inst_row["best_match_ratio"],
                        best_stage=inst_row["best_stage"],
                        stage1_sub_key_match=inst_row["stage1_sub_key_match"],
                        stage2_match_ratio=inst_row["stage2_match_ratio"],
                        stage2_sub_key_match=inst_row.get("stage2_sub_key_match", np.nan),
                        stage2_tail_key_match=inst_row.get("stage2_tail_key_match", np.nan),
                        stage3_match_ratio=inst_row["stage3_match_ratio"],
                        stage3_sub_key_match=inst_row.get("stage3_sub_key_match", np.nan),
                        stage3_tail_key_match=inst_row.get("stage3_tail_key_match", np.nan),
                        total_seconds=inst_row["total_seconds"],
                        total_evals=inst_row["total_evals"],
                        notes=(
                            f"{inst_row['stop_reason']};"
                            f"cfg={config_fingerprint};"
                            f"retry={int(repeat_attempt)};"
                            f"soff={int(search_seed_offset)}"
                        ),
                    )
                    _append_csv_row_common(hist, hist_row, merge_fieldnames=True)
                    history_rows_written += 1

                    done += 1
                    elapsed = time.time() - t0_all
                    eta = (elapsed / float(done)) * float(total - done) if done else 0.0
                    print(
                        f"[colsub] skip-proven tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"source_run={src_run if src_run else 'unknown'} "
                        f"best_match={float(src_match):.3f}",
                        flush=True,
                    )
                    print(
                        f"[colsub] {done}/{total} tier={tier.name} status=skipped_proven "
                        f"best_match={float(src_match if np.isfinite(src_match) else 0.0):.3f} "
                        f"run={base._format_seconds(time.time() - t0_i)} "
                        f"elapsed={base._format_seconds(elapsed)} eta={base._format_seconds(eta)}",
                        flush=True,
                    )
                    now = time.time()
                    if (now - last_hb) >= float(HEARTBEAT_SECONDS):
                        print(
                            f"[colsub] heartbeat elapsed={base._format_seconds(now - t0_all)} "
                            f"done={done}/{total} "
                            f"global_best_match={float(best_global['match']):.3f} "
                            f"tier={best_global['tier']} text={best_global['text_id']} key_seed={best_global['key_seed']} "
                            f"stage={best_global['stage']} preview=\"{best_global['preview']}\"",
                            flush=True,
                        )
                        last_hb = now
                    continue

                if bool(AVOID_REPEAT_FAIL) and int(repeat_attempt) > 0:
                    print(
                        f"[colsub] retry-avoid tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"prior_failed_attempts={int(repeat_attempt)} "
                        f"search_seed_offset={int(search_seed_offset)}",
                        flush=True,
                    )

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
                true_tail = key_true[sub_len : sub_len + int(tier.columns)].astype(
                    np.int16, copy=False
                )
                pt_stage1_oracle = np.asarray(sub_cipher.decrypt_single(ciphertext=ct_idx, key=true_sub), dtype=np.uint8).reshape(-1)
                scorer_full = dict(SCORER_FULL, encoding_dir=direction)
                stage1_use_full = bool(STAGE1_C1_USE_FULL_SCORER and int(tier.columns) == 1)
                scorer_stage1 = dict((SCORER_FULL if stage1_use_full else SCORER_STAGE1), encoding_dir=direction)
                stage1_force_no_wli = (not stage1_use_full)
                stage1_hard_rerank_active = bool(
                    STAGE1_HARD_RERANK_ENABLED
                    and int(tier.columns) in set(int(x) for x in STAGE1_HARD_RERANK_COLUMNS)
                )
                print(
                    f"[colsub] objective tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"search_seed_offset={int(search_seed_offset)} "
                    f"stage1={scorer_stage1['objective']} "
                    f"stage23={scorer_full['objective']}",
                    flush=True,
                )
                scorer_full_runtime = build_scorer(cfg_full, ScoringConfig(**scorer_full))
                scorer_stage1_runtime = build_scorer(cfg_sub, ScoringConfig(**scorer_stage1))
                scorer_stage1_hard_runtime = (
                    build_scorer(
                        cfg_sub,
                        ScoringConfig(**dict(SCORER_STAGE1_HARD_RERANK, encoding_dir=direction)),
                    )
                    if stage1_hard_rerank_active
                    else None
                )
                scorer_stage2_fast_runtime = None
                if int(tier.columns) <= int(STAGE2_EXACT_MAX_COLUMNS) and bool(STAGE2_EXACT_TWO_PASS):
                    scorer_stage2_fast = dict(
                        objective="pct.logp.win10",
                        include_char=True,
                        use_word_breaks=False,
                        char_weights=dict(STAGE2_FAST_CHAR_WEIGHTS),
                        wli_weights={},
                        encoding_dir=direction,
                        impl=SCORER_IMPL,
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
                stage1_weights_src = (SCORER_FULL if stage1_use_full else SCORER_STAGE1)
                print(
                    "[colsub] oracle-score "
                    f"stage=stage1_sub model={s1_obj} "
                    f"(char={_weights_text(dict(stage1_weights_src.get('char_weights', {})))},"
                    f"wli={_weights_text(dict(stage1_weights_src.get('wli_weights', {})))},"
                    f"wb={0 if stage1_force_no_wli else 1}) "
                    f"score={oracle_s1:.6f} raw={oracle_s1_raw:.6f}",
                    flush=True,
                )
                print(
                    "[colsub] oracle-score "
                    f"stage=stage2_3 model={s23_obj} "
                    f"(char={_weights_text(dict(SCORER_FULL.get('char_weights', {})))},"
                    f"wli={_weights_text(dict(SCORER_FULL.get('wli_weights', {})))},wb=1) "
                    f"score={oracle_s23:.6f} raw={oracle_s23_raw:.6f}",
                    flush=True,
                )
                if not np.array_equal(np.asarray(full_cipher.decrypt_single(ciphertext=ct_idx, key=key_true), dtype=np.uint8), np.asarray(pt_idx, dtype=np.uint8)):
                    raise RuntimeError(f"[colsub] gate0 roundtrip failed tier={tier.name} text={text_id} key_seed={key_seed}")
                _print_stage_preview(label="oracle", pt=pt_idx.tolist(), wli=wli, scorer_wli=True, match_ratio=1.0)

                # Stage 1
                t_s1 = time.time()
                solver_stage1_base_cfg = dict(SOLVER_STAGE1)
                solver_stage1_base_cfg["seed"] = int(solver_stage1_base_cfg.get("seed", 2026)) + int(search_seed_shift)
                stage1_sub_limit = int(STAGE1_SUB_CANDIDATES_BY_COLUMNS.get(int(tier.columns), STAGE1_SUB_CANDIDATES))
                stage1_archive_keep = max(int(stage1_sub_limit), int(STAGE12_ARCHIVE_KEEP), 1)
                stage1_scout_runs = max(1, int(STAGE12_SCOUT_RUNS))
                if int(tier.columns) == 1:
                    stage1_scout_runs = min(int(stage1_scout_runs), int(STAGE1_C1_MAX_SCOUTS))
                stage1_oracle_guard = bool(
                    STAGE1_USE_ORACLE_GUIDE_STOP
                    or (
                        bool(STAGE1_C1_FORCE_ORACLE_STOP)
                        and int(tier.columns) == 1
                        and bool(stage1_use_full)
                    )
                )
                if stage1_oracle_guard:
                    s1_margin = (
                        float(STAGE1_ORACLE_STOP_MARGIN)
                        if bool(STAGE1_USE_ORACLE_GUIDE_STOP)
                        else float(STAGE1_C1_ORACLE_STOP_MARGIN)
                    )
                    s1_stop = min(0.999999, float(oracle_s1) + float(s1_margin))
                    solver_stage1_base_cfg["stop_score"] = float(s1_stop)
                period_restart_mult = float(
                    STAGE1_SEED_RESTART_MULT_BY_PERIOD.get(int(tier.period), 1.0)
                )
                solver_stage1_base_cfg["seed_restarts"] = max(
                    1,
                    int(
                        round(
                            float(
                                solver_stage1_base_cfg.get(
                                    "seed_restarts", STAGE1_SEED_RESTARTS
                                )
                            )
                            * period_restart_mult
                        )
                    ),
                )
                seed_global_shrink = float(
                    STAGE1_SEED_GLOBAL_SHRINK_BY_PERIOD.get(
                        int(tier.period), STAGE1_SEED_GLOBAL_SHRINK_DEFAULT
                    )
                )
                seed_phase_len_target = int(
                    STAGE1_SEED_PHASE_LEN_TARGET_BY_PERIOD.get(
                        int(tier.period), STAGE1_SEED_PHASE_LEN_TARGET_DEFAULT
                    )
                )
                print(
                    f"[colsub] stage1-stop tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"stop_score={solver_stage1_base_cfg.get('stop_score', 'none')} "
                    f"plateau_rounds={solver_stage1_base_cfg.get('plateau_rounds')} "
                    f"plateau_min_delta={solver_stage1_base_cfg.get('plateau_min_delta')} "
                    f"seed_restarts={solver_stage1_base_cfg.get('seed_restarts')} "
                    f"seed_restart_mult={period_restart_mult:.2f} "
                    f"seed_shrink={seed_global_shrink:.3f} "
                    f"seed_phase_target={seed_phase_len_target} "
                    f"scouts={stage1_scout_runs} archive_keep={stage1_archive_keep} "
                    f"scout_plateau=(delta={float(STAGE1_SCOUT_NO_IMPROVE_DELTA):.1e},"
                    f"patience={int(STAGE1_SCOUT_NO_IMPROVE_PATIENCE)},"
                    f"min_new_archive={int(STAGE1_SCOUT_MIN_NEW_ARCHIVE)}) "
                    f"search_seed_offset={int(search_seed_offset)} "
                    f"oracle_guard={'on' if stage1_oracle_guard else 'off'}",
                    flush=True,
                )
                s1_eval_wli = None if stage1_force_no_wli else wli
                stage1_archive: Dict[Tuple[int, ...], Dict[str, Any]] = {}
                stage1_best_score = float("-inf")
                stage1_best_sub: List[int] = []
                stage1_best_pt: List[int] = []
                stage1_best_match = float("-inf")
                ev1 = 0
                base_steps = int(solver_stage1_base_cfg.get("steps", 0))
                base_restarts = int(solver_stage1_base_cfg.get("restarts", 0))
                base_seed_restarts = int(
                    solver_stage1_base_cfg.get("seed_restarts", STAGE1_SEED_RESTARTS)
                )
                stage1_scouts_done = 0
                stage1_no_improve_scouts = 0
                stage1_rerank_evals = 0

                for scout_idx in range(stage1_scout_runs):
                    stage1_scouts_done += 1
                    pre_scout_best_score = float(stage1_best_score)
                    pre_scout_archive_n = int(len(stage1_archive))
                    solver_stage1_cfg = dict(solver_stage1_base_cfg)
                    solver_stage1_cfg["seed"] = int(solver_stage1_base_cfg.get("seed", 2026)) + 7919 * int(scout_idx)
                    if scout_idx > 0:
                        solver_stage1_cfg["steps"] = max(
                            int(STAGE1_SCOUT_MIN_STEPS),
                            int(round(float(base_steps) * float(STAGE1_SCOUT_STEP_SCALE))),
                        )
                        solver_stage1_cfg["restarts"] = max(
                            int(STAGE1_SCOUT_MIN_RESTARTS),
                            int(round(float(base_restarts) * float(STAGE1_SCOUT_RESTART_SCALE))),
                        )
                        solver_stage1_cfg["seed_restarts"] = max(
                            1,
                            int(round(float(base_seed_restarts) * float(STAGE1_SCOUT_RESTART_SCALE))),
                        )

                    scout_seed = 2026 + int(key_seed) + int(search_seed_shift) + 1009 * int(scout_idx)
                    s1_seeds = make_periodic_seed_pool_col_then_sub(
                        ct_idx,
                        period=tier.period,
                        direction=direction.value,
                        seed=int(scout_seed),
                        n_block_seeds=int(STAGE1_SEED_N_BLOCKS),
                        total_seeds=int(STAGE1_SEED_TOTAL),
                        swaps_per_block=int(STAGE1_SEED_SWAPS),
                        alphabet_size=ALPHABET_SIZE,
                        global_shrink=float(seed_global_shrink),
                        phase_len_target=int(seed_phase_len_target),
                    )
                    sol1 = run(
                        text=ct_idx.tolist(),
                        cipher=by_name.cipher("periodic_substitution", period=tier.period, alphabet_size=ALPHABET_SIZE),
                        key=KeySpec.periodic_substitution(period=tier.period, alphabet_size=ALPHABET_SIZE),
                        solver=SolverSpec.kaeding(**solver_stage1_cfg),
                        scorer_params=scorer_stage1,
                        wli_data=wli,
                        encoding_dir=direction,
                        telemetry_on=True,
                        initial_keys=s1_seeds,
                        force_no_wli=stage1_force_no_wli,
                    )
                    ev1 += int((getattr(sol1, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
                    sub_best = np.asarray(getattr(sol1, "key", []) or [], dtype=np.int16).reshape(-1)
                    sub_key_match_this = base._match_ratio(sub_best.tolist(), true_sub.tolist())
                    sub_candidates_this = _extract_top_keys(sol1, limit=stage1_sub_limit) or [sub_best.astype(int).tolist()]
                    sub_eval_keys: List[List[int]] = []
                    for sub_key in sub_candidates_this:
                        sub_arr = np.asarray(sub_key, dtype=np.int16).reshape(-1)
                        if sub_arr.size != int(sub_len):
                            continue
                        sub_eval_keys.append(sub_arr.astype(int).tolist())
                    if sub_eval_keys:
                        pt1_batch, sc1_batch, _batch_stats = decrypt_and_score_keys_chunked(
                            cipher=sub_cipher,
                            ciphertext=ct_idx,
                            keys=sub_eval_keys,
                            scorer=scorer_stage1_runtime,
                            wli=s1_eval_wli,
                            chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                            require_batch=bool(REQUIRE_BATCH_SCORING),
                        )
                        for j, sub_key_vals in enumerate(sub_eval_keys):
                            sub_arr = np.asarray(sub_key_vals, dtype=np.int16).reshape(-1)
                            pt1 = np.asarray(pt1_batch[j], dtype=np.uint8).reshape(-1)
                            sc1 = float(sc1_batch[j]) if j < int(sc1_batch.size) else float("nan")
                            key_t = tuple(int(x) for x in sub_arr.tolist())
                            sub_m = float(base._match_ratio(sub_arr.tolist(), true_sub.tolist()))
                            prev = stage1_archive.get(key_t)
                            if (prev is None) or (sc1 > float(prev.get("score", float("-inf")))):
                                stage1_archive[key_t] = dict(
                                    sub_key=sub_arr.astype(int).tolist(),
                                    score=float(sc1),
                                    sub_key_match=float(sub_m),
                                    plaintext=pt1.astype(int).tolist(),
                                )
                            if sc1 > stage1_best_score:
                                stage1_best_score = float(sc1)
                                stage1_best_sub = sub_arr.astype(int).tolist()
                                stage1_best_pt = pt1.astype(int).tolist()
                                stage1_best_match = float(sub_m)

                    stages.append(
                        dict(
                            tier=tier.name,
                            text_id=int(text_id),
                            key_seed=int(key_seed),
                            stage=f"stage1_sub_scout_{int(scout_idx) + 1}",
                            score=float(getattr(sol1, "score", float("nan"))),
                            sub_key_match=float(sub_key_match_this),
                            seconds=0.0,
                            evals=int((getattr(sol1, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0),
                            candidates=len(sub_candidates_this),
                            scout_seed=int(scout_seed),
                        )
                    )
                    if (
                        bool(STAGE1_C1_EARLY_BREAK_ON_SOLVED_MATCH)
                        and int(tier.columns) == 1
                        and stage1_best_pt
                    ):
                        stage1_best_m = float(base._match_ratio(stage1_best_pt, pt_idx.tolist()))
                        if stage1_best_m >= float(SOLVE_MATCH_THRESHOLD):
                            print(
                                f"[colsub] stage1-early-stop tier={tier.name} text={text_id} key_seed={key_seed} "
                                f"reason=c1_solved match={stage1_best_m:.3f} scouts_done={stage1_scouts_done}/{stage1_scout_runs}",
                                flush=True,
                            )
                            break

                    stage1_score_gain = float(stage1_best_score - pre_scout_best_score) if np.isfinite(stage1_best_score) and np.isfinite(pre_scout_best_score) else float("inf")
                    stage1_new_archive = int(len(stage1_archive) - pre_scout_archive_n)
                    if (
                        scout_idx > 0
                        and stage1_score_gain <= float(STAGE1_SCOUT_NO_IMPROVE_DELTA)
                        and stage1_new_archive <= int(STAGE1_SCOUT_MIN_NEW_ARCHIVE)
                    ):
                        stage1_no_improve_scouts += 1
                    else:
                        stage1_no_improve_scouts = 0
                    if (
                        scout_idx + 1 < int(stage1_scout_runs)
                        and stage1_no_improve_scouts >= int(STAGE1_SCOUT_NO_IMPROVE_PATIENCE)
                    ):
                        print(
                            f"[colsub] stage1-early-stop tier={tier.name} text={text_id} key_seed={key_seed} "
                            f"reason=scout_plateau scouts_done={stage1_scouts_done}/{stage1_scout_runs} "
                            f"score_gain={stage1_score_gain:.6g} new_archive={stage1_new_archive}",
                            flush=True,
                        )
                        break

                dt1 = float(time.time() - t_s1)
                if stage1_hard_rerank_active and scorer_stage1_hard_runtime is not None and stage1_archive:
                    rerank_entries: List[Dict[str, Any]] = []
                    rerank_plaintexts: List[np.ndarray] = []
                    for entry in stage1_archive.values():
                        pt_entry = np.asarray(entry.get("plaintext", []), dtype=np.uint8).reshape(-1)
                        if pt_entry.size == 0:
                            continue
                        rerank_entries.append(entry)
                        rerank_plaintexts.append(pt_entry)
                    reranked = 0
                    if rerank_plaintexts:
                        rerank_scores, _batch_stats = score_plaintexts_chunked(
                            scorer=scorer_stage1_hard_runtime,
                            plaintexts=rerank_plaintexts,
                            wli=None,
                            chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                            require_batch=bool(REQUIRE_BATCH_SCORING),
                        )
                        for idx, entry in enumerate(rerank_entries):
                            if idx < int(rerank_scores.size):
                                entry["rerank_score"] = float(rerank_scores[idx])
                                reranked += 1
                    stage1_rerank_evals = int(reranked)
                    ev1 += int(reranked)
                    print(
                        f"[colsub] stage1-rerank tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"mode=char34_no_wli active=1 entries={reranked}",
                        flush=True,
                    )
                stage1_ranked = sorted(
                    stage1_archive.values(),
                    key=(
                        (lambda e: (
                            float(e.get("rerank_score", float("-inf"))),
                            float(e.get("score", float("-inf"))),
                            float(e.get("sub_key_match", float("-inf"))),
                        ))
                        if stage1_hard_rerank_active
                        else (lambda e: (
                            float(e.get("score", float("-inf"))),
                            float(e.get("sub_key_match", float("-inf"))),
                        ))
                    ),
                    reverse=True,
                )
                if len(stage1_ranked) > int(stage1_archive_keep):
                    stage1_ranked = stage1_ranked[: int(stage1_archive_keep)]
                sub_candidates = [list(map(int, e.get("sub_key", []))) for e in stage1_ranked if e.get("sub_key")]
                if not sub_candidates and stage1_best_sub:
                    sub_candidates = [list(stage1_best_sub)]
                sub_key_match = float(stage1_best_match if np.isfinite(stage1_best_match) else 0.0)
                if stage1_best_pt:
                    m1 = base._match_ratio(stage1_best_pt, pt_idx.tolist())
                    _print_stage_preview(label="stage1_sub", pt=stage1_best_pt, wli=wli, scorer_wli=not stage1_force_no_wli, match_ratio=float(m1))
                stages.append(
                    dict(
                        tier=tier.name,
                        text_id=int(text_id),
                        key_seed=int(key_seed),
                        stage="stage1_sub",
                        score=float(stage1_best_score if np.isfinite(stage1_best_score) else np.nan),
                        sub_key_match=float(sub_key_match),
                        seconds=round(dt1, 3),
                        evals=int(ev1),
                        candidates=len(sub_candidates),
                        scouts=int(stage1_scouts_done),
                        archive_keep=int(stage1_archive_keep),
                        hard_rerank_active=int(bool(stage1_hard_rerank_active)),
                        hard_rerank_evals=int(stage1_rerank_evals),
                    )
                )
                print(
                    f"[colsub] stage1-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"score={float(stage1_best_score if np.isfinite(stage1_best_score) else np.nan):.6f} "
                    f"sub_key_match={float(sub_key_match):.3f} "
                    f"evals={int(ev1)} seconds={dt1:.1f} "
                    f"candidates={len(sub_candidates)} scouts={int(stage1_scouts_done)} "
                    f"hard_rerank={'on' if stage1_hard_rerank_active else 'off'} "
                    f"rerank_evals={int(stage1_rerank_evals)}",
                    flush=True,
                )

                # Stage 2
                best2_match, best2_score, best2_key, best2_preview, best2_secs, best2_evals = float("-inf"), float("-inf"), None, "", 0.0, 0
                best2_pt: List[int] | None = None
                best2_sub_key_match = float("nan")
                best2_tail_key_match = float("nan")
                stage2_evals_total = 0
                stage2_archive_keep = max(1, int(STAGE12_ARCHIVE_KEEP))
                stage2_promote_top = max(1, int(STAGE12_PROMOTE_TOP))
                stage2_archive: Dict[Tuple[int, ...], Dict[str, Any]] = {}
                stage2_entry_score = float("-inf")

                def _consider_stage2_candidate(
                    *,
                    full_key_arr: np.ndarray,
                    pt2_arr: np.ndarray,
                    match_val: float,
                    score_val: float,
                    preview_label: str,
                    sub_key_match: float | None = None,
                    tail_key_match: float | None = None,
                ) -> None:
                    nonlocal best2_match, best2_score, best2_key, best2_pt, best2_preview, best2_secs, best2_evals
                    nonlocal best2_sub_key_match, best2_tail_key_match
                    key_list = full_key_arr.astype(int).tolist()
                    key_t = tuple(int(x) for x in key_list)
                    prev = stage2_archive.get(key_t)
                    if (prev is None) or (float(score_val) > float(prev.get("score", float("-inf")))):
                        stage2_archive[key_t] = dict(
                            key=key_list,
                            score=float(score_val),
                            match=float(match_val),
                            sub_key_match=(
                                float(sub_key_match) if sub_key_match is not None else float("nan")
                            ),
                            tail_key_match=(
                                float(tail_key_match) if tail_key_match is not None else float("nan")
                            ),
                            plaintext=pt2_arr.astype(int).tolist(),
                            preview=base._safe_preview_latin(pt2_arr, wli),
                        )
                    if (match_val > best2_match) or (abs(match_val - best2_match) <= 1e-12 and score_val > best2_score):
                        best2_match, best2_score = float(match_val), float(score_val)
                        best2_sub_key_match = (
                            float(sub_key_match) if sub_key_match is not None else float("nan")
                        )
                        best2_tail_key_match = (
                            float(tail_key_match) if tail_key_match is not None else float("nan")
                        )
                        best2_key = key_list
                        best2_pt = pt2_arr.astype(int).tolist()
                        best2_preview = base._safe_preview_latin(pt2_arr, wli)
                        best2_secs, best2_evals = 0.0, int(stage2_evals_total)
                        _print_stage_preview(label=preview_label, pt=pt2_arr.tolist(), wli=wli, scorer_wli=True, match_ratio=float(match_val))

                exact_sub_limit = int(STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS.get(int(tier.columns), STAGE2_EXACT_SUB_CANDIDATES))
                pass1_top_tails = int(STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS.get(int(tier.columns), STAGE2_EXACT_PASS1_TOP_TAILS))
                hybrid_sub_limit = int(
                    STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS.get(
                        int(tier.columns), STAGE2_HYBRID_SUB_CANDIDATES
                    )
                )
                if int(tier.columns) <= 1:
                    identity_full_keys: List[List[int]] = []
                    identity_sub_keys: List[np.ndarray] = []
                    for sub_key in sub_candidates:
                        sub_arr = np.asarray(sub_key, dtype=np.int16).reshape(-1)
                        if sub_arr.size != int(sub_len):
                            continue
                        full_key = np.concatenate([sub_arr, np.asarray([0], dtype=np.int16)], axis=0)
                        identity_sub_keys.append(sub_arr)
                        identity_full_keys.append(full_key.astype(int).tolist())
                    if identity_full_keys:
                        pt2_batch, sc2_batch, _batch_stats = decrypt_and_score_keys_chunked(
                            cipher=full_cipher,
                            ciphertext=ct_idx,
                            keys=identity_full_keys,
                            scorer=scorer_full_runtime,
                            wli=wli,
                            chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                            require_batch=bool(REQUIRE_BATCH_SCORING),
                        )
                        for i, full_key_vals in enumerate(identity_full_keys):
                            full_key = np.asarray(full_key_vals, dtype=np.int16).reshape(-1)
                            sub_arr = np.asarray(identity_sub_keys[i], dtype=np.int16).reshape(-1)
                            pt2 = np.asarray(pt2_batch[i], dtype=np.uint8).reshape(-1)
                            m2 = base._match_ratio(pt2.tolist(), pt_idx.tolist())
                            sub_m = float(base._match_ratio(sub_arr.tolist(), true_sub.tolist()))
                            tail_m = 1.0
                            sc2 = float(sc2_batch[i]) if i < int(sc2_batch.size) else float("nan")
                            stage2_evals_total += 1
                            stages.append(
                                dict(
                                    tier=tier.name,
                                    text_id=int(text_id),
                                    key_seed=int(key_seed),
                                    stage=f"stage2_identity_attempt_{i+1}",
                                    score=sc2,
                                    match_ratio=float(m2),
                                    sub_key_match=float(sub_m),
                                    tail_key_match=float(tail_m),
                                    seconds=0.0,
                                    evals=0,
                                )
                            )
                            _consider_stage2_candidate(
                                full_key_arr=full_key,
                                pt2_arr=pt2,
                                match_val=float(m2),
                                score_val=float(sc2),
                                preview_label=f"stage2_identity_best_{i+1}",
                                sub_key_match=float(sub_m),
                                tail_key_match=float(tail_m),
                            )
                elif int(tier.columns) <= int(STAGE2_EXACT_MAX_COLUMNS):
                    exact_subs = sub_candidates[: max(1, int(exact_sub_limit))]
                    exact_early_stop = False
                    for i, sub_key in enumerate(exact_subs):
                        sub_arr = np.asarray(sub_key, dtype=np.int16)
                        sub_m = float(base._match_ratio(sub_arr.tolist(), true_sub.tolist()))
                        pass1_evals = 0
                        pass2_evals = 0
                        shortlist_tails: List[Tuple[int, ...]] = []
                        all_tails: List[Tuple[int, ...]] = [
                            tuple(int(x) for x in tail) for tail in permutations(range(int(tier.columns)))
                        ]

                        if bool(STAGE2_EXACT_TWO_PASS) and scorer_stage2_fast_runtime is not None:
                            pass1_ranked: List[Tuple[float, Tuple[int, ...]]] = []
                            for tail_chunk in _chunk_sequence(all_tails, int(BATCH_EVAL_CHUNK_SIZE)):
                                eval_keys = [
                                    np.concatenate([sub_arr, np.asarray(tail, dtype=np.int16)], axis=0).astype(int).tolist()
                                    for tail in tail_chunk
                                ]
                                pt_block, fast_block, _batch_stats = decrypt_and_score_keys_chunked(
                                    cipher=full_cipher,
                                    ciphertext=ct_idx,
                                    keys=eval_keys,
                                    scorer=scorer_stage2_fast_runtime,
                                    wli=None,
                                    chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                                    require_batch=bool(REQUIRE_BATCH_SCORING),
                                )
                                pass1_evals += int(len(eval_keys))
                                stage2_evals_total += int(len(eval_keys))
                                for j, tail in enumerate(tail_chunk):
                                    pt2 = np.asarray(pt_block[j], dtype=np.uint8).reshape(-1)
                                    fast_sc = float(fast_block[j]) if j < int(fast_block.size) else float("nan")
                                    pass1_ranked.append((fast_sc, tuple(int(x) for x in tail)))
                                    if bool(STAGE2_EXACT_EARLY_SOLVE_BREAK):
                                        m2 = base._match_ratio(pt2.tolist(), pt_idx.tolist())
                                        tail_m = float(base._match_ratio(list(tail), true_tail.tolist()))
                                        if float(m2) >= float(SOLVE_MATCH_THRESHOLD):
                                            full_key = np.asarray(eval_keys[j], dtype=np.int16).reshape(-1)
                                            full_scores, _score_stats = score_plaintexts_chunked(
                                                scorer=scorer_full_runtime,
                                                plaintexts=[pt2],
                                                wli=wli,
                                                chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                                                require_batch=bool(REQUIRE_BATCH_SCORING),
                                            )
                                            sc2 = float(full_scores[0]) if full_scores.size > 0 else float("nan")
                                            pass2_evals += 1
                                            stage2_evals_total += 1
                                            _consider_stage2_candidate(
                                                full_key_arr=full_key,
                                                pt2_arr=pt2,
                                                match_val=float(m2),
                                                score_val=float(sc2),
                                                preview_label=f"stage2_exact_best_sub{i+1}",
                                                sub_key_match=float(sub_m),
                                                tail_key_match=float(tail_m),
                                            )
                                            exact_early_stop = True
                                            break
                                if exact_early_stop:
                                    break
                            if not exact_early_stop:
                                pass1_ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
                                k_short = min(int(pass1_top_tails), len(pass1_ranked))
                                shortlist_tails = [tail for _s, tail in pass1_ranked[:k_short]]
                        else:
                            shortlist_tails = list(all_tails)

                        if not exact_early_stop:
                            for tail_chunk in _chunk_sequence(shortlist_tails, int(BATCH_EVAL_CHUNK_SIZE)):
                                eval_keys = [
                                    np.concatenate([sub_arr, np.asarray(tail, dtype=np.int16)], axis=0).astype(int).tolist()
                                    for tail in tail_chunk
                                ]
                                pt_block, sc_block, _batch_stats = decrypt_and_score_keys_chunked(
                                    cipher=full_cipher,
                                    ciphertext=ct_idx,
                                    keys=eval_keys,
                                    scorer=scorer_full_runtime,
                                    wli=wli,
                                    chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                                    require_batch=bool(REQUIRE_BATCH_SCORING),
                                )
                                pass2_evals += int(len(eval_keys))
                                stage2_evals_total += int(len(eval_keys))
                                for j, tail in enumerate(tail_chunk):
                                    full_key = np.asarray(eval_keys[j], dtype=np.int16).reshape(-1)
                                    pt2 = np.asarray(pt_block[j], dtype=np.uint8).reshape(-1)
                                    m2 = base._match_ratio(pt2.tolist(), pt_idx.tolist())
                                    tail_m = float(base._match_ratio(list(tail), true_tail.tolist()))
                                    sc2 = float(sc_block[j]) if j < int(sc_block.size) else float("nan")
                                    _consider_stage2_candidate(
                                        full_key_arr=full_key,
                                        pt2_arr=pt2,
                                        match_val=float(m2),
                                        score_val=float(sc2),
                                        preview_label=f"stage2_exact_best_sub{i+1}",
                                        sub_key_match=float(sub_m),
                                        tail_key_match=float(tail_m),
                                    )
                                    if bool(STAGE2_EXACT_EARLY_SOLVE_BREAK) and float(m2) >= float(SOLVE_MATCH_THRESHOLD):
                                        exact_early_stop = True
                                        break
                                if exact_early_stop:
                                    break
                        stages.append(
                            dict(
                                tier=tier.name,
                                text_id=int(text_id),
                                key_seed=int(key_seed),
                                stage=f"stage2_exact_attempt_{i+1}",
                                score=float(best2_score),
                                match_ratio=float(best2_match),
                                sub_key_match=float(best2_sub_key_match),
                                tail_key_match=float(best2_tail_key_match),
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
                        f"[colsub] stage2-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"mode=exact best_match={float(best2_match):.3f} best_score={float(best2_score):.6f} "
                        f"best_sub_key_match={float(best2_sub_key_match) if np.isfinite(best2_sub_key_match) else float('nan'):.3f} "
                        f"best_tail_key_match={float(best2_tail_key_match) if np.isfinite(best2_tail_key_match) else float('nan'):.3f} "
                        f"evals={int(stage2_evals_total)}",
                        flush=True,
                    )
                else:
                    hybrid_subs = sub_candidates[: max(1, int(hybrid_sub_limit))]
                    for i, sub_key in enumerate(hybrid_subs):
                        t_s2 = time.time()
                        inter = sub_cipher.decrypt_single(ciphertext=ct_idx, key=np.asarray(sub_key, dtype=np.int16))
                        solver_stage2_cfg = dict(SOLVER_STAGE2)
                        solver_stage2_cfg["seed"] = int(solver_stage2_cfg.get("seed", 2026)) + int(search_seed_shift) + 131 * int(i)
                        tail_total = int(
                            STAGE2_TAIL_SEEDS_TOTAL_BY_COLUMNS.get(
                                int(tier.columns), STAGE2_TAIL_SEEDS_TOTAL
                            )
                        )
                        tail_structured_swaps = int(
                            STAGE2_TAIL_STRUCTURED_SWAPS_BY_COLUMNS.get(
                                int(tier.columns), STAGE2_TAIL_STRUCTURED_SWAPS
                            )
                        )
                        tail_random = int(
                            max(
                                1,
                                min(
                                    int(tail_total),
                                    round(float(tail_total) * float(STAGE2_TAIL_RANDOM_FRACTION)),
                                ),
                            )
                        )
                        tail_seeds = make_tail_seed_pool(
                            columns=int(tier.columns),
                            seed=int(solver_stage2_cfg.get("seed", 0)),
                            total_seeds=int(tail_total),
                            structured_swaps=int(tail_structured_swaps),
                            random_seeds=int(tail_random),
                            max_exact_columns=int(STAGE2_EXACT_MAX_COLUMNS),
                        )
                        sol2 = run(
                            text=np.asarray(inter, dtype=np.uint8).tolist(),
                            cipher=by_name.cipher("columnar", key_length=tier.columns),
                            key=KeySpec.permutation(len=tier.columns),
                            solver=SolverSpec.hybrid(**solver_stage2_cfg),
                            scorer_params=scorer_full,
                            wli_data=wli,
                            encoding_dir=direction,
                            telemetry_on=True,
                            force_no_wli=False,
                            initial_keys=tail_seeds,
                        )
                        dt2 = float(time.time() - t_s2)
                        ev2 = int((getattr(sol2, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
                        stage2_evals_total += int(ev2)
                        col_key = np.asarray(getattr(sol2, "key", []) or [], dtype=np.int16).reshape(-1)
                        if col_key.size != int(tier.columns):
                            continue
                        full_key = np.concatenate([np.asarray(sub_key, dtype=np.int16), col_key], axis=0)
                        pt2 = np.asarray(full_cipher.decrypt_single(ciphertext=ct_idx, key=full_key), dtype=np.uint8).reshape(-1)
                        m2 = base._match_ratio(pt2.tolist(), pt_idx.tolist())
                        sub_m = float(
                            base._match_ratio(
                                np.asarray(sub_key, dtype=np.int16).tolist(),
                                true_sub.tolist(),
                            )
                        )
                        tail_m = float(base._match_ratio(col_key.astype(int).tolist(), true_tail.tolist()))
                        _judge_scores, _judge_stats = score_plaintexts_chunked(
                            scorer=scorer_full_runtime,
                            plaintexts=[pt2],
                            wli=wli,
                            chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                            require_batch=bool(REQUIRE_BATCH_SCORING),
                        )
                        sc2 = float(_judge_scores[0]) if _judge_scores.size > 0 else float("nan")
                        stage2_evals_total += 1
                        stages.append(
                            dict(
                                tier=tier.name,
                                text_id=int(text_id),
                                key_seed=int(key_seed),
                                stage=f"stage2_col_attempt_{i+1}",
                                score=sc2,
                                match_ratio=float(m2),
                                sub_key_match=float(sub_m),
                                tail_key_match=float(tail_m),
                                seconds=round(dt2, 3),
                                evals=ev2,
                            )
                        )
                        _consider_stage2_candidate(
                            full_key_arr=full_key,
                            pt2_arr=pt2,
                            match_val=float(m2),
                            score_val=float(sc2),
                            preview_label=f"stage2_best_attempt_{i+1}",
                            sub_key_match=float(sub_m),
                            tail_key_match=float(tail_m),
                        )
                    print(
                        f"[colsub] stage2-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"mode=hybrid best_match={float(best2_match):.3f} best_score={float(best2_score):.6f} "
                        f"best_sub_key_match={float(best2_sub_key_match) if np.isfinite(best2_sub_key_match) else float('nan'):.3f} "
                        f"best_tail_key_match={float(best2_tail_key_match) if np.isfinite(best2_tail_key_match) else float('nan'):.3f} "
                        f"evals={int(stage2_evals_total)} sub_limit={int(hybrid_sub_limit)}",
                        flush=True,
                    )

                stage2_all = list(stage2_archive.values())
                stage2_ranked_by_score = sorted(
                    stage2_all,
                    key=lambda e: (float(e.get("score", float("-inf"))), float(e.get("match", float("-inf")))),
                    reverse=True,
                )
                stage2_ranked_by_match = sorted(
                    stage2_all,
                    key=lambda e: (float(e.get("match", float("-inf"))), float(e.get("score", float("-inf")))),
                    reverse=True,
                )
                stage2_ranked = stage2_ranked_by_score[: int(stage2_archive_keep)]
                # Promotion must come from the pruned "kept" pool, not the full archive.
                stage2_kept_by_score = list(stage2_ranked)
                stage2_kept_by_match = sorted(
                    stage2_ranked,
                    key=lambda e: (
                        float(e.get("match", float("-inf"))),
                        float(e.get("score", float("-inf"))),
                    ),
                    reverse=True,
                )

                stage2_promoted: List[Dict[str, Any]] = []
                stage2_promoted_seen: set[Tuple[int, ...]] = set()

                def _push_promoted(entry: Dict[str, Any]) -> None:
                    key_vals = tuple(int(x) for x in entry.get("key", []))
                    if (not key_vals) or (key_vals in stage2_promoted_seen):
                        return
                    stage2_promoted_seen.add(key_vals)
                    stage2_promoted.append(entry)

                max_rank = max(len(stage2_kept_by_score), len(stage2_kept_by_match))
                for r in range(max_rank):
                    if len(stage2_promoted) >= int(stage2_promote_top):
                        break
                    if r < len(stage2_kept_by_score):
                        _push_promoted(stage2_kept_by_score[r])
                    if len(stage2_promoted) >= int(stage2_promote_top):
                        break
                    if r < len(stage2_kept_by_match):
                        _push_promoted(stage2_kept_by_match[r])

                if (best2_key is None) and stage2_kept_by_score:
                    top = stage2_kept_by_score[0]
                    best2_key = list(map(int, top.get("key", [])))
                    best2_pt = list(map(int, top.get("plaintext", [])))
                    best2_preview = str(top.get("preview", best2_preview))
                    best2_score = float(top.get("score", best2_score))
                    best2_match = float(top.get("match", best2_match))

                if stage2_kept_by_score:
                    stage2_entry_score = float(stage2_kept_by_score[0].get("score", float("-inf")))
                elif np.isfinite(best2_score):
                    stage2_entry_score = float(best2_score)
                print(
                    f"[colsub] stage2-archive tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"entries={len(stage2_archive)} kept={len(stage2_ranked)} promoted={len(stage2_promoted)} "
                    f"top_score={float(stage2_entry_score) if np.isfinite(stage2_entry_score) else float('nan'):.6f} "
                    f"top_match={float(best2_match) if np.isfinite(best2_match) else float('nan'):.3f}",
                    flush=True,
                )

                best_preview = str(best2_preview)

                # Stage 3
                best3_match, best3_score, stop_reason = float("nan"), float("nan"), "completed_pipeline"
                best3_key: List[int] | None = None
                best3_pt: List[int] | None = None
                best3_sub_key_match = float("nan")
                best3_tail_key_match = float("nan")
                ev3 = 0
                stage2_gap_to_oracle = float("nan")
                stage3_band_name = ""
                stage3_entry_mode = "full"
                stage3_full_entry_score = _stage3_full_entry_score(int(tier.columns))
                stage3_probe_entry_score = _stage3_probe_entry_score(int(tier.columns))
                if np.isfinite(best2_match) and best2_match >= SOLVE_MATCH_THRESHOLD:
                    stop_reason = "solved_stage2"
                elif best2_key is not None:
                    t_s3 = time.time()
                    init3_n = int(STAGE3_INITIAL_KEYS_BY_COLUMNS.get(int(tier.columns), STAGE3_INITIAL_KEYS))
                    promoted_keys: List[List[int]] = []
                    seen_promoted: set[Tuple[int, ...]] = set()
                    for ent in stage2_promoted:
                        k = list(map(int, ent.get("key", [])))
                        if len(k) != int(key_len):
                            continue
                        kt = tuple(k)
                        if kt in seen_promoted:
                            continue
                        seen_promoted.add(kt)
                        promoted_keys.append(k)
                    if not promoted_keys:
                        promoted_keys = [list(map(int, best2_key))]

                    per_seed = max(1, int(np.ceil(float(init3_n) / float(len(promoted_keys)))))
                    init3_all: List[List[int]] = []
                    for j, seed_key in enumerate(promoted_keys):
                        init3_all.extend(
                            _mutate_full_key(
                                seed_key,
                                period=tier.period,
                                columns=tier.columns,
                                seed=7000 + int(key_seed) + int(search_seed_shift) + 97 * int(j),
                                n=per_seed,
                            )
                        )
                    init3: List[List[int]] = []
                    seen_init: set[Tuple[int, ...]] = set()
                    for k in init3_all:
                        kt = tuple(int(x) for x in k)
                        if kt in seen_init:
                            continue
                        seen_init.add(kt)
                        init3.append(list(map(int, k)))
                        if len(init3) >= int(init3_n):
                            break
                    solver_stage3_cfg = dict(SOLVER_STAGE3)
                    solver_stage3_cfg["seed"] = int(solver_stage3_cfg.get("seed", 2026)) + int(search_seed_shift)
                    stage2_gate_score = float(stage2_entry_score if np.isfinite(stage2_entry_score) else best2_score)
                    if np.isfinite(stage2_gate_score) and np.isfinite(oracle_s23):
                        stage2_gap_to_oracle = max(0.0, float(oracle_s23) - float(stage2_gate_score))
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
                    hard_far_override_applied = False
                    if (
                        str(stage3_band_name) == "far"
                        and int(tier.columns) in STAGE3_HARD_COLUMNS
                    ):
                        solver_stage3_cfg.update(
                            steps=int(STAGE3_HARD_FAR_OVERRIDE.get("steps", solver_stage3_cfg.get("steps", 0))),
                            restarts=int(
                                STAGE3_HARD_FAR_OVERRIDE.get("restarts", solver_stage3_cfg.get("restarts", 0))
                            ),
                            plateau_rounds=int(
                                STAGE3_HARD_FAR_OVERRIDE.get(
                                    "plateau_rounds",
                                    solver_stage3_cfg.get("plateau_rounds", 0),
                                )
                            ),
                            col_batch=int(
                                STAGE3_HARD_FAR_OVERRIDE.get("col_batch", solver_stage3_cfg.get("col_batch", 0))
                            ),
                        )
                        hard_far_override_applied = True

                    entry_score = float(stage2_gate_score) if np.isfinite(stage2_gate_score) else float("-inf")
                    if stage3_full_entry_score is None and stage3_probe_entry_score is None:
                        stage3_entry_mode = "full"
                    else:
                        full_gate = float(stage3_full_entry_score) if stage3_full_entry_score is not None else float("inf")
                        probe_gate = float(stage3_probe_entry_score) if stage3_probe_entry_score is not None else float(full_gate)
                        if entry_score >= full_gate:
                            stage3_entry_mode = "full"
                        elif entry_score >= probe_gate:
                            stage3_entry_mode = "medium"
                        else:
                            stage3_entry_mode = "probe"

                    if stage3_entry_mode == "medium":
                        solver_stage3_cfg.update(
                            steps=max(1200, min(int(solver_stage3_cfg.get("steps", 0)), 1800)),
                            restarts=1,
                            plateau_rounds=min(int(solver_stage3_cfg.get("plateau_rounds", 0)), 220),
                            col_batch=min(int(solver_stage3_cfg.get("col_batch", 0)), 96),
                            inner_batch=min(int(solver_stage3_cfg.get("inner_batch", 0)), 128),
                        )
                    elif stage3_entry_mode == "probe":
                        solver_stage3_cfg.update(
                            steps=max(700, min(int(solver_stage3_cfg.get("steps", 0)), 900)),
                            restarts=1,
                            plateau_rounds=min(int(solver_stage3_cfg.get("plateau_rounds", 0)), 140),
                            col_batch=min(int(solver_stage3_cfg.get("col_batch", 0)), 96),
                            inner_batch=min(int(solver_stage3_cfg.get("inner_batch", 0)), 128),
                        )

                    if STAGE3_USE_ORACLE_GUIDE_STOP:
                        relax = max(0.0, min(0.95, float(STAGE3_ORACLE_STOP_RELAX_FRACTION)))
                        s3_stop = float(oracle_s23) - (abs(float(oracle_s23)) * relax) + float(STAGE3_ORACLE_STOP_MARGIN)
                        s3_stop = min(0.999999, float(s3_stop))
                        solver_stage3_cfg["stop_score"] = float(s3_stop)
                    print(
                        f"[colsub] stage3-stop tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"band={stage3_band_name} entry_mode={stage3_entry_mode} "
                        f"entry_score={entry_score:.6f} "
                        f"entry_full={stage3_full_entry_score if stage3_full_entry_score is not None else 'none'} "
                        f"entry_probe={stage3_probe_entry_score if stage3_probe_entry_score is not None else 'none'} "
                        f"gap_to_oracle={stage2_gap_to_oracle:.6f} "
                        f"oracle_relax={float(STAGE3_ORACLE_STOP_RELAX_FRACTION):.3f} "
                        f"init_keys={len(init3)} "
                        f"promoted_keys={len(promoted_keys)} "
                        f"steps={solver_stage3_cfg.get('steps')} restarts={solver_stage3_cfg.get('restarts')} "
                        f"col_batch={solver_stage3_cfg.get('col_batch')} inner_batch={solver_stage3_cfg.get('inner_batch')} "
                        f"stop_score={solver_stage3_cfg.get('stop_score', 'none')} "
                        f"hard_far_override={int(bool(hard_far_override_applied))} "
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
                    try:
                        k3 = np.asarray(getattr(sol3, "key", []) or [], dtype=np.int16).reshape(-1)
                        if k3.size == int(key_len):
                            best3_key = k3.astype(int).tolist()
                            best3_sub_key_match = float(
                                base._match_ratio(
                                    k3[:sub_len].astype(int).tolist(), true_sub.tolist()
                                )
                            )
                            best3_tail_key_match = float(
                                base._match_ratio(
                                    k3[sub_len : sub_len + int(tier.columns)].astype(int).tolist(),
                                    true_tail.tolist(),
                                )
                            )
                    except Exception:
                        best3_key = None
                    if pt3.size > 0:
                        best3_pt = pt3.astype(int).tolist()
                    stages.append(
                        dict(
                            tier=tier.name,
                            text_id=int(text_id),
                            key_seed=int(key_seed),
                            stage="stage3_full_refine",
                            score=best3_score,
                            match_ratio=float(best3_match),
                            sub_key_match=float(best3_sub_key_match),
                            tail_key_match=float(best3_tail_key_match),
                            seconds=round(dt3, 3),
                            evals=ev3,
                            stage3_band=stage3_band_name,
                            stage3_entry_mode=str(stage3_entry_mode),
                            stage2_gap_to_oracle=float(stage2_gap_to_oracle),
                            stage3_entry_full_score=(
                                float(stage3_full_entry_score) if stage3_full_entry_score is not None else np.nan
                            ),
                            stage3_entry_probe_score=(
                                float(stage3_probe_entry_score) if stage3_probe_entry_score is not None else np.nan
                            ),
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
                        # col_then_sub has one post-Stage2 improvement boundary (Stage2 -> Stage3).
                        # Respect stall-stage-limit semantics without overstating available boundaries.
                        stop_reason = "stalled_no_improve" if int(STALL_STAGE_LIMIT) <= 1 else "unsolved"
                    print(
                        f"[colsub] stage3-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"band={stage3_band_name} entry_mode={stage3_entry_mode} "
                        f"match={float(best3_match):.3f} score={float(best3_score):.6f} "
                        f"sub_key_match={float(best3_sub_key_match) if np.isfinite(best3_sub_key_match) else float('nan'):.3f} "
                        f"tail_key_match={float(best3_tail_key_match) if np.isfinite(best3_tail_key_match) else float('nan'):.3f} "
                        f"evals={ev3} stop={stop_reason}",
                        flush=True,
                    )

                best_match = max(float(best2_match if np.isfinite(best2_match) else 0.0), float(best3_match if np.isfinite(best3_match) else 0.0))
                best_stage = "stage3_full_refine" if np.isfinite(best3_match) and best3_match >= best2_match else "stage2_search"
                best_key_idx: List[int] | None = best3_key if best_stage == "stage3_full_refine" else best2_key
                best_plaintext_idx: List[int] | None = best3_pt if best_stage == "stage3_full_refine" else best2_pt
                best_objective_score = float(best3_score if best_stage == "stage3_full_refine" else best2_score)
                status = "solved" if best_match >= SOLVE_MATCH_THRESHOLD else ("stalled" if stop_reason == "stalled_no_improve" else "unsolved")
                dt_i = float(time.time() - t0_i)
                total_evals = int(ev1 + int(stage2_evals_total) + int(ev3))
                instances.append(dict(
                    tier=tier.name, period=tier.period, columns=tier.columns, length=tier.length, text_id=int(text_id),
                    key_seed=int(key_seed), offset_hint=int(off), offset_used=int(offset_used), status=status, stop_reason=stop_reason,
                    solve_threshold=float(SOLVE_MATCH_THRESHOLD), best_stage=best_stage, best_match_ratio=float(best_match),
                    best_objective_score=float(best_objective_score),
                    stage1_sub_key_match=float(sub_key_match),
                    stage2_match_ratio=float(best2_match if np.isfinite(best2_match) else np.nan),
                    stage2_sub_key_match=float(best2_sub_key_match),
                    stage2_tail_key_match=float(best2_tail_key_match),
                    stage3_match_ratio=float(best3_match if np.isfinite(best3_match) else np.nan),
                    stage3_sub_key_match=float(best3_sub_key_match),
                    stage3_tail_key_match=float(best3_tail_key_match),
                    stage2_gap_to_oracle=float(stage2_gap_to_oracle),
                    stage3_entry_mode=str(stage3_entry_mode),
                    stage3_entry_full_score=(
                        float(stage3_full_entry_score) if stage3_full_entry_score is not None else np.nan
                    ),
                    stage3_entry_probe_score=(
                        float(stage3_probe_entry_score) if stage3_probe_entry_score is not None else np.nan
                    ),
                    stage3_band=str(stage3_band_name),
                    retry_attempt=int(repeat_attempt),
                    search_seed_offset=int(search_seed_offset),
                    config_fingerprint=str(config_fingerprint),
                    total_seconds=round(dt_i, 3), total_evals=total_evals, preview_best_latin=best_preview,
                ))
                inst_row = dict(instances[-1])
                stage_rows_instance = [
                    dict(s)
                    for s in stages
                    if s.get("tier") == tier.name
                    and int(s.get("text_id", -1)) == int(text_id)
                    and int(s.get("key_seed", -1)) == int(key_seed)
                ]

                if best_match > float(best_global["match"]):
                    best_global["match"] = float(best_match)
                    best_global["tier"] = str(tier.name)
                    best_global["text_id"] = int(text_id)
                    best_global["key_seed"] = int(key_seed)
                    best_global["stage"] = str(best_stage)
                    best_global["preview"] = str(best_preview)

                # Checkpoint per-instance so completed solves survive interruption/restarts.
                summary_ckpt = _build_summary(TIERS, instances)
                write_pipeline_snapshot_files(
                    run_dir=run_dir,
                    instances=instances,
                    stages=stages,
                    summary=summary_ckpt,
                )

                artifact_payload = dict(
                    profile=PROFILE,
                    mode=PIPELINE_RUN_MODE,
                    config_fingerprint=str(config_fingerprint),
                    instance=inst_row,
                    stages=stage_rows_instance,
                    io=dict(
                        ciphertext_idx=_to_int_list(ct_idx),
                        target_plaintext_idx=_to_int_list(pt_idx),
                        final_best_key_idx=(
                            list(map(int, best_key_idx))
                            if best_key_idx is not None
                            else []
                        ),
                        final_best_plaintext_idx=(
                            list(map(int, best_plaintext_idx))
                            if best_plaintext_idx is not None
                            else []
                        ),
                        true_key_idx=_to_int_list(key_true),
                        wli_data=[list(map(int, span)) for span in wli],
                    ),
                )
                artifact_name = (
                    f"{tier.name}__text{int(text_id)}__seed{int(key_seed)}.json"
                )
                final_dir.mkdir(parents=True, exist_ok=True)
                write_json(final_dir / artifact_name, artifact_payload)

                hist_row = dict(
                    timestamp_utc=datetime.now(timezone.utc).isoformat(),
                    run_id=run_dir.name,
                    profile_id=PROFILE,
                    fixture_id=inst_row["tier"],
                    text_id=inst_row["text_id"],
                    key_seed=inst_row["key_seed"],
                    period=inst_row["period"],
                    columns=inst_row["columns"],
                    length=inst_row["length"],
                    status=inst_row["status"],
                    solve_threshold=inst_row["solve_threshold"],
                    best_match_ratio=inst_row["best_match_ratio"],
                    best_stage=inst_row["best_stage"],
                    stage1_sub_key_match=inst_row["stage1_sub_key_match"],
                    stage2_match_ratio=inst_row["stage2_match_ratio"],
                    stage2_sub_key_match=inst_row.get("stage2_sub_key_match", np.nan),
                    stage2_tail_key_match=inst_row.get("stage2_tail_key_match", np.nan),
                    stage3_match_ratio=inst_row["stage3_match_ratio"],
                    stage3_sub_key_match=inst_row.get("stage3_sub_key_match", np.nan),
                    stage3_tail_key_match=inst_row.get("stage3_tail_key_match", np.nan),
                    total_seconds=inst_row["total_seconds"],
                    total_evals=inst_row["total_evals"],
                    notes=(
                        f"{inst_row['stop_reason']};"
                        f"cfg={config_fingerprint};"
                        f"retry={int(repeat_attempt)};"
                        f"soff={int(search_seed_offset)}"
                    ),
                )
                _append_csv_row_common(hist, hist_row, merge_fieldnames=True)
                history_rows_written += 1

                if inst_row["status"] == "solved":
                    solved_record = dict(
                        timestamp_utc=datetime.now(timezone.utc).isoformat(),
                        run_id=run_dir.name,
                        profile=PROFILE,
                        mode=PIPELINE_RUN_MODE,
                        config=run_config,
                        instance=inst_row,
                        stages=stage_rows_instance,
                        io=dict(
                            ciphertext_idx=_to_int_list(ct_idx),
                            oracle_plaintext_idx=_to_int_list(pt_idx),
                            best_plaintext_idx=(list(best_plaintext_idx) if best_plaintext_idx is not None else None),
                            best_key_idx=(list(best_key_idx) if best_key_idx is not None else None),
                            true_key_idx=_to_int_list(key_true),
                            wli_data=[list(map(int, span)) for span in wli],
                        ),
                    )
                    solved_file = (
                        proven_dir
                        / f"{inst_row['tier']}__text{int(inst_row['text_id'])}__seed{int(inst_row['key_seed'])}.json"
                    )
                    try:
                        solved_jsonl.parent.mkdir(parents=True, exist_ok=True)
                        proven_dir.mkdir(parents=True, exist_ok=True)
                        with solved_jsonl.open("a", encoding="utf-8") as f:
                            f.write(json.dumps(solved_record, ensure_ascii=True) + "\n")
                        solved_rows_written += 1
                        write_json(solved_file, solved_record)
                        print(
                            f"[colsub] proven-solved-write tier={tier.name} text={text_id} key_seed={key_seed} "
                            f"jsonl={solved_jsonl.relative_to(root)} file={solved_file.relative_to(root)}",
                            flush=True,
                        )
                    except Exception as exc:
                        print(
                            f"[colsub] warn: proven-solved-write failed tier={tier.name} text={text_id} key_seed={key_seed} "
                            f"err={type(exc).__name__}:{exc}",
                            flush=True,
                        )

                done += 1
                elapsed = time.time() - t0_all
                eta = (elapsed / float(done)) * float(total - done) if done else 0.0
                print(f"[colsub] {done}/{total} tier={tier.name} status={status} best_match={best_match:.3f} run={base._format_seconds(dt_i)} elapsed={base._format_seconds(elapsed)} eta={base._format_seconds(eta)}", flush=True)
                if best_preview:
                    print(f"[colsub] best-instance-preview tier={tier.name} text={text_id} key_seed={key_seed} text=\"{best_preview}\"", flush=True)
                now = time.time()
                if (now - last_hb) >= float(HEARTBEAT_SECONDS):
                    print(
                        f"[colsub] heartbeat elapsed={base._format_seconds(now - t0_all)} "
                        f"done={done}/{total} "
                        f"global_best_match={float(best_global['match']):.3f} "
                        f"tier={best_global['tier']} text={best_global['text_id']} key_seed={best_global['key_seed']} "
                        f"stage={best_global['stage']} preview=\"{best_global['preview']}\"",
                        flush=True,
                    )
                    last_hb = now

    summary = _build_summary(TIERS, instances)

    write_pipeline_snapshot_files(
        run_dir=run_dir,
        instances=instances,
        stages=stages,
        summary=summary,
    )
    if instances:
        best_instance = max(
            instances,
            key=lambda r: float(r.get("best_match_ratio", float("-inf"))),
        )
        best_dir.mkdir(parents=True, exist_ok=True)
        write_json(best_dir / "best_instance.json", best_instance)
        (best_dir / "best_preview.txt").write_text(
            str(best_instance.get("preview_best_latin", "")),
            encoding="utf-8",
        )

    print(f"[colsub] completed in {base._format_seconds(time.time() - t0_all)}", flush=True)
    print(f"[colsub] reports: {run_dir.relative_to(root)}", flush=True)
    print(f"[colsub] final_artifacts: {final_dir.relative_to(root)}", flush=True)
    print(f"[colsub] best: {(best_dir / 'best_instance.json').relative_to(root)}", flush=True)
    print(f"[colsub] history: {hist.relative_to(root)} rows={history_rows_written}", flush=True)
    print(
        "[colsub] proven-solved: "
        f"{solved_jsonl.relative_to(root)} rows={solved_rows_written} files={proven_dir.relative_to(root)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
