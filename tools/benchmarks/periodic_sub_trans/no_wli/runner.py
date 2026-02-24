from __future__ import annotations

"""No-WLI staged periodic+columnar benchmark.

This benchmark keeps the same stage structure as the main pipeline benchmark and
removes all WLI dependencies so runic-like short-text tuning can be measured
with character-only models.

Default scorer schedule:
- Stage 1: A_char1 (explore)
- Stage 2: M_char12 (rerank/promote)
- Stage 3: B_char34 (deep refine)
"""

import csv
import hashlib
import json
import re
import subprocess
import sys
import time
from itertools import permutations
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

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
from rune_decrypter_prime.utils.seed_utils import make_periodic_seed_pool

from tools.benchmarks.periodic_sub_trans.common import bench_solve_periodic_columnar_kaeding as base
from tools.benchmarks.periodic_sub_trans.common.batch_eval import (
    decrypt_and_score_keys_chunked,
    score_plaintexts_chunked,
)
from tools.benchmarks.periodic_sub_trans.common.core_enums import BenchmarkOrder
from tools.benchmarks.config.no_wli_pipeline_profiles import get_no_wli_pipeline_profile
from tools.benchmarks.periodic_sub_trans.common.paths import make_flavor_run_dir


ALPHABET_SIZE = 29
ORDER = BenchmarkOrder.COL_THEN_SUB.value  # keep v1 aligned with the proven pipeline; add both orders in later variants.
PROFILE = "pipeline_no_wli_v1"
PIPELINE_RUN_MODE = "focus_p5_c1_only"  # "full" | "focus_500_nowli" | "focus_p5_c1_only" | "smoke"
ENCODING_DIR = "ltr"  # "ltr" | "rtl"
NO_WLI_PIPELINE_PROFILE_ID = "no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1"
# Previous default kept in-file for one-line A/B rollback when needed.
NO_WLI_PIPELINE_PROFILE_ID_PREVIOUS_DEFAULT = "no_wli_a1_m12_b34_stage3avg_fulltext_v1"
NO_WLI_LONGRUN3X_PROFILE_ID = "no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1"
SCORER_STAGE1_LABEL = "A_char1"
SCORER_STAGE2_LABEL = "M_char12"
SCORER_STAGE3_LABEL = "B_char34"
SCORER_IMPL = ScorerImpl.NUMPY.value  # Keep scoring/backend consistent across stages for now.
SCORER_STAGE3_IMPL_AVG_FULLTEXT = ScorerImpl.NUMPY.value  # Stability guard for AVG full-text.
BATCH_EVAL_CHUNK_SIZE = 256  # Shared chunk size for decrypt+score batching in runner-level loops.
REQUIRE_BATCH_SCORING = True  # Fail fast if scorer can't execute true batch path in perf profiles.
STAGE2_PROMOTE_BY_STAGE3_JUDGE = True  # Bridge into Stage-3 objective basin before refine.
STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE = True  # Use Stage-3 objective for entry-band selection.
REQUIRE_NO_ECDF_FOR_AVG_FULLTEXT = True  # Hard guard: avg.full_text scorers must never touch ECDF.

SOLVE_MATCH_THRESHOLD = 0.90
STALL_DELTA = 0.002
STALL_STAGE_LIMIT = 1
HEARTBEAT_SECONDS = 900
PREVIEW_CHARS = 240

TEXT_OFFSETS = [0]
KEY_SEEDS = [111]

STAGE1_SUB_CANDIDATES = 24
STAGE3_INITIAL_KEYS = 18

STAGE1_SUB_CANDIDATES_BY_COLUMNS = {1: 8, 3: 32, 5: 24, 7: 24, 10: 20, 13: 20}
STAGE3_INITIAL_KEYS_BY_COLUMNS = {1: 8, 3: 36, 5: 30, 7: 40, 10: 40, 13: 48}

STAGE2_EXACT_MAX_COLUMNS = 7
STAGE2_EXACT_SUB_CANDIDATES = 4
STAGE2_EXACT_TWO_PASS = True
STAGE2_EXACT_PASS1_TOP_TAILS = 160
STAGE2_EXACT_EARLY_SOLVE_BREAK = True
STAGE2_PASS1_PRIMARY_CHAR_WEIGHTS = {3: 0.2, 4: 0.8}
STAGE2_PASS1_FALLBACK_CHAR_WEIGHTS = {2: 1.0}
STAGE2_PASS1_DIVERSITY_MIN_HAMMING_FACTOR = 0.40
STAGE2_PASS1_DIVERSITY_MIN_FIRST_SYMBOLS = 3
STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS = {3: 24, 5: 12, 7: 12}
STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS = {3: 6, 5: 120, 7: 768}
STAGE2_HYBRID_SUB_CANDIDATES = 10
STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS = {10: 10, 13: 8}

SAVE_STAGE2_TOPK = 12
SAVE_STAGE3_TOPK = True
SAVE_STAGE3_TOPK_LIMIT = 5

STAGE1_SEED_RESTARTS = 96
STAGE1_SEED_N_BLOCKS = 18
STAGE1_SEED_TOTAL = 256
STAGE1_SEED_SWAPS = 3
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
STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS = 2

# Stage-3 dynamic budget bands (no-WLI, short text). These are deliberately modest.
STAGE3_DYNAMIC_BANDS = [
    dict(name="very_close", max_gap=0.010, steps=900, restarts=1, plateau_rounds=140, col_batch=96, inner_batch=128),
    dict(name="close", max_gap=0.030, steps=1600, restarts=1, plateau_rounds=200, col_batch=96, inner_batch=128),
    dict(name="mid", max_gap=0.080, steps=2400, restarts=2, plateau_rounds=260, col_batch=112, inner_batch=128),
    dict(name="far", max_gap=1e9, steps=3200, restarts=2, plateau_rounds=320, col_batch=112, inner_batch=128),
]

# Optional two-phase Stage-3 mode (solve-first).
STAGE3_TWO_PHASE_ENABLED = False
STAGE3_PHASEA_CFG: Dict[str, Any] = {
    "steps": 350,
    "restarts": 1,
    "inner_batch": 64,
    "col_every": 1,
    "col_batch": 64,
    "slip_every": 0,
    "slip_swaps": 0,
    "stall_slip_limit": 0,
}
STAGE3_PHASEB_CFG: Dict[str, Any] = {
    "steps": 1400,
    "inner_batch": 128,
    "col_every": 1,
    "col_batch": 96,
    "slip_every": 70,
    "stall_rounds": 160,
    "stall_slip_limit": 8,
    "slip_swaps": 28,
}
STAGE3_PHASEB_TOP_N = 8
STAGE3_PHASEB_GATE_DELTA_FLOOR = 0.008
STAGE3_PHASEB_GATE_END_GAIN_FLOOR = 0.004

# c1 fast-pass focus overrides (used to solve p5/c1 first without globally over-tuning all tiers).
STAGE3_C1_FOCUS_ENABLED = True
STAGE3_C1_INIT_KEYS = 192
STAGE3_C1_PHASEA_STEPS = 2400
STAGE3_C1_PHASEB_STEPS = 12000
STAGE3_C1_PHASEB_TOP_N = 48
STAGE3_C1_PHASEB_GATE_DELTA_FLOOR = 0.010
STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR = 0.006

_STAGE3_TWO_PHASE_ENABLED_DEFAULT = bool(STAGE3_TWO_PHASE_ENABLED)
_STAGE3_PHASEA_CFG_DEFAULT = dict(STAGE3_PHASEA_CFG)
_STAGE3_PHASEB_CFG_DEFAULT = dict(STAGE3_PHASEB_CFG)
_STAGE3_PHASEB_TOP_N_DEFAULT = int(STAGE3_PHASEB_TOP_N)
_STAGE3_PHASEB_GATE_DELTA_FLOOR_DEFAULT = float(STAGE3_PHASEB_GATE_DELTA_FLOOR)
_STAGE3_PHASEB_GATE_END_GAIN_FLOOR_DEFAULT = float(STAGE3_PHASEB_GATE_END_GAIN_FLOOR)
_STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS_DEFAULT = int(STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS)
_STAGE3_C1_FOCUS_ENABLED_DEFAULT = bool(STAGE3_C1_FOCUS_ENABLED)
_STAGE3_C1_INIT_KEYS_DEFAULT = int(STAGE3_C1_INIT_KEYS)
_STAGE3_C1_PHASEA_STEPS_DEFAULT = int(STAGE3_C1_PHASEA_STEPS)
_STAGE3_C1_PHASEB_STEPS_DEFAULT = int(STAGE3_C1_PHASEB_STEPS)
_STAGE3_C1_PHASEB_TOP_N_DEFAULT = int(STAGE3_C1_PHASEB_TOP_N)
_STAGE3_C1_PHASEB_GATE_DELTA_FLOOR_DEFAULT = float(STAGE3_C1_PHASEB_GATE_DELTA_FLOOR)
_STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR_DEFAULT = float(STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR)

# Scorers (char-only everywhere).
SCORER_STAGE1 = dict(
    objective="pct.logp.win10",
    include_char=True,
    use_word_breaks=False,
    char_weights={1: 1.0},
    wli_weights={},
    impl=SCORER_IMPL,
)
SCORER_STAGE2 = dict(
    objective="pct.logp.win10",
    include_char=True,
    use_word_breaks=False,
    char_weights={1: 0.4, 2: 0.6},
    wli_weights={},
    impl=SCORER_IMPL,
)
SCORER_FULL = dict(
    objective="pct.logp.win10",
    include_char=True,
    use_word_breaks=False,
    char_weights={3: 0.2, 4: 0.8},
    wli_weights={},
    impl=SCORER_IMPL,
)

SOLVER_STAGE1 = dict(
    steps=2600,
    restarts=2,
    inner_batch=128,
    slip_every=0,
    slip_blocks=1,
    slip_policy="stall",
    stall_rounds=250,
    stall_slip_limit=3,
    slip_swaps=24,
    stall_stop_on_limit=True,
    block_schedule="round_robin",
    col_every=0,
    col_batch=0,
    use_raw_score=False,
    raw_accept_min_delta=1e-6,
    pct_plateau_min_delta=1e-4,
    plateau_rounds=420,
    plateau_min_delta=5e-4,
    delta_window=200,
    top_k=28,
    progress_pct=5,
    print_progress=True,
    seed=2026,
    seed_restarts=96,
)

SOLVER_STAGE2 = dict(
    use_beam=True,
    beam_width=64,
    rounds=4,
    expand_mode="sample",
    sample_per_parent=40,
    top_parents_factor=0.4,
    progress_pct=10,
    print_progress=True,
    ga=dict(
        pop_size=96,
        generations=60,
        elite_frac=0.1,
        cx_frac=0.85,
        mut_prob=0.30,
        tournament_k=3,
        plateau_rounds=16,
        stop_score=1.0,
        print_progress=True,
    ),
    sa=dict(
        sa_iters=2200,
        sa_init_temp=0.95,
        sa_min_temp=1e-4,
        sa_cooling=0.997,
        plateau_rounds=240,
        local_improve_on_accept=True,
        stop_score=1.0,
        print_progress=True,
    ),
    seed=2026,
    verbose=True,
    log_interval=10,
    stop_score=1.0,
)

SOLVER_STAGE3 = dict(
    steps=3200,
    restarts=2,
    inner_batch=128,
    col_every=1,
    col_batch=128,
    slip_every=80,
    slip_blocks=1,
    slip_policy="stall",
    stall_rounds=220,
    stall_slip_limit=4,
    slip_swaps=40,
    use_raw_score=False,
    raw_accept_min_delta=1e-6,
    pct_plateau_min_delta=1e-4,
    plateau_rounds=320,
    plateau_min_delta=4e-4,
    delta_window=200,
    top_k=20,
    progress_pct=1,
    print_progress=True,
    seed=2026,
)


@dataclass(frozen=True)
class Tier:
    name: str
    period: int
    columns: int
    length: int


TIERS: List[Tier] = [
    # Default set is overridden by run-mode.
    Tier("focus_p7_c7_l452", 7, 7, 452),
]


def _apply_profile_defaults() -> None:
    """Load the named no-WLI profile and apply its deterministic defaults."""

    global PROFILE, SCORER_STAGE1_LABEL, SCORER_STAGE2_LABEL, SCORER_STAGE3_LABEL
    global SCORER_STAGE1, SCORER_STAGE2, SCORER_FULL
    global STAGE1_SUB_CANDIDATES, STAGE3_INITIAL_KEYS
    global STAGE1_SUB_CANDIDATES_BY_COLUMNS, STAGE3_INITIAL_KEYS_BY_COLUMNS
    global STAGE2_EXACT_MAX_COLUMNS, STAGE2_EXACT_SUB_CANDIDATES, STAGE2_EXACT_TWO_PASS
    global STAGE2_EXACT_PASS1_TOP_TAILS, STAGE2_EXACT_EARLY_SOLVE_BREAK
    global STAGE2_PASS1_PRIMARY_CHAR_WEIGHTS, STAGE2_PASS1_FALLBACK_CHAR_WEIGHTS
    global STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS, STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS
    global STAGE2_HYBRID_SUB_CANDIDATES, STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS
    global STAGE1_SEED_RESTARTS, STAGE1_SEED_N_BLOCKS, STAGE1_SEED_TOTAL, STAGE1_SEED_SWAPS
    global STAGE12_SCOUT_RUNS, STAGE12_ARCHIVE_KEEP, STAGE12_PROMOTE_TOP
    global STAGE1_SCOUT_STEP_SCALE, STAGE1_SCOUT_RESTART_SCALE, STAGE1_SCOUT_MIN_STEPS, STAGE1_SCOUT_MIN_RESTARTS
    global STAGE1_SCOUT_NO_IMPROVE_DELTA, STAGE1_SCOUT_NO_IMPROVE_PATIENCE, STAGE1_SCOUT_MIN_NEW_ARCHIVE, STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS
    global STAGE3_DYNAMIC_BANDS
    global SOLVER_STAGE1, SOLVER_STAGE2, SOLVER_STAGE3
    global STAGE3_TWO_PHASE_ENABLED, STAGE3_PHASEA_CFG, STAGE3_PHASEB_CFG
    global STAGE3_PHASEB_TOP_N, STAGE3_PHASEB_GATE_DELTA_FLOOR, STAGE3_PHASEB_GATE_END_GAIN_FLOOR
    global STAGE3_C1_FOCUS_ENABLED, STAGE3_C1_INIT_KEYS
    global STAGE3_C1_PHASEA_STEPS, STAGE3_C1_PHASEB_STEPS, STAGE3_C1_PHASEB_TOP_N
    global STAGE3_C1_PHASEB_GATE_DELTA_FLOOR, STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR

    profile = get_no_wli_pipeline_profile(NO_WLI_PIPELINE_PROFILE_ID)
    PROFILE = str(profile.profile_id)
    SCORER_STAGE1_LABEL = str(profile.scorer_schedule.stage1_label)
    SCORER_STAGE2_LABEL = str(profile.scorer_schedule.stage2_label)
    SCORER_STAGE3_LABEL = str(profile.scorer_schedule.stage3_label)
    SCORER_STAGE1 = profile.scorer_schedule.stage1_a.to_params()
    SCORER_STAGE2 = profile.scorer_schedule.stage2_m.to_params()
    SCORER_FULL = profile.scorer_schedule.stage3_b.to_params()
    SCORER_STAGE1["impl"] = SCORER_IMPL
    SCORER_STAGE2["impl"] = SCORER_IMPL
    SCORER_FULL["impl"] = _effective_stage3_impl(SCORER_FULL)

    STAGE1_SUB_CANDIDATES = int(profile.stage1_sub_candidates)
    STAGE3_INITIAL_KEYS = int(profile.stage3_initial_keys)
    STAGE1_SUB_CANDIDATES_BY_COLUMNS = {int(k): int(v) for k, v in profile.stage1_sub_candidates_by_columns.items()}
    STAGE3_INITIAL_KEYS_BY_COLUMNS = {int(k): int(v) for k, v in profile.stage3_initial_keys_by_columns.items()}

    STAGE2_EXACT_MAX_COLUMNS = int(profile.stage2_exact_max_columns)
    STAGE2_EXACT_SUB_CANDIDATES = int(profile.stage2_exact_sub_candidates)
    STAGE2_EXACT_TWO_PASS = bool(profile.stage2_exact_two_pass)
    STAGE2_EXACT_PASS1_TOP_TAILS = int(profile.stage2_exact_pass1_top_tails)
    STAGE2_EXACT_EARLY_SOLVE_BREAK = bool(profile.stage2_exact_early_solve_break)
    STAGE2_PASS1_PRIMARY_CHAR_WEIGHTS = {
        int(k): float(v) for k, v in profile.scorer_schedule.stage2_pass1_primary.items()
    }
    STAGE2_PASS1_FALLBACK_CHAR_WEIGHTS = {
        int(k): float(v) for k, v in profile.scorer_schedule.stage2_pass1_fallback.items()
    }
    STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS = {
        int(k): int(v) for k, v in profile.stage2_exact_sub_candidates_by_columns.items()
    }
    STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS = {
        int(k): int(v) for k, v in profile.stage2_exact_pass1_top_tails_by_columns.items()
    }
    STAGE2_HYBRID_SUB_CANDIDATES = int(profile.stage2_hybrid_sub_candidates)
    STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS = {
        int(k): int(v) for k, v in profile.stage2_hybrid_sub_candidates_by_columns.items()
    }

    STAGE1_SEED_RESTARTS = int(profile.stage1_seed_restarts)
    STAGE1_SEED_N_BLOCKS = int(profile.stage1_seed_n_blocks)
    STAGE1_SEED_TOTAL = int(profile.stage1_seed_total)
    STAGE1_SEED_SWAPS = int(profile.stage1_seed_swaps)
    STAGE12_SCOUT_RUNS = int(profile.stage12_scout_runs)
    STAGE12_ARCHIVE_KEEP = int(profile.stage12_archive_keep)
    STAGE12_PROMOTE_TOP = int(profile.stage12_promote_top)
    STAGE1_SCOUT_STEP_SCALE = float(profile.stage1_scout_step_scale)
    STAGE1_SCOUT_RESTART_SCALE = float(profile.stage1_scout_restart_scale)
    STAGE1_SCOUT_MIN_STEPS = int(profile.stage1_scout_min_steps)
    STAGE1_SCOUT_MIN_RESTARTS = int(profile.stage1_scout_min_restarts)
    STAGE1_SCOUT_NO_IMPROVE_DELTA = float(profile.stage1_scout_no_improve_delta)
    STAGE1_SCOUT_NO_IMPROVE_PATIENCE = int(profile.stage1_scout_no_improve_patience)
    STAGE1_SCOUT_MIN_NEW_ARCHIVE = int(profile.stage1_scout_min_new_archive)
    STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS = int(_STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS_DEFAULT)

    STAGE3_DYNAMIC_BANDS = [dict(x) for x in profile.stage3_dynamic_bands]
    SOLVER_STAGE1 = dict(profile.solver_stage1)
    SOLVER_STAGE2 = dict(profile.solver_stage2)
    SOLVER_STAGE3 = dict(profile.solver_stage3)
    STAGE3_TWO_PHASE_ENABLED = bool(_STAGE3_TWO_PHASE_ENABLED_DEFAULT)
    STAGE3_PHASEA_CFG = dict(_STAGE3_PHASEA_CFG_DEFAULT)
    STAGE3_PHASEB_CFG = dict(_STAGE3_PHASEB_CFG_DEFAULT)
    STAGE3_PHASEB_TOP_N = int(_STAGE3_PHASEB_TOP_N_DEFAULT)
    STAGE3_PHASEB_GATE_DELTA_FLOOR = float(_STAGE3_PHASEB_GATE_DELTA_FLOOR_DEFAULT)
    STAGE3_PHASEB_GATE_END_GAIN_FLOOR = float(_STAGE3_PHASEB_GATE_END_GAIN_FLOOR_DEFAULT)
    STAGE3_C1_FOCUS_ENABLED = bool(_STAGE3_C1_FOCUS_ENABLED_DEFAULT)
    STAGE3_C1_INIT_KEYS = int(_STAGE3_C1_INIT_KEYS_DEFAULT)
    STAGE3_C1_PHASEA_STEPS = int(_STAGE3_C1_PHASEA_STEPS_DEFAULT)
    STAGE3_C1_PHASEB_STEPS = int(_STAGE3_C1_PHASEB_STEPS_DEFAULT)
    STAGE3_C1_PHASEB_TOP_N = int(_STAGE3_C1_PHASEB_TOP_N_DEFAULT)
    STAGE3_C1_PHASEB_GATE_DELTA_FLOOR = float(_STAGE3_C1_PHASEB_GATE_DELTA_FLOOR_DEFAULT)
    STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR = float(_STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR_DEFAULT)

    if str(profile.profile_id) == NO_WLI_LONGRUN3X_PROFILE_ID:
        # Longrun profile default: safe local refinement first, then aggressive phase-B only for top-N.
        STAGE3_TWO_PHASE_ENABLED = True
        STAGE3_PHASEA_CFG = {
            "steps": 900,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
        }
        STAGE3_PHASEB_CFG = {
            "steps": 4200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 128,
            "slip_every": 70,
            "stall_rounds": 240,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
        }
        STAGE3_PHASEB_TOP_N = 16
        STAGE3_PHASEB_GATE_DELTA_FLOOR = 0.008
        STAGE3_PHASEB_GATE_END_GAIN_FLOOR = 0.004
        # Force full scout pass before early-stop can trigger.
        STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS = int(max(1, STAGE12_SCOUT_RUNS))


def _repo_root() -> Path:
    return _ROOT


def _git_short() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(_repo_root()), stderr=subprocess.DEVNULL)
        return out.decode("utf-8", errors="replace").strip() or "nogit"
    except Exception:
        return "nogit"


def _apply_run_mode() -> None:
    global PROFILE, HEARTBEAT_SECONDS, TIERS, TEXT_OFFSETS, KEY_SEEDS
    if PIPELINE_RUN_MODE == "full":
        return
    if PIPELINE_RUN_MODE == "smoke":
        PROFILE = f"{NO_WLI_PIPELINE_PROFILE_ID}__smoke"
        HEARTBEAT_SECONDS = 300
        TEXT_OFFSETS[:] = [0]
        KEY_SEEDS[:] = [111]
        TIERS[:] = [
            Tier("smoke_p7_c5_l452", 7, 5, 452),
            Tier("smoke_p9_c7_l446", 9, 7, 446),
        ]
        return
    if PIPELINE_RUN_MODE == "focus_p5_c1_only":
        PROFILE = f"{NO_WLI_PIPELINE_PROFILE_ID}__p5c1"
        HEARTBEAT_SECONDS = 900
        TEXT_OFFSETS[:] = [0]
        KEY_SEEDS[:] = [111]
        TIERS[:] = [
            Tier("focus_p5_c1_l452", 5, 1, 452),
        ]
        return
    if PIPELINE_RUN_MODE == "focus_500_nowli":
        PROFILE = f"{NO_WLI_PIPELINE_PROFILE_ID}__focus500"
        HEARTBEAT_SECONDS = 900
        TEXT_OFFSETS[:] = [0]
        KEY_SEEDS[:] = [111]
        # Curated runic-like set, explicitly starting with period-5 no-WLI tiers.
        TIERS[:] = [
            Tier("focus_p5_c1_l452", 5, 1, 452),
            Tier("focus_p5_c3_l452", 5, 3, 452),
            Tier("focus_p5_c5_l452", 5, 5, 452),
            Tier("focus_p7_c5_l452", 7, 5, 452),
            Tier("focus_p7_c7_l452", 7, 7, 452),
            Tier("focus_p8_c5_l505", 8, 5, 505),
            Tier("focus_p9_c7_l446", 9, 7, 446),
            Tier("focus_p14_c7_l452", 14, 7, 452),
            Tier("focus_p15_c7_l415", 15, 7, 415),
            Tier("focus_p18_c7_l446", 18, 7, 446),
            Tier("focus_p21_c7_l483", 21, 7, 483),
        ]
        return


def _extract_top_keys(sol: Any, *, limit: int) -> List[List[int]]:
    """Best-effort extraction of top keys from Kaeding telemetry.

    Matches the behaviour in the proven pipeline script: take telemetry top_keys
    if present, then include the final key, and dedupe.
    """
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
    """Generate lightweight local mutations around a full product-cipher key."""
    rng = np.random.default_rng(int(seed))
    base_arr = np.asarray(base_key, dtype=np.int16).copy()
    out = [base_arr.astype(int).tolist()]
    sub_len = int(period) * ALPHABET_SIZE
    while len(out) < int(n):
        k = base_arr.copy()
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


def _key_hash16(key_vals: Sequence[int]) -> str:
    arr = np.asarray(list(map(int, key_vals)), dtype=np.int16).reshape(-1)
    return hashlib.sha1(arr.tobytes()).hexdigest()[:16]


def _preview_latin(pt: Sequence[int], wli: Sequence[Sequence[int]]) -> str:
    return base._safe_preview_latin(pt, wli, limit=PREVIEW_CHARS)


def _print_stage_preview(
    *,
    label: str,
    pt: Sequence[int],
    wli: Sequence[Sequence[int]],
    match_ratio: float | None = None,
) -> None:
    txt = _preview_latin(pt, wli)
    mr_txt = ""
    if match_ratio is not None and np.isfinite(float(match_ratio)):
        mr_txt = f" match_ratio={float(match_ratio):.3f}"
    print(
        f"[pipeline_no_wli] preview {label} scorer_wli=off "
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


def _scorer_objective_summary(scorer_cfg: Dict[str, Any]) -> str:
    obj = str(scorer_cfg.get("objective", "unknown"))
    policy = scorer_cfg.get("avg_window_policy", None)
    if policy and str(policy).strip().lower() == "full_text":
        m = re.search(r"\.win(\d+)$", obj)
        win_cfg = m.group(1) if m else "na"
        if obj.startswith("avg.logp"):
            return (
                f"avg.logp (policy=full_text,span=full_text,"
                f"win_configured={win_cfg},win_effective=FULL_TEXT)"
            )
        return (
            f"{obj} (policy=full_text,span=full_text,"
            f"win_configured={win_cfg},win_effective=FULL_TEXT)"
        )
    if policy:
        return f"{obj} policy={policy}"
    return obj


def _is_avg_fulltext_scorer(scorer_cfg: Dict[str, Any]) -> bool:
    obj = str(scorer_cfg.get("objective", "")).strip().lower()
    policy = str(scorer_cfg.get("avg_window_policy", "")).strip().lower()
    return obj.startswith("avg.logp") and policy == "full_text"


def _effective_stage3_impl(scorer_cfg: Dict[str, Any]) -> str:
    if _is_avg_fulltext_scorer(scorer_cfg):
        return str(SCORER_STAGE3_IMPL_AVG_FULLTEXT)
    return str(SCORER_IMPL)


def _stage2_judge_pool_limit(
    *,
    ranked_count: int,
    archive_keep: int,
    stage3_scorer_cfg: Dict[str, Any],
) -> int:
    ranked_n = max(0, int(ranked_count))
    if ranked_n <= 0:
        return 0
    if (not bool(STAGE2_PROMOTE_BY_STAGE3_JUDGE)) and (not bool(STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE)):
        target = max(1, int(SAVE_STAGE2_TOPK))
        return max(1, min(ranked_n, target))
    if _is_avg_fulltext_scorer(stage3_scorer_cfg):
        target = max(1, int(archive_keep))
    else:
        target = max(1, int(SAVE_STAGE2_TOPK))
    return max(1, min(ranked_n, target))


def _guard_no_ecdf_usage(*, scorer_runtime: Any, scorer_cfg: Dict[str, Any], stage_label: str) -> None:
    """Fail fast if an AVG full-text scorer attempts to initialize/use ECDF."""

    if not _is_avg_fulltext_scorer(scorer_cfg):
        return
    if not bool(REQUIRE_NO_ECDF_FOR_AVG_FULLTEXT):
        return
    ecdf_attr = getattr(scorer_runtime, "_ecdf", None)
    if ecdf_attr is not None:
        raise RuntimeError(
            f"[pipeline_no_wli] ECDF guard failed: stage={stage_label} objective={scorer_cfg.get('objective')} "
            "avg_window_policy=full_text unexpectedly has initialized ECDF."
        )
    if hasattr(scorer_runtime, "_ensure_ecdf"):
        def _ecdf_forbidden(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError(
                f"[pipeline_no_wli] ECDF guard failed: stage={stage_label} objective={scorer_cfg.get('objective')} "
                "avg_window_policy=full_text attempted ECDF access."
            )

        setattr(scorer_runtime, "_ensure_ecdf", _ecdf_forbidden)


def _entry_key_tuple(entry: Dict[str, Any]) -> Tuple[int, ...]:
    key_vals = entry.get("key", [])
    if not isinstance(key_vals, list) or (not key_vals):
        return tuple()
    return tuple(int(x) for x in key_vals)


def _ensure_best_entry_in_ranked(
    *,
    ranked_entries: Sequence[Dict[str, Any]],
    best_entry: Dict[str, Any] | None,
) -> List[Dict[str, Any]]:
    out = list(ranked_entries)
    if best_entry is None:
        return out
    best_t = _entry_key_tuple(best_entry)
    if not best_t:
        return out
    ranked_key_set = {_entry_key_tuple(ent) for ent in out}
    if best_t not in ranked_key_set:
        out.insert(0, best_entry)
    return out


def _ensure_best_entry_in_promoted(
    *,
    promoted_entries: Sequence[Dict[str, Any]],
    best_entry: Dict[str, Any] | None,
    promote_top: int,
) -> Tuple[List[Dict[str, Any]], bool]:
    out = list(promoted_entries)
    if best_entry is None:
        return out, False
    best_t = _entry_key_tuple(best_entry)
    if not best_t:
        return out, False
    promoted_key_set = {_entry_key_tuple(ent) for ent in out}
    if best_t in promoted_key_set:
        return out, True
    top_n = int(max(1, promote_top))
    if len(out) >= top_n:
        out = out[: top_n - 1]
    out.append(best_entry)
    return out, True


def _build_stage3_promoted_keys(
    *,
    promoted_entries: Sequence[Dict[str, Any]],
    best_key: Sequence[int] | None,
    key_len: int,
) -> List[List[int]]:
    out: List[List[int]] = []
    seen: set[Tuple[int, ...]] = set()
    if best_key is not None:
        best_list = [int(x) for x in best_key]
        if len(best_list) == int(key_len):
            best_t = tuple(best_list)
            if best_t not in seen:
                seen.add(best_t)
                out.append(best_list)
    for ent in promoted_entries:
        key_vals = ent.get("key", [])
        if not isinstance(key_vals, list):
            continue
        k = [int(x) for x in key_vals]
        if len(k) != int(key_len):
            continue
        kt = tuple(k)
        if kt in seen:
            continue
        seen.add(kt)
        out.append(k)
    return out


_apply_profile_defaults()


def _tail_hamming(a: Sequence[int], b: Sequence[int]) -> int:
    return int(sum(1 for x, y in zip(a, b) if int(x) != int(y)))


def _tail_diversity_metrics(tails: List[Tuple[int, ...]], *, columns: int) -> Dict[str, float]:
    if not tails:
        return dict(unique_first=0.0, mean_hamming=0.0)
    uniq_first = float(len({int(t[0]) for t in tails if len(t) > 0}))
    if len(tails) < 2:
        return dict(unique_first=uniq_first, mean_hamming=0.0)
    total = 0
    count = 0
    for i in range(len(tails)):
        ti = tails[i]
        for j in range(i + 1, len(tails)):
            total += _tail_hamming(ti, tails[j])
            count += 1
    mean_h = float(total / max(1, count))
    return dict(unique_first=uniq_first, mean_hamming=mean_h)


def _tail_diversity_collapsed(tails: List[Tuple[int, ...]], *, columns: int) -> Tuple[bool, Dict[str, float]]:
    metrics = _tail_diversity_metrics(tails, columns=columns)
    min_first = float(min(max(1, int(STAGE2_PASS1_DIVERSITY_MIN_FIRST_SYMBOLS)), int(columns)))
    min_hamming = float(max(1.0, float(STAGE2_PASS1_DIVERSITY_MIN_HAMMING_FACTOR) * float(columns)))
    collapsed = bool(metrics["unique_first"] < min_first or metrics["mean_hamming"] < min_hamming)
    metrics["min_first_required"] = float(min_first)
    metrics["min_hamming_required"] = float(min_hamming)
    return collapsed, metrics


def _select_stage3_band(gap_to_oracle: float) -> Dict[str, Any]:
    gap = float(gap_to_oracle)
    for band in STAGE3_DYNAMIC_BANDS:
        if gap <= float(band.get("max_gap", 1e9)):
            return dict(band)
    return dict(STAGE3_DYNAMIC_BANDS[-1])


def _oracle_score_for_stage(
    *,
    pt_idx: np.ndarray,
    cipher_cfg: CipherConfig,
    scorer_params: Dict[str, Any],
) -> Tuple[float, float, str]:
    s_cfg = ScoringConfig(**scorer_params)
    scorer = build_scorer(cipher_cfg, s_cfg)
    # no-WLI: always score without WLI arg.
    score, raw = scorer.score_with_raw(pt_idx, None)
    return float(score), float(raw), _scorer_objective_summary(scorer_params)


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
    direction_txt = str(ENCODING_DIR).strip().lower()
    if direction_txt == "ltr":
        direction = Direction.LTR
    elif direction_txt == "rtl":
        direction = Direction.RTL
    else:
        raise ValueError(f"Unsupported ENCODING_DIR={ENCODING_DIR!r}; expected 'ltr' or 'rtl'")
    print("[pipeline_no_wli] bootstrap: checking char LM assets...", flush=True)
    base._require_assets(direction, ns=(1, 3, 4), need_wli=False)
    pt_base, wli_base = base._encode_long_plaintext(direction)

    root = _repo_root()
    run_dir = make_flavor_run_dir(flavor="no_wli", run_prefix="bench_solve_pipeline_no_wli")
    best_dir = run_dir / "best"
    best_dir.mkdir(parents=True, exist_ok=True)
    final_dir = run_dir / "final_instances"
    final_dir.mkdir(parents=True, exist_ok=True)

    run_config = dict(
        profile=PROFILE,
        mode=PIPELINE_RUN_MODE,
        direction=direction.value,
        order=ORDER,
        alphabet_size=int(ALPHABET_SIZE),
        threshold=float(SOLVE_MATCH_THRESHOLD),
        stall_delta=float(STALL_DELTA),
        stall_stage_limit=int(STALL_STAGE_LIMIT),
        text_offsets=list(map(int, TEXT_OFFSETS)),
        key_seeds=list(map(int, KEY_SEEDS)),
        artifacts=dict(
            final_best=True,
            stage2_topk=int(SAVE_STAGE2_TOPK),
            stage3_topk_enabled=bool(SAVE_STAGE3_TOPK),
            stage3_topk=int(SAVE_STAGE3_TOPK_LIMIT),
        ),
        scorer_schedule=dict(
            stage1=str(SCORER_STAGE1_LABEL),
            stage2=str(SCORER_STAGE2_LABEL),
            stage3=str(SCORER_STAGE3_LABEL),
        ),
        stage1=dict(
            scorer=dict(SCORER_STAGE1),
            solver=dict(SOLVER_STAGE1),
            seed_restarts=int(STAGE1_SEED_RESTARTS),
            seed_plan=dict(
                blocks=int(STAGE1_SEED_N_BLOCKS),
                total=int(STAGE1_SEED_TOTAL),
                swaps=int(STAGE1_SEED_SWAPS),
            ),
            scout=dict(
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
                early_stop_min_scouts=int(STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS),
            ),
            sub_candidates=int(STAGE1_SUB_CANDIDATES),
            sub_candidates_by_columns={str(k): int(v) for k, v in STAGE1_SUB_CANDIDATES_BY_COLUMNS.items()},
        ),
        stage2=dict(
            scorer=dict(SCORER_STAGE2),
            pass1_primary_char_weights={str(k): float(v) for k, v in STAGE2_PASS1_PRIMARY_CHAR_WEIGHTS.items()},
            pass1_fallback_char_weights={str(k): float(v) for k, v in STAGE2_PASS1_FALLBACK_CHAR_WEIGHTS.items()},
            pass1_diversity_rule=dict(
                min_hamming_factor=float(STAGE2_PASS1_DIVERSITY_MIN_HAMMING_FACTOR),
                min_first_symbols=int(STAGE2_PASS1_DIVERSITY_MIN_FIRST_SYMBOLS),
            ),
            exact_max_columns=int(STAGE2_EXACT_MAX_COLUMNS),
            exact_sub_candidates=int(STAGE2_EXACT_SUB_CANDIDATES),
            exact_sub_by_columns={str(k): int(v) for k, v in STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS.items()},
            exact_two_pass=bool(STAGE2_EXACT_TWO_PASS),
            pass1_top_tails=int(STAGE2_EXACT_PASS1_TOP_TAILS),
            pass1_top_by_columns={str(k): int(v) for k, v in STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS.items()},
            early_solve_break=bool(STAGE2_EXACT_EARLY_SOLVE_BREAK),
            hybrid_solver=dict(SOLVER_STAGE2),
            hybrid_sub_candidates=int(STAGE2_HYBRID_SUB_CANDIDATES),
            hybrid_sub_by_columns={str(k): int(v) for k, v in STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS.items()},
            judge_pool=dict(
                mode=(
                    "stage3_judge_enabled"
                    if bool(STAGE2_PROMOTE_BY_STAGE3_JUDGE or STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE)
                    else "telemetry_only_topk"
                ),
                topk_default=int(SAVE_STAGE2_TOPK),
                promote_by_stage3_judge=bool(STAGE2_PROMOTE_BY_STAGE3_JUDGE),
                entry_band_by_stage3_judge=bool(STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE),
            ),
        ),
        stage3=dict(
            scorer=dict(SCORER_FULL),
            solver=dict(SOLVER_STAGE3),
            init_keys=int(STAGE3_INITIAL_KEYS),
            init_by_columns={str(k): int(v) for k, v in STAGE3_INITIAL_KEYS_BY_COLUMNS.items()},
            dynamic_bands=[dict(b) for b in STAGE3_DYNAMIC_BANDS],
            two_phase=dict(
                enabled=bool(STAGE3_TWO_PHASE_ENABLED),
                phase_a=dict(STAGE3_PHASEA_CFG),
                phase_b=dict(STAGE3_PHASEB_CFG),
                phase_b_top_n=int(STAGE3_PHASEB_TOP_N),
                gate_delta_floor=float(STAGE3_PHASEB_GATE_DELTA_FLOOR),
                gate_end_gain_floor=float(STAGE3_PHASEB_GATE_END_GAIN_FLOOR),
            ),
            c1_focus=dict(
                enabled=bool(STAGE3_C1_FOCUS_ENABLED),
                init_keys=int(STAGE3_C1_INIT_KEYS),
                phase_a_steps=int(STAGE3_C1_PHASEA_STEPS),
                phase_b_steps=int(STAGE3_C1_PHASEB_STEPS),
                phase_b_top_n=int(STAGE3_C1_PHASEB_TOP_N),
                gate_delta_floor=float(STAGE3_C1_PHASEB_GATE_DELTA_FLOOR),
                gate_end_gain_floor=float(STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR),
            ),
        ),
    )
    (run_dir / "run_config.json").write_text(json.dumps(run_config, indent=2), encoding="utf-8")

    print(
        f"[pipeline_no_wli] setup: profile={PROFILE} mode={PIPELINE_RUN_MODE} "
        f"direction={direction.value} order={ORDER} A={ALPHABET_SIZE}",
        flush=True,
    )
    print(
        f"[pipeline_no_wli] PROFILE_BANNER "
        f"NO_WLI_PIPELINE_PROFILE_ID={NO_WLI_PIPELINE_PROFILE_ID} "
        f"previous_default={NO_WLI_PIPELINE_PROFILE_ID_PREVIOUS_DEFAULT} "
        f"stage3={_scorer_objective_summary(SCORER_FULL)}",
        flush=True,
    )
    print(
        f"[pipeline_no_wli] setup: objective "
        f"impl(stage1/2)={getattr(SCORER_IMPL, 'value', SCORER_IMPL)} "
        f"impl(stage3)={str(SCORER_FULL.get('impl', SCORER_IMPL))} "
        f"stage1=({SCORER_STAGE1_LABEL},{_scorer_objective_summary(SCORER_STAGE1)},wli_off) "
        f"stage2=({SCORER_STAGE2_LABEL},{_scorer_objective_summary(SCORER_STAGE2)},wli_off) "
        f"stage3=({SCORER_STAGE3_LABEL},{_scorer_objective_summary(SCORER_FULL)},wli_off)",
        flush=True,
    )
    print(
        f"[pipeline_no_wli] setup: ecdf_guard="
        f"{'on' if bool(REQUIRE_NO_ECDF_FOR_AVG_FULLTEXT) else 'off'} "
        f"(avg_fulltext_required_for_all_stages={bool(REQUIRE_NO_ECDF_FOR_AVG_FULLTEXT)})",
        flush=True,
    )
    print(
        f"[pipeline_no_wli] setup: search knobs "
        f"stage1_seed_restarts={int(STAGE1_SEED_RESTARTS)} "
        f"stage1_seed_plan=(blocks={int(STAGE1_SEED_N_BLOCKS)},total={int(STAGE1_SEED_TOTAL)},swaps={int(STAGE1_SEED_SWAPS)}) "
        f"stage12_scout_runs={int(STAGE12_SCOUT_RUNS)} stage12_archive_keep={int(STAGE12_ARCHIVE_KEEP)} "
        f"stage12_promote_top={int(STAGE12_PROMOTE_TOP)} "
        f"stage1_scout_scale=(steps={float(STAGE1_SCOUT_STEP_SCALE):.2f},restarts={float(STAGE1_SCOUT_RESTART_SCALE):.2f}) "
        f"stage1_scout_mins=(steps={int(STAGE1_SCOUT_MIN_STEPS)},restarts={int(STAGE1_SCOUT_MIN_RESTARTS)}) "
        f"stage1_scout_plateau=(delta={float(STAGE1_SCOUT_NO_IMPROVE_DELTA):.1e},"
        f"patience={int(STAGE1_SCOUT_NO_IMPROVE_PATIENCE)},"
        f"min_new_archive={int(STAGE1_SCOUT_MIN_NEW_ARCHIVE)},"
        f"early_stop_min_scouts={int(STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS)}) "
        f"stage1_sub_candidates={int(STAGE1_SUB_CANDIDATES)} "
        f"stage1_sub_by_c={json.dumps({str(k): int(v) for k, v in STAGE1_SUB_CANDIDATES_BY_COLUMNS.items()}, separators=(',', ':'))} "
        f"stage3_init_keys={int(STAGE3_INITIAL_KEYS)} "
        f"stage3_init_by_c={json.dumps({str(k): int(v) for k, v in STAGE3_INITIAL_KEYS_BY_COLUMNS.items()}, separators=(',', ':'))} "
        f"stage2_exact_max_columns={int(STAGE2_EXACT_MAX_COLUMNS)} "
        f"stage2_exact_sub_candidates={int(STAGE2_EXACT_SUB_CANDIDATES)} "
        f"stage2_exact_sub_by_c={json.dumps({str(k): int(v) for k, v in STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS.items()}, separators=(',', ':'))} "
        f"stage2_pass1_primary={_weights_text(STAGE2_PASS1_PRIMARY_CHAR_WEIGHTS)} "
        f"stage2_pass1_fallback={_weights_text(STAGE2_PASS1_FALLBACK_CHAR_WEIGHTS)} "
        f"stage2_hybrid_sub_candidates={int(STAGE2_HYBRID_SUB_CANDIDATES)} "
        f"stage2_hybrid_sub_by_c={json.dumps({str(k): int(v) for k, v in STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS.items()}, separators=(',', ':'))}",
        flush=True,
    )
    print(
        f"[pipeline_no_wli] setup: stage3_two_phase="
        f"{'on' if bool(STAGE3_TWO_PHASE_ENABLED) else 'off'} "
        f"phaseA={json.dumps(dict(STAGE3_PHASEA_CFG), separators=(',', ':'))} "
        f"phaseB={json.dumps(dict(STAGE3_PHASEB_CFG), separators=(',', ':'))} "
        f"phaseB_top_n={int(STAGE3_PHASEB_TOP_N)} "
        f"phaseB_gate=(delta={float(STAGE3_PHASEB_GATE_DELTA_FLOOR):.4f},"
        f"end_gain={float(STAGE3_PHASEB_GATE_END_GAIN_FLOOR):.4f}) "
        f"c1_focus=(enabled={1 if bool(STAGE3_C1_FOCUS_ENABLED) else 0},"
        f"init_keys={int(STAGE3_C1_INIT_KEYS)},"
        f"phaseA_steps={int(STAGE3_C1_PHASEA_STEPS)},"
        f"phaseB_steps={int(STAGE3_C1_PHASEB_STEPS)},"
        f"phaseB_top_n={int(STAGE3_C1_PHASEB_TOP_N)},"
        f"gate_delta={float(STAGE3_C1_PHASEB_GATE_DELTA_FLOOR):.4f},"
        f"gate_end_gain={float(STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR):.4f})",
        flush=True,
    )
    print(f"[pipeline_no_wli] setup: tiers={len(TIERS)} text_offsets={TEXT_OFFSETS} key_seeds={KEY_SEEDS}", flush=True)
    print(f"[pipeline_no_wli] reports: {run_dir.relative_to(root)}", flush=True)

    stages: List[dict] = []
    instances: List[dict] = []
    total = len(TIERS) * len(TEXT_OFFSETS) * len(KEY_SEEDS)
    done = 0
    t0_all = time.time()
    last_hb = float(t0_all)
    best_global = {"match": float("-inf"), "tier": "", "text_id": -1, "key_seed": -1, "stage": "", "preview": ""}

    for tier in TIERS:
        for text_id, off in enumerate(TEXT_OFFSETS):
            pt_idx, wli, offset_used = base._slice_word_aligned(pt_base, wli_base, length=tier.length, offset_hint=int(off))
            for key_seed in KEY_SEEDS:
                t0_i = time.time()
                key_len = int(tier.period * ALPHABET_SIZE + tier.columns)
                rng = np.random.default_rng(int(key_seed))
                keyops = PeriodicStructuredMatrixKeyOps(K=key_len, period=tier.period, A=ALPHABET_SIZE, columns=tier.columns)
                key_true = keyops.random(rng).astype(np.int16, copy=False)

                cfg_full = CipherConfig(
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
                cfg_sub = CipherConfig(
                    name="periodic_substitution",
                    ciphertext=[],
                    period=tier.period,
                    alphabet_size=ALPHABET_SIZE,
                    key_length=tier.period * ALPHABET_SIZE,
                    encoding_dir=direction,
                    wli_data=[],
                    device=Device.CPU,
                )
                full_cipher = PeriodicColumnarCipher(cfg_full)
                sub_cipher = PeriodicSubstitutionCipher(cfg_sub)
                ct_idx = full_cipher.encrypt_single(plaintext=pt_idx, key=key_true)

                sub_len = int(tier.period * ALPHABET_SIZE)
                true_sub = key_true[:sub_len].astype(np.int16, copy=False)
                pt_stage1_oracle = np.asarray(sub_cipher.decrypt_single(ciphertext=ct_idx, key=true_sub), dtype=np.uint8).reshape(-1)

                scorer_stage1 = dict(SCORER_STAGE1, encoding_dir=direction)
                scorer_stage2 = dict(SCORER_STAGE2, encoding_dir=direction)
                scorer_full = dict(SCORER_FULL, encoding_dir=direction)
                if bool(REQUIRE_NO_ECDF_FOR_AVG_FULLTEXT):
                    scorer_gate = [
                        ("stage1", scorer_stage1),
                        ("stage2", scorer_stage2),
                        ("stage3", scorer_full),
                    ]
                    non_fulltext = [lbl for lbl, cfg in scorer_gate if not _is_avg_fulltext_scorer(cfg)]
                    if non_fulltext:
                        raise RuntimeError(
                            "[pipeline_no_wli] no-ECDF guard requires avg.logp full_text for all stages; "
                            f"non_compliant={','.join(non_fulltext)} profile={NO_WLI_PIPELINE_PROFILE_ID}"
                        )
                scorer_stage1_runtime = build_scorer(cfg_sub, ScoringConfig(**scorer_stage1))
                scorer_stage2_runtime = build_scorer(cfg_full, ScoringConfig(**scorer_stage2))
                scorer_full_runtime = build_scorer(cfg_full, ScoringConfig(**scorer_full))
                _guard_no_ecdf_usage(scorer_runtime=scorer_stage1_runtime, scorer_cfg=scorer_stage1, stage_label="stage1")
                _guard_no_ecdf_usage(scorer_runtime=scorer_stage2_runtime, scorer_cfg=scorer_stage2, stage_label="stage2")
                _guard_no_ecdf_usage(scorer_runtime=scorer_full_runtime, scorer_cfg=scorer_full, stage_label="stage3")
                scorer_stage2_pass1_primary_runtime = None
                scorer_stage2_pass1_fallback_runtime = None
                if int(tier.columns) <= int(STAGE2_EXACT_MAX_COLUMNS) and bool(STAGE2_EXACT_TWO_PASS):
                    stage2_objective = str(SCORER_STAGE2.get("objective", "pct.logp.win10"))
                    stage2_avg_policy = SCORER_STAGE2.get("avg_window_policy", None)
                    scorer_stage2_pass1_primary = dict(
                        objective=stage2_objective,
                        include_char=True,
                        use_word_breaks=False,
                        char_weights=dict(STAGE2_PASS1_PRIMARY_CHAR_WEIGHTS),
                        wli_weights={},
                        encoding_dir=direction,
                        impl=SCORER_IMPL,
                    )
                    if stage2_avg_policy is not None:
                        scorer_stage2_pass1_primary["avg_window_policy"] = str(stage2_avg_policy)
                    scorer_stage2_pass1_primary_runtime = build_scorer(
                        cfg_full, ScoringConfig(**scorer_stage2_pass1_primary)
                    )
                    _guard_no_ecdf_usage(
                        scorer_runtime=scorer_stage2_pass1_primary_runtime,
                        scorer_cfg=scorer_stage2_pass1_primary,
                        stage_label="stage2_pass1_primary",
                    )
                    if dict(STAGE2_PASS1_FALLBACK_CHAR_WEIGHTS) and (
                        dict(STAGE2_PASS1_FALLBACK_CHAR_WEIGHTS) != dict(STAGE2_PASS1_PRIMARY_CHAR_WEIGHTS)
                    ):
                        scorer_stage2_pass1_fallback = dict(
                            objective=stage2_objective,
                            include_char=True,
                            use_word_breaks=False,
                            char_weights=dict(STAGE2_PASS1_FALLBACK_CHAR_WEIGHTS),
                            wli_weights={},
                            encoding_dir=direction,
                            impl=SCORER_IMPL,
                        )
                        if stage2_avg_policy is not None:
                            scorer_stage2_pass1_fallback["avg_window_policy"] = str(stage2_avg_policy)
                        scorer_stage2_pass1_fallback_runtime = build_scorer(
                            cfg_full, ScoringConfig(**scorer_stage2_pass1_fallback)
                        )
                        _guard_no_ecdf_usage(
                            scorer_runtime=scorer_stage2_pass1_fallback_runtime,
                            scorer_cfg=scorer_stage2_pass1_fallback,
                            stage_label="stage2_pass1_fallback",
                        )

                oracle_s1, oracle_s1_raw, s1_obj = _oracle_score_for_stage(pt_idx=pt_stage1_oracle, cipher_cfg=cfg_sub, scorer_params=scorer_stage1)
                oracle_s2, oracle_s2_raw, s2_obj = _oracle_score_for_stage(pt_idx=pt_idx, cipher_cfg=cfg_full, scorer_params=scorer_stage2)
                oracle_s3, oracle_s3_raw, s3_obj = _oracle_score_for_stage(pt_idx=pt_idx, cipher_cfg=cfg_full, scorer_params=scorer_full)
                print(
                    f"[pipeline_no_wli] objective tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"stage1={SCORER_STAGE1_LABEL} stage2={SCORER_STAGE2_LABEL} stage3={SCORER_STAGE3_LABEL}",
                    flush=True,
                )
                print(
                    "[pipeline_no_wli] oracle-score "
                    f"stage=stage1_sub model={s1_obj} "
                    f"(char={_weights_text(dict(SCORER_STAGE1.get('char_weights', {})))},wli={{}},wb=0) "
                    f"score={oracle_s1:.6f} raw={oracle_s1_raw:.6f}",
                    flush=True,
                )
                print(
                    "[pipeline_no_wli] oracle-score "
                    f"stage=stage2_search model={s2_obj} "
                    f"(char={_weights_text(dict(SCORER_STAGE2.get('char_weights', {})))},wli={{}},wb=0) "
                    f"score={oracle_s2:.6f} raw={oracle_s2_raw:.6f}",
                    flush=True,
                )
                print(
                    "[pipeline_no_wli] oracle-score "
                    f"stage=stage3_refine model={s3_obj} "
                    f"(char={_weights_text(dict(SCORER_FULL.get('char_weights', {})))},wli={{}},wb=0) "
                    f"score={oracle_s3:.6f} raw={oracle_s3_raw:.6f}",
                    flush=True,
                )

                if not np.array_equal(
                    np.asarray(full_cipher.decrypt_single(ciphertext=ct_idx, key=key_true), dtype=np.uint8),
                    np.asarray(pt_idx, dtype=np.uint8),
                ):
                    raise RuntimeError(f"[pipeline_no_wli] gate0 roundtrip failed tier={tier.name} text={text_id} key_seed={key_seed}")

                _print_stage_preview(label="oracle", pt=pt_idx.tolist(), wli=wli, match_ratio=1.0)

                # Stage 1: periodic substitution (scouts + archive).
                t_s1 = time.time()
                solver_stage1_base_cfg = dict(SOLVER_STAGE1)
                solver_stage1_base_cfg["seed_restarts"] = int(STAGE1_SEED_RESTARTS)
                stage1_sub_limit = int(STAGE1_SUB_CANDIDATES_BY_COLUMNS.get(int(tier.columns), STAGE1_SUB_CANDIDATES))
                stage1_archive_keep = max(int(stage1_sub_limit), int(STAGE12_ARCHIVE_KEEP), 1)
                stage1_scout_runs = max(1, int(STAGE12_SCOUT_RUNS))
                print(
                    f"[pipeline_no_wli] stage1-stop tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"stop_score={solver_stage1_base_cfg.get('stop_score', 'none')} "
                    f"plateau_rounds={solver_stage1_base_cfg.get('plateau_rounds')} "
                    f"plateau_min_delta={solver_stage1_base_cfg.get('plateau_min_delta')} "
                    f"scouts={stage1_scout_runs} archive_keep={stage1_archive_keep} "
                    f"scout_plateau=(delta={float(STAGE1_SCOUT_NO_IMPROVE_DELTA):.1e},"
                    f"patience={int(STAGE1_SCOUT_NO_IMPROVE_PATIENCE)},"
                    f"min_new_archive={int(STAGE1_SCOUT_MIN_NEW_ARCHIVE)},"
                    f"early_stop_min_scouts={int(STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS)}) "
                    f"oracle_guard=off",
                    flush=True,
                )
                stage1_archive: Dict[Tuple[int, ...], Dict[str, Any]] = {}
                stage1_unique_start_hashes: set[str] = set()
                stage1_unique_end_hashes: set[str] = set()
                stage1_best_score = float("-inf")
                stage1_best_sub: List[int] = []
                stage1_best_pt: List[int] = []
                stage1_best_match = float("-inf")
                ev1 = 0
                base_steps = int(solver_stage1_base_cfg.get("steps", 0))
                base_restarts = int(solver_stage1_base_cfg.get("restarts", 0))
                base_seed_restarts = int(solver_stage1_base_cfg.get("seed_restarts", STAGE1_SEED_RESTARTS))
                stage1_scouts_done = 0
                stage1_no_improve_scouts = 0
                stage1_seed_probe_added_total = 0
                stage1_seed_probe_scouts = 0

                for scout_idx in range(stage1_scout_runs):
                    stage1_scouts_done += 1
                    pre_scout_best_score = float(stage1_best_score)
                    pre_scout_archive_n = int(len(stage1_archive))
                    pre_scout_unique_end_n = int(len(stage1_unique_end_hashes))
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

                    scout_seed = 2026 + int(key_seed) + 1009 * int(scout_idx)
                    s1_seeds = make_periodic_seed_pool(
                        ct_idx,
                        period=tier.period,
                        direction=direction.value,
                        seed=int(scout_seed),
                        n_block_seeds=int(STAGE1_SEED_N_BLOCKS),
                        total_seeds=int(STAGE1_SEED_TOTAL),
                        swaps_per_block=int(STAGE1_SEED_SWAPS),
                        alphabet_size=ALPHABET_SIZE,
                    )
                    for _seed_key in s1_seeds:
                        stage1_unique_start_hashes.add(_key_hash16(_seed_key))
                    sol1 = run(
                        text=ct_idx.tolist(),
                        cipher=by_name.cipher("periodic_substitution", period=tier.period, alphabet_size=ALPHABET_SIZE),
                        key=KeySpec.periodic_substitution(period=tier.period, alphabet_size=ALPHABET_SIZE),
                        solver=SolverSpec.kaeding(**solver_stage1_cfg),
                        scorer_params=scorer_stage1,
                        wli_data=[],
                        encoding_dir=direction,
                        telemetry_on=True,
                        initial_keys=s1_seeds,
                        force_no_wli=True,
                    )
                    scout_evals = int((getattr(sol1, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
                    ev1 += scout_evals
                    sub_best = np.asarray(getattr(sol1, "key", []) or [], dtype=np.int16).reshape(-1)
                    sub_key_match_this = base._match_ratio(sub_best.tolist(), true_sub.tolist())
                    sub_candidates_this = _extract_top_keys(sol1, limit=stage1_sub_limit) or [sub_best.astype(int).tolist()]
                    sub_candidates_source = "telemetry_topk"
                    seed_probe_added = 0
                    if len(sub_candidates_this) < int(stage1_sub_limit):
                        # Fallback when telemetry top-keys collapse to 1 candidate:
                        # probe deterministic stage1 seed pool and backfill best-scoring diverse keys.
                        seen_keys: set[Tuple[int, ...]] = set(
                            tuple(int(x) for x in row) for row in sub_candidates_this if row
                        )
                        seed_probe_keys: List[np.ndarray] = []
                        for seed_key in s1_seeds:
                            seed_arr = np.asarray(seed_key, dtype=np.int16).reshape(-1)
                            if seed_arr.size != int(sub_len):
                                continue
                            seed_t = tuple(int(x) for x in seed_arr.tolist())
                            if seed_t in seen_keys:
                                continue
                            seen_keys.add(seed_t)
                            seed_probe_keys.append(seed_arr)
                        if seed_probe_keys:
                            _pt_seed, sc_seed, _seed_stats = decrypt_and_score_keys_chunked(
                                cipher=sub_cipher,
                                ciphertext=ct_idx,
                                keys=seed_probe_keys,
                                scorer=scorer_stage1_runtime,
                                wli=None,
                                key_dtype=np.int16,
                                chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                                require_batch=bool(REQUIRE_BATCH_SCORING),
                            )
                            if int(sc_seed.size) > 0:
                                seed_ranked = np.argsort(sc_seed)[::-1]
                                for seed_idx in seed_ranked.tolist():
                                    if len(sub_candidates_this) >= int(stage1_sub_limit):
                                        break
                                    key_list = seed_probe_keys[int(seed_idx)].astype(int).tolist()
                                    sub_candidates_this.append(key_list)
                                    seed_probe_added += 1
                        if seed_probe_added > 0:
                            sub_candidates_source = "telemetry_plus_seed_probe"
                            stage1_seed_probe_scouts += 1
                            stage1_seed_probe_added_total += int(seed_probe_added)
                        elif sub_candidates_this:
                            sub_candidates_source = "telemetry_only"
                        else:
                            sub_candidates_source = "seed_probe_empty"

                    sub_keys_stage1: List[np.ndarray] = []
                    for sub_key in sub_candidates_this:
                        sub_arr = np.asarray(sub_key, dtype=np.int16).reshape(-1)
                        if sub_arr.size == int(sub_len):
                            sub_keys_stage1.append(sub_arr)
                    if sub_keys_stage1:
                        pt_batch, sc_batch, _batch_stats = decrypt_and_score_keys_chunked(
                            cipher=sub_cipher,
                            ciphertext=ct_idx,
                            keys=sub_keys_stage1,
                            scorer=scorer_stage1_runtime,
                            wli=None,
                            key_dtype=np.int16,
                            chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                            require_batch=bool(REQUIRE_BATCH_SCORING),
                        )
                        scout_unique_end_hashes: set[str] = set()
                        for i_row, sub_arr in enumerate(sub_keys_stage1):
                            pt1 = np.asarray(pt_batch[i_row], dtype=np.uint8).reshape(-1)
                            sc1 = float(sc_batch[i_row])
                            key_t = tuple(int(x) for x in sub_arr.tolist())
                            scout_unique_end_hashes.add(_key_hash16(key_t))
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
                        stage1_unique_end_hashes.update(scout_unique_end_hashes)

                    stage1_score_gain = (
                        float(stage1_best_score - pre_scout_best_score)
                        if np.isfinite(stage1_best_score) and np.isfinite(pre_scout_best_score)
                        else float("inf")
                    )
                    stage1_new_archive = int(len(stage1_archive) - pre_scout_archive_n)
                    stage1_new_unique_hashes = int(len(stage1_unique_end_hashes) - pre_scout_unique_end_n)
                    stages.append(
                        dict(
                            tier=tier.name,
                            text_id=int(text_id),
                            key_seed=int(key_seed),
                            stage=f"stage1_sub_scout_{int(scout_idx) + 1}",
                            score=float(getattr(sol1, "score", float("nan"))),
                            sub_key_match=float(sub_key_match_this),
                            seconds=0.0,
                            evals=int(scout_evals),
                            candidates=len(sub_candidates_this),
                            candidate_source=str(sub_candidates_source),
                            seed_probe_added=int(seed_probe_added),
                            scout_seed=int(scout_seed),
                            archive_size=int(len(stage1_archive)),
                            new_archive_keys=int(stage1_new_archive),
                            new_archive_hashes=int(stage1_new_unique_hashes),
                            score_gain=(float(stage1_score_gain) if np.isfinite(stage1_score_gain) else np.nan),
                        )
                    )
                    if (
                        scout_idx > 0
                        and stage1_score_gain <= float(STAGE1_SCOUT_NO_IMPROVE_DELTA)
                        and stage1_new_unique_hashes <= int(STAGE1_SCOUT_MIN_NEW_ARCHIVE)
                    ):
                        stage1_no_improve_scouts += 1
                    else:
                        stage1_no_improve_scouts = 0
                    min_scouts_before_early_stop = int(
                        max(1, min(int(stage1_scout_runs), int(STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS)))
                    )
                    if (
                        scout_idx + 1 < int(stage1_scout_runs)
                        and int(stage1_scouts_done) >= int(min_scouts_before_early_stop)
                        and stage1_no_improve_scouts >= int(STAGE1_SCOUT_NO_IMPROVE_PATIENCE)
                    ):
                        print(
                            f"[pipeline_no_wli] stage1-early-stop tier={tier.name} text={text_id} key_seed={key_seed} "
                            f"reason=scout_plateau scouts_done={stage1_scouts_done}/{stage1_scout_runs} "
                            f"score_gain={stage1_score_gain:.6g} new_archive={stage1_new_archive} "
                            f"new_archive_hashes={int(stage1_new_unique_hashes)}",
                            flush=True,
                        )
                        break

                dt1 = float(time.time() - t_s1)
                stage1_ranked = sorted(
                    stage1_archive.values(),
                    key=lambda e: (float(e.get("score", float("-inf"))), float(e.get("sub_key_match", float("-inf")))),
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
                    _print_stage_preview(label="stage1_sub", pt=stage1_best_pt, wli=wli, match_ratio=float(m1))
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
                        archive_size=int(len(stage1_archive)),
                    )
                )
                print(
                    f"[pipeline_no_wli] stage1-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"score={float(stage1_best_score if np.isfinite(stage1_best_score) else np.nan):.6f} "
                    f"sub_key_match={float(sub_key_match):.3f} evals={int(ev1)} seconds={dt1:.1f} "
                    f"candidates={len(sub_candidates)} scouts={int(stage1_scouts_done)} "
                    f"archive_size={int(len(stage1_archive))} "
                    f"seed_probe_scouts={int(stage1_seed_probe_scouts)} "
                    f"seed_probe_added_total={int(stage1_seed_probe_added_total)}",
                    flush=True,
                )
                print(
                    f"[pipeline_no_wli] stage1-diversity tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"unique_start_hash={int(len(stage1_unique_start_hashes))} "
                    f"unique_end_hash={int(len(stage1_unique_end_hashes))} "
                    f"archive_size={int(len(stage1_archive))}",
                    flush=True,
                )

                # Stage 2: identity/exact/hybrid with archive+promote.
                best2_match, best2_score, best2_key, best2_preview = float("-inf"), float("-inf"), None, ""
                best2_pt: List[int] | None = None
                stage2_evals_total = 0
                stage2_archive_keep = max(1, int(STAGE12_ARCHIVE_KEEP))
                stage2_promote_top = max(1, int(STAGE12_PROMOTE_TOP))
                stage2_archive: Dict[Tuple[int, ...], Dict[str, Any]] = {}
                stage2_entry_score = float("-inf")
                exact_sub_limit = int(STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS.get(int(tier.columns), STAGE2_EXACT_SUB_CANDIDATES))
                pass1_top_tails = int(STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS.get(int(tier.columns), STAGE2_EXACT_PASS1_TOP_TAILS))
                hybrid_sub_limit = int(
                    STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS.get(int(tier.columns), STAGE2_HYBRID_SUB_CANDIDATES)
                )
                tail_chunk = int(BATCH_EVAL_CHUNK_SIZE)

                def _iter_tail_chunks(columns: int, chunk_size: int):
                    block: List[Tuple[int, ...]] = []
                    for tail in permutations(range(int(columns))):
                        block.append(tuple(int(x) for x in tail))
                        if len(block) >= int(chunk_size):
                            yield block
                            block = []
                    if block:
                        yield block

                def _consider_stage2_candidate(*, full_key_arr: np.ndarray, pt2_arr: np.ndarray, match_val: float, score_val: float, preview_label: str) -> None:
                    nonlocal best2_match, best2_score, best2_key, best2_pt, best2_preview
                    key_list = full_key_arr.astype(int).tolist()
                    key_t = tuple(int(x) for x in key_list)
                    prev = stage2_archive.get(key_t)
                    if (prev is None) or (float(score_val) > float(prev.get("score", float("-inf")))):
                        stage2_archive[key_t] = dict(
                            key=key_list,
                            score=float(score_val),
                            match=float(match_val),
                            plaintext=pt2_arr.astype(int).tolist(),
                            preview=_preview_latin(pt2_arr.tolist(), wli),
                        )
                    if (match_val > best2_match) or (abs(match_val - best2_match) <= 1e-12 and score_val > best2_score):
                        best2_match, best2_score = float(match_val), float(score_val)
                        best2_key = key_list
                        best2_pt = pt2_arr.astype(int).tolist()
                        best2_preview = _preview_latin(pt2_arr.tolist(), wli)
                        _print_stage_preview(label=preview_label, pt=pt2_arr.tolist(), wli=wli, match_ratio=float(match_val))

                if int(tier.columns) <= 1:
                    full_keys_identity: List[np.ndarray] = []
                    for sub_key in sub_candidates:
                        sub_arr = np.asarray(sub_key, dtype=np.int16).reshape(-1)
                        full_key = np.concatenate([sub_arr, np.asarray([0], dtype=np.int16)], axis=0)
                        full_keys_identity.append(full_key)
                    if full_keys_identity:
                        pt_batch, sc_batch, _batch_stats = decrypt_and_score_keys_chunked(
                            cipher=full_cipher,
                            ciphertext=ct_idx,
                            keys=full_keys_identity,
                            scorer=scorer_stage2_runtime,
                            wli=None,
                            key_dtype=np.int16,
                            chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                            require_batch=bool(REQUIRE_BATCH_SCORING),
                        )
                        for i, full_key in enumerate(full_keys_identity):
                            pt2 = np.asarray(pt_batch[i], dtype=np.uint8).reshape(-1)
                            m2 = base._match_ratio(pt2.tolist(), pt_idx.tolist())
                            sc2 = float(sc_batch[i])
                            stage2_evals_total += 1
                            _consider_stage2_candidate(
                                full_key_arr=full_key,
                                pt2_arr=pt2,
                                match_val=float(m2),
                                score_val=float(sc2),
                                preview_label=f"stage2_identity_best_{i+1}",
                            )
                    print(
                        f"[pipeline_no_wli] stage2-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"mode=identity best_match_ratio={float(best2_match):.3f} "
                        f"best_score_at_best_match={float(best2_score):.6f} evals={int(stage2_evals_total)}",
                        flush=True,
                    )
                elif int(tier.columns) <= int(STAGE2_EXACT_MAX_COLUMNS):
                    exact_subs = sub_candidates[: max(1, int(exact_sub_limit))]
                    exact_early_stop = False
                    for i, sub_key in enumerate(exact_subs):
                        sub_arr = np.asarray(sub_key, dtype=np.int16)
                        pass1_evals = 0
                        pass2_evals = 0
                        shortlist_tails: List[Tuple[int, ...]] = []
                        pass1_scorer_used = "none"
                        pass1_fallback_used = False
                        pass1_primary_metrics: Dict[str, float] = {}
                        pass1_used_metrics: Dict[str, float] = {}

                        if bool(STAGE2_EXACT_TWO_PASS) and scorer_stage2_pass1_primary_runtime is not None:
                            pass1_ranked: List[Tuple[float, Tuple[int, ...]]] = []
                            for tail_block in _iter_tail_chunks(int(tier.columns), tail_chunk):
                                full_keys_block: List[np.ndarray] = []
                                for tail in tail_block:
                                    col_key = np.asarray(tail, dtype=np.int16)
                                    full_keys_block.append(np.concatenate([sub_arr, col_key], axis=0))
                                pt_block, fast_block, _batch_stats = decrypt_and_score_keys_chunked(
                                    cipher=full_cipher,
                                    ciphertext=ct_idx,
                                    keys=full_keys_block,
                                    scorer=scorer_stage2_pass1_primary_runtime,
                                    wli=None,
                                    key_dtype=np.int16,
                                    chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                                    require_batch=bool(REQUIRE_BATCH_SCORING),
                                )
                                pass1_evals += int(len(tail_block))
                                stage2_evals_total += int(len(tail_block))
                                for j, tail in enumerate(tail_block):
                                    pt2 = np.asarray(pt_block[j], dtype=np.uint8).reshape(-1)
                                    full_key = full_keys_block[j]
                                    fast_sc = float(fast_block[j])
                                    pass1_ranked.append((fast_sc, tail))
                                    if bool(STAGE2_EXACT_EARLY_SOLVE_BREAK):
                                        m2 = base._match_ratio(pt2.tolist(), pt_idx.tolist())
                                        if float(m2) >= float(SOLVE_MATCH_THRESHOLD):
                                            sc2 = float(
                                                score_plaintexts_chunked(
                                                    scorer=scorer_stage2_runtime,
                                                    plaintexts=np.asarray([pt2], dtype=np.uint8),
                                                    wli=None,
                                                    chunk_size=1,
                                                    require_batch=bool(REQUIRE_BATCH_SCORING),
                                                )[0][0]
                                            )
                                            pass2_evals += 1
                                            stage2_evals_total += 1
                                            _consider_stage2_candidate(
                                                full_key_arr=full_key,
                                                pt2_arr=pt2,
                                                match_val=float(m2),
                                                score_val=float(sc2),
                                                preview_label=f"stage2_exact_best_sub{i+1}",
                                            )
                                            exact_early_stop = True
                                            break
                                if exact_early_stop:
                                    break
                            if not exact_early_stop:
                                pass1_ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
                                k_short = min(int(pass1_top_tails), len(pass1_ranked))
                                shortlist_primary = [tail for _s, tail in pass1_ranked[:k_short]]
                                pass1_scorer_used = "primary_char34"
                                collapsed, pass1_primary_metrics = _tail_diversity_collapsed(
                                    shortlist_primary, columns=int(tier.columns)
                                )
                                shortlist_tails = list(shortlist_primary)
                                pass1_used_metrics = dict(pass1_primary_metrics)
                                if collapsed and scorer_stage2_pass1_fallback_runtime is not None:
                                    pass1_fallback_used = True
                                    pass1_ranked_fb: List[Tuple[float, Tuple[int, ...]]] = []
                                    for tail_block in _iter_tail_chunks(int(tier.columns), tail_chunk):
                                        full_keys_block: List[np.ndarray] = []
                                        for tail in tail_block:
                                            col_key = np.asarray(tail, dtype=np.int16)
                                            full_keys_block.append(np.concatenate([sub_arr, col_key], axis=0))
                                        _pt_block, fast_fb_block, _batch_stats = decrypt_and_score_keys_chunked(
                                            cipher=full_cipher,
                                            ciphertext=ct_idx,
                                            keys=full_keys_block,
                                            scorer=scorer_stage2_pass1_fallback_runtime,
                                            wli=None,
                                            key_dtype=np.int16,
                                            chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                                            require_batch=bool(REQUIRE_BATCH_SCORING),
                                        )
                                        pass1_evals += int(len(tail_block))
                                        stage2_evals_total += int(len(tail_block))
                                        for j, tail in enumerate(tail_block):
                                            fast_sc_fb = float(fast_fb_block[j])
                                            pass1_ranked_fb.append((fast_sc_fb, tail))
                                    pass1_ranked_fb.sort(key=lambda x: (x[0], x[1]), reverse=True)
                                    shortlist_tails = [tail for _s, tail in pass1_ranked_fb[:k_short]]
                                    pass1_scorer_used = "fallback_char2"
                                    _collapsed_fb, pass1_used_metrics = _tail_diversity_collapsed(
                                        shortlist_tails, columns=int(tier.columns)
                                    )
                        else:
                            shortlist_tails = [tuple(int(x) for x in tail) for tail in permutations(range(int(tier.columns)))]
                            pass1_scorer_used = "full_enum"
                            _collapsed_enum, pass1_used_metrics = _tail_diversity_collapsed(
                                shortlist_tails, columns=int(tier.columns)
                            )

                        if not exact_early_stop:
                            for lo in range(0, len(shortlist_tails), int(tail_chunk)):
                                tail_block = shortlist_tails[lo : lo + int(tail_chunk)]
                                full_keys_block: List[np.ndarray] = []
                                for tail in tail_block:
                                    col_key = np.asarray(tail, dtype=np.int16)
                                    full_keys_block.append(np.concatenate([sub_arr, col_key], axis=0))
                                pt_block, sc_block, _batch_stats = decrypt_and_score_keys_chunked(
                                    cipher=full_cipher,
                                    ciphertext=ct_idx,
                                    keys=full_keys_block,
                                    scorer=scorer_stage2_runtime,
                                    wli=None,
                                    key_dtype=np.int16,
                                    chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                                    require_batch=bool(REQUIRE_BATCH_SCORING),
                                )
                                pass2_evals += int(len(tail_block))
                                stage2_evals_total += int(len(tail_block))
                                for j, _tail in enumerate(tail_block):
                                    pt2 = np.asarray(pt_block[j], dtype=np.uint8).reshape(-1)
                                    full_key = full_keys_block[j]
                                    m2 = base._match_ratio(pt2.tolist(), pt_idx.tolist())
                                    sc2 = float(sc_block[j])
                                    _consider_stage2_candidate(
                                        full_key_arr=full_key,
                                        pt2_arr=pt2,
                                        match_val=float(m2),
                                        score_val=float(sc2),
                                        preview_label=f"stage2_exact_best_sub{i+1}",
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
                                seconds=0.0,
                                evals=int(stage2_evals_total),
                                pass1_evals=int(pass1_evals),
                                pass2_evals=int(pass2_evals),
                                pass2_shortlist=int(len(shortlist_tails)),
                                pass1_top_cap=int(pass1_top_tails),
                                exact_sub_limit=int(exact_sub_limit),
                                early_stop=int(bool(exact_early_stop)),
                                pass1_scorer_used=str(pass1_scorer_used),
                                pass1_fallback_used=int(bool(pass1_fallback_used)),
                                pass1_primary_unique_first=float(pass1_primary_metrics.get("unique_first", np.nan)),
                                pass1_primary_mean_hamming=float(pass1_primary_metrics.get("mean_hamming", np.nan)),
                                pass1_used_unique_first=float(pass1_used_metrics.get("unique_first", np.nan)),
                                pass1_used_mean_hamming=float(pass1_used_metrics.get("mean_hamming", np.nan)),
                            )
                        )
                        if exact_early_stop:
                            break
                    print(
                        f"[pipeline_no_wli] stage2-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"mode=exact best_match_ratio={float(best2_match):.3f} "
                        f"best_score_at_best_match={float(best2_score):.6f} evals={int(stage2_evals_total)}",
                        flush=True,
                    )
                else:
                    hybrid_subs = sub_candidates[: max(1, int(hybrid_sub_limit))]
                    for i, sub_key in enumerate(hybrid_subs):
                        t_s2 = time.time()
                        inter = sub_cipher.decrypt_single(ciphertext=ct_idx, key=np.asarray(sub_key, dtype=np.int16))
                        solver_stage2_cfg = dict(SOLVER_STAGE2)
                        solver_stage2_cfg["seed"] = int(solver_stage2_cfg.get("seed", 2026)) + 131 * int(i) + int(key_seed)
                        sol2 = run(
                            text=np.asarray(inter, dtype=np.uint8).tolist(),
                            cipher=by_name.cipher("columnar", key_length=tier.columns),
                            key=KeySpec.permutation(len=tier.columns),
                            solver=SolverSpec.hybrid(**solver_stage2_cfg),
                            scorer_params=scorer_full,
                            wli_data=[],
                            encoding_dir=direction,
                            telemetry_on=True,
                            force_no_wli=True,
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
                        _judge_scores, _judge_stats = score_plaintexts_chunked(
                            scorer=scorer_stage2_runtime,
                            plaintexts=[pt2],
                            wli=None,
                            chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                            require_batch=bool(REQUIRE_BATCH_SCORING),
                        )
                        sc2 = float(_judge_scores[0]) if _judge_scores.size > 0 else float("nan")
                        stages.append(
                            dict(
                                tier=tier.name,
                                text_id=int(text_id),
                                key_seed=int(key_seed),
                                stage=f"stage2_col_attempt_{i+1}",
                                score=float(sc2),
                                match_ratio=float(m2),
                                seconds=round(dt2, 3),
                                evals=int(ev2),
                            )
                        )
                        _consider_stage2_candidate(
                            full_key_arr=full_key,
                            pt2_arr=pt2,
                            match_val=float(m2),
                            score_val=float(sc2),
                            preview_label=f"stage2_best_attempt_{i+1}",
                        )
                    print(
                        f"[pipeline_no_wli] stage2-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"mode=hybrid best_match_ratio={float(best2_match):.3f} "
                        f"best_score_at_best_match={float(best2_score):.6f} "
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
                stage2_best_entry: Dict[str, Any] | None = None
                stage2_best_key_t: Tuple[int, ...] = tuple()
                if best2_key is not None:
                    stage2_best_key_t = tuple(int(x) for x in best2_key)
                    if stage2_best_key_t and stage2_best_key_t in stage2_archive:
                        stage2_best_entry = dict(stage2_archive[stage2_best_key_t])
                    elif stage2_best_key_t and best2_pt is not None:
                        stage2_best_entry = dict(
                            key=list(map(int, best2_key)),
                            score=float(best2_score),
                            match=float(best2_match),
                            plaintext=list(map(int, best2_pt)),
                            preview=str(best2_preview),
                        )
                # Elitism guard: never let the Stage-2 best candidate be excluded from the
                # Stage-3 bridge pool when ranking/pruning by score.
                stage2_ranked = _ensure_best_entry_in_ranked(
                    ranked_entries=stage2_ranked,
                    best_entry=stage2_best_entry,
                )
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
                stage2_promote_mode = "score_match_interleave"

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
                stage2_entry_score_judge = float("-inf")
                stage2_judge_pool_size = _stage2_judge_pool_limit(
                    ranked_count=len(stage2_ranked),
                    archive_keep=int(stage2_archive_keep),
                    stage3_scorer_cfg=dict(SCORER_FULL),
                )
                stage2_judge_entries = stage2_ranked[: int(stage2_judge_pool_size)]
                stage2_judge_plaintexts: List[np.ndarray] = []
                stage2_judge_map: List[int] = []
                for rank_idx, ent in enumerate(stage2_judge_entries, start=1):
                    pt_list = ent.get("plaintext", [])
                    if isinstance(pt_list, list) and pt_list:
                        stage2_judge_plaintexts.append(np.asarray(pt_list, dtype=np.uint8).reshape(-1))
                        stage2_judge_map.append(int(rank_idx))
                stage2_judge_scores: Dict[int, float] = {}
                if stage2_judge_plaintexts:
                    _judge_scores, _judge_stats = score_plaintexts_chunked(
                        scorer=scorer_full_runtime,
                        plaintexts=stage2_judge_plaintexts,
                        wli=None,
                        chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                        require_batch=bool(REQUIRE_BATCH_SCORING),
                    )
                    for idx, rank_idx in enumerate(stage2_judge_map):
                        if idx < int(_judge_scores.size):
                            stage2_judge_scores[int(rank_idx)] = float(_judge_scores[idx])
                if 1 in stage2_judge_scores:
                    stage2_entry_score_judge = float(stage2_judge_scores[1])
                if (not np.isfinite(stage2_entry_score_judge)) and np.isfinite(stage2_entry_score):
                    stage2_entry_score_judge = float(stage2_entry_score)

                if bool(STAGE2_PROMOTE_BY_STAGE3_JUDGE) and _is_avg_fulltext_scorer(SCORER_FULL) and stage2_judge_scores:
                    judged_entries: List[Dict[str, Any]] = []
                    for rank_idx, ent in enumerate(stage2_judge_entries, start=1):
                        judge_sc = float(stage2_judge_scores.get(int(rank_idx), float("nan")))
                        if not np.isfinite(judge_sc):
                            continue
                        enriched = dict(ent)
                        enriched["judge_score"] = float(judge_sc)
                        judged_entries.append(enriched)
                    if judged_entries:
                        by_judge = sorted(
                            judged_entries,
                            key=lambda e: (
                                float(e.get("judge_score", float("-inf"))),
                                float(e.get("match", float("-inf"))),
                            ),
                            reverse=True,
                        )
                        by_match = sorted(
                            judged_entries,
                            key=lambda e: (
                                float(e.get("match", float("-inf"))),
                                float(e.get("judge_score", float("-inf"))),
                            ),
                            reverse=True,
                        )
                        stage2_promoted = []
                        stage2_promoted_seen = set()
                        max_jrank = max(len(by_judge), len(by_match))
                        for r in range(max_jrank):
                            if len(stage2_promoted) >= int(stage2_promote_top):
                                break
                            if r < len(by_judge):
                                _push_promoted(by_judge[r])
                            if len(stage2_promoted) >= int(stage2_promote_top):
                                break
                            if r < len(by_match):
                                _push_promoted(by_match[r])
                        stage2_promote_mode = "judge_match_interleave"

                stage2_promoted, stage2_best_in_promoted = _ensure_best_entry_in_promoted(
                    promoted_entries=stage2_promoted,
                    best_entry=stage2_best_entry,
                    promote_top=int(stage2_promote_top),
                )
                stage2_promoted_seen = {
                    _entry_key_tuple(ent)
                    for ent in stage2_promoted
                    if _entry_key_tuple(ent)
                }

                stage2_topk_payload: List[Dict[str, Any]] = []
                for rank_idx, ent in enumerate(stage2_kept_by_score[: int(SAVE_STAGE2_TOPK)], start=1):
                    key_list = list(map(int, ent.get("key", [])))
                    pt_list = list(map(int, ent.get("plaintext", [])))
                    judge_sc = float(stage2_judge_scores.get(int(rank_idx), float("nan")))
                    stage2_topk_payload.append(
                        dict(
                            rank=int(rank_idx),
                            score_stage2=float(ent.get("score", float("nan"))),
                            score_judge=float(judge_sc),
                            match_ratio=float(ent.get("match", float("nan"))),
                            key_idx=key_list,
                            plaintext_idx=pt_list,
                        )
                    )
                stage2_topk_has_best_match = False
                if stage2_best_entry is not None:
                    best2_t = _entry_key_tuple(stage2_best_entry)
                    payload_key_set = {
                        tuple(int(x) for x in row.get("key_idx", []))
                        for row in stage2_topk_payload
                        if isinstance(row.get("key_idx"), list) and row.get("key_idx")
                    }
                    stage2_topk_has_best_match = bool(best2_t in payload_key_set)
                    if (not stage2_topk_has_best_match) and best2_t:
                        best2_pt = np.asarray(stage2_best_entry.get("plaintext", []), dtype=np.uint8).reshape(-1)
                        best2_judge = float("nan")
                        if best2_pt.size > 0:
                            _judge_arr, _judge_stats = score_plaintexts_chunked(
                                scorer=scorer_full_runtime,
                                plaintexts=[best2_pt],
                                wli=None,
                                chunk_size=1,
                                require_batch=bool(REQUIRE_BATCH_SCORING),
                            )
                            if _judge_arr.size > 0:
                                best2_judge = float(_judge_arr[0])
                        stage2_topk_payload.append(
                            dict(
                                rank=int(len(stage2_topk_payload) + 1),
                                score_stage2=float(stage2_best_entry.get("score", float("nan"))),
                                score_judge=float(best2_judge),
                                match_ratio=float(stage2_best_entry.get("match", float("nan"))),
                                key_idx=list(map(int, stage2_best_entry.get("key", []))),
                                plaintext_idx=list(map(int, stage2_best_entry.get("plaintext", []))),
                                tag="best_match_injected",
                            )
                        )
                        stage2_topk_has_best_match = True
                print(
                    f"[pipeline_no_wli] stage2-archive tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"entries={len(stage2_archive)} kept={len(stage2_ranked)} promoted={len(stage2_promoted)} "
                    f"judge_pool={int(stage2_judge_pool_size)} promoted_by={stage2_promote_mode} "
                    f"best2_in_promoted={1 if stage2_best_in_promoted else 0} "
                    f"best2_in_stage2_topk={1 if stage2_topk_has_best_match else 0} "
                    f"top_score_mid_rank1={float(stage2_entry_score) if np.isfinite(stage2_entry_score) else float('nan'):.6f} "
                    f"top_score_judge_rank1={float(stage2_entry_score_judge) if np.isfinite(stage2_entry_score_judge) else float('nan'):.6f} "
                    f"top_match_ratio={float(best2_match) if np.isfinite(best2_match) else float('nan'):.3f}",
                    flush=True,
                )

                # Stage 3: full refine seeded from promoted Stage-2 basins.
                best3_match, best3_score, stop_reason = float("nan"), float("nan"), "completed_pipeline"
                ev3 = 0
                stage2_gap_to_oracle = float("nan")
                stage3_band_name = ""
                pt3 = np.asarray([], dtype=np.uint8)
                best3_key: List[int] | None = None
                stage3_topk_payload: List[Dict[str, Any]] = []
                stage3_init_target = 0
                stage3_init_actual = 0
                stage3_promoted_keys_count = 0
                stage3_gate_source = ""
                stage3_phaseB_top_n_cfg = 0
                stage3_phaseB_gate_delta_cfg = float("nan")
                stage3_phaseB_gate_end_gain_cfg = float("nan")
                if np.isfinite(best2_match) and best2_match >= SOLVE_MATCH_THRESHOLD:
                    stop_reason = "solved_stage2"
                elif best2_key is not None:
                    t_s3 = time.time()
                    c1_focus_enabled = bool(STAGE3_C1_FOCUS_ENABLED and int(tier.columns) <= 1)
                    init3_n_base = int(STAGE3_INITIAL_KEYS_BY_COLUMNS.get(int(tier.columns), STAGE3_INITIAL_KEYS))
                    init3_n = int(max(init3_n_base, int(STAGE3_C1_INIT_KEYS))) if c1_focus_enabled else int(init3_n_base)
                    promoted_keys = _build_stage3_promoted_keys(
                        promoted_entries=stage2_promoted,
                        best_key=best2_key,
                        key_len=int(key_len),
                    )
                    if not promoted_keys:
                        promoted_keys = [list(map(int, best2_key))]
                    stage3_promoted_keys_count = int(len(promoted_keys))

                    per_seed = max(1, int(np.ceil(float(init3_n) / float(len(promoted_keys)))))
                    init3_all: List[List[int]] = []
                    for j, seed_key in enumerate(promoted_keys):
                        init3_all.append(list(map(int, seed_key)))
                        init3_all.extend(
                            _mutate_full_key(
                                seed_key,
                                period=tier.period,
                                columns=tier.columns,
                                seed=7000 + int(key_seed) + 97 * int(j),
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
                    stage3_init_target = int(init3_n)
                    stage3_init_actual = int(len(init3))

                    solver_stage3_cfg = dict(SOLVER_STAGE3)
                    stage2_gate_source = "mid"
                    if bool(STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE) and np.isfinite(stage2_entry_score_judge):
                        stage2_gate_score = float(stage2_entry_score_judge)
                        stage2_gate_source = "judge"
                    else:
                        stage2_gate_score = float(stage2_entry_score)
                        stage2_gate_source = "mid"
                    stage3_gate_source = str(stage2_gate_source)
                    promoted_best_match = float("nan")
                    if stage2_promoted:
                        promoted_match_vals = [
                            float(ent.get("match", float("nan"))) for ent in stage2_promoted
                        ]
                        finite_promoted = [v for v in promoted_match_vals if np.isfinite(v)]
                        if finite_promoted:
                            promoted_best_match = float(max(finite_promoted))
                    if np.isfinite(best2_match):
                        promoted_best_match = (
                            float(best2_match)
                            if (not np.isfinite(promoted_best_match))
                            else float(max(float(promoted_best_match), float(best2_match)))
                        )
                    if np.isfinite(stage2_gate_score) and np.isfinite(oracle_s3):
                        stage2_gap_to_oracle = max(0.0, float(oracle_s3) - float(stage2_gate_score))
                    else:
                        stage2_gap_to_oracle = float("inf")
                    band = _select_stage3_band(stage2_gap_to_oracle)
                    stage3_band_name = str(band.get("name", ""))
                    stage3_phaseA_cfg = dict(STAGE3_PHASEA_CFG)
                    stage3_phaseB_cfg = dict(STAGE3_PHASEB_CFG)
                    stage3_phaseB_top_n = int(STAGE3_PHASEB_TOP_N)
                    stage3_phaseB_gate_delta = float(STAGE3_PHASEB_GATE_DELTA_FLOOR)
                    stage3_phaseB_gate_end_gain = float(STAGE3_PHASEB_GATE_END_GAIN_FLOOR)
                    if c1_focus_enabled:
                        stage3_phaseA_cfg["steps"] = int(max(int(stage3_phaseA_cfg.get("steps", 0)), int(STAGE3_C1_PHASEA_STEPS)))
                        stage3_phaseB_cfg["steps"] = int(max(int(stage3_phaseB_cfg.get("steps", 0)), int(STAGE3_C1_PHASEB_STEPS)))
                        stage3_phaseB_cfg["col_every"] = 0
                        stage3_phaseB_cfg["col_batch"] = 0
                        stage3_phaseB_top_n = int(max(int(stage3_phaseB_top_n), int(STAGE3_C1_PHASEB_TOP_N)))
                        stage3_phaseB_gate_delta = float(max(float(stage3_phaseB_gate_delta), float(STAGE3_C1_PHASEB_GATE_DELTA_FLOOR)))
                        stage3_phaseB_gate_end_gain = float(max(float(stage3_phaseB_gate_end_gain), float(STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR)))
                    stage3_phaseB_top_n_cfg = int(stage3_phaseB_top_n)
                    stage3_phaseB_gate_delta_cfg = float(stage3_phaseB_gate_delta)
                    stage3_phaseB_gate_end_gain_cfg = float(stage3_phaseB_gate_end_gain)
                    solver_stage3_cfg.update(
                        steps=int(band.get("steps", solver_stage3_cfg.get("steps", 0))),
                        restarts=int(band.get("restarts", solver_stage3_cfg.get("restarts", 0))),
                        plateau_rounds=int(band.get("plateau_rounds", solver_stage3_cfg.get("plateau_rounds", 0))),
                        col_batch=int(band.get("col_batch", solver_stage3_cfg.get("col_batch", 0))),
                        inner_batch=int(band.get("inner_batch", solver_stage3_cfg.get("inner_batch", 0))),
                    )
                    print(
                        f"[pipeline_no_wli] stage3-stop tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"band={stage3_band_name} entry_mode=full entry_score={stage2_gate_score:.6f} "
                        f"entry_score_source={stage2_gate_source} "
                        f"init_keys={len(init3)} promoted_keys={len(promoted_keys)} "
                        f"init_target={int(init3_n)} c1_focus={1 if c1_focus_enabled else 0} "
                        f"stage2_best_match={float(best2_match):.3f} promoted_best_match={float(promoted_best_match):.3f} "
                        f"steps={solver_stage3_cfg.get('steps')} restarts={solver_stage3_cfg.get('restarts')} "
                        f"col_batch={solver_stage3_cfg.get('col_batch')} inner_batch={solver_stage3_cfg.get('inner_batch')} "
                        f"gap_to_oracle={stage2_gap_to_oracle:.6f}",
                        flush=True,
                    )
                    if bool(STAGE3_TWO_PHASE_ENABLED):
                        print(
                            f"[pipeline_no_wli] stage3-two-phase "
                            f"phaseA={json.dumps(dict(stage3_phaseA_cfg), separators=(',', ':'))} "
                            f"phaseB={json.dumps(dict(stage3_phaseB_cfg), separators=(',', ':'))} "
                            f"phaseB_top_n={int(stage3_phaseB_top_n)} "
                            f"gate=(delta={float(stage3_phaseB_gate_delta):.4f},"
                            f"end_gain={float(stage3_phaseB_gate_end_gain):.4f})",
                            flush=True,
                        )
                    dt3 = 0.0
                    ev3 = 0
                    slip_count = 0
                    slip_accept_count = 0
                    slip_accept_rate = float("nan")
                    accept_rate = float("nan")
                    phase_attempts_total = 0
                    phase_improves_total = 0
                    phase_best_delta_max = float("nan")
                    phaseA_best_delta = float("nan")
                    phaseA_best_start_score = float("nan")
                    phaseA_best_end_score = float("nan")
                    phaseB_top_n_used = 0
                    phaseB_skipped = 0
                    phaseB_ran = 0
                    phaseB_skip_reason = ""

                    def _extract_kaeding_metrics(kaeding_obj: Any) -> Dict[str, float]:
                        if not isinstance(kaeding_obj, dict):
                            return dict(
                                slip_count=0,
                                slip_accept_count=0,
                                slip_accept_rate=float("nan"),
                                accept_rate=float("nan"),
                                phase_attempts_total=0,
                                phase_improves_total=0,
                                phase_best_delta_max=float("nan"),
                            )
                        _slip_count = int(kaeding_obj.get("slip_count", 0) or 0)
                        _accept_rate = float(kaeding_obj.get("accept_rate", float("nan")))
                        _slips_list = kaeding_obj.get("slips", [])
                        _slip_accept_count = 0
                        if isinstance(_slips_list, list):
                            for rec in _slips_list:
                                if not isinstance(rec, dict):
                                    continue
                                raw_before = float(rec.get("raw_before", float("nan")))
                                raw_after = float(rec.get("raw_after", float("nan")))
                                if np.isfinite(raw_before) and np.isfinite(raw_after) and raw_after > raw_before:
                                    _slip_accept_count += 1
                        _slip_accept_rate = (
                            float(_slip_accept_count) / float(max(1, _slip_count)) if _slip_count > 0 else float("nan")
                        )
                        _phase_attempts_total = 0
                        _phase_improves_total = 0
                        _phase_best_delta_max = float("nan")
                        per_phase = kaeding_obj.get("per_phase", {})
                        if isinstance(per_phase, dict) and per_phase:
                            delta_vals: List[float] = []
                            for rec in per_phase.values():
                                if not isinstance(rec, dict):
                                    continue
                                _phase_attempts_total += int(rec.get("attempts", 0) or 0)
                                _phase_improves_total += int(rec.get("improves", 0) or 0)
                                d = rec.get("best_delta_raw", None)
                                if d is not None and np.isfinite(float(d)):
                                    delta_vals.append(float(d))
                            if delta_vals:
                                _phase_best_delta_max = float(max(delta_vals))
                        return dict(
                            slip_count=int(_slip_count),
                            slip_accept_count=int(_slip_accept_count),
                            slip_accept_rate=float(_slip_accept_rate),
                            accept_rate=float(_accept_rate),
                            phase_attempts_total=int(_phase_attempts_total),
                            phase_improves_total=int(_phase_improves_total),
                            phase_best_delta_max=float(_phase_best_delta_max),
                        )

                    def _append_stage3_topk(kaeding_obj: Any) -> None:
                        if (not bool(SAVE_STAGE3_TOPK)) or (not isinstance(kaeding_obj, dict)):
                            return
                        top_keys = kaeding_obj.get("top_keys", [])
                        top_raw = kaeding_obj.get("top_raw", [])
                        top_pct = kaeding_obj.get("top_pct", [])
                        if not isinstance(top_keys, list):
                            return
                        top_key_records: List[Tuple[int, List[int]]] = []
                        for rank_idx, key_vals in enumerate(top_keys[: int(SAVE_STAGE3_TOPK_LIMIT)], start=1):
                            if not isinstance(key_vals, list):
                                continue
                            key_list = list(map(int, key_vals))
                            if len(key_list) != int(key_len):
                                continue
                            top_key_records.append((int(rank_idx), key_list))
                        if not top_key_records:
                            return
                        eval_keys = [key_list for _rank_idx, key_list in top_key_records]
                        pt_batch, judge_scores, _judge_stats = decrypt_and_score_keys_chunked(
                            cipher=full_cipher,
                            ciphertext=ct_idx,
                            keys=eval_keys,
                            scorer=scorer_full_runtime,
                            wli=None,
                            chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                            require_batch=bool(REQUIRE_BATCH_SCORING),
                        )
                        for idx, (rank_idx, key_list) in enumerate(top_key_records):
                            pt_k = np.asarray(pt_batch[idx], dtype=np.uint8).reshape(-1)
                            judge_sc = float(judge_scores[idx]) if idx < int(judge_scores.size) else float("nan")
                            stage3_topk_payload.append(
                                dict(
                                    rank=int(rank_idx),
                                    score_raw=(
                                        float(top_raw[rank_idx - 1])
                                        if isinstance(top_raw, list) and (rank_idx - 1) < len(top_raw)
                                        else float("nan")
                                    ),
                                    score_pct=(
                                        float(top_pct[rank_idx - 1])
                                        if isinstance(top_pct, list) and (rank_idx - 1) < len(top_pct)
                                        else float("nan")
                                    ),
                                    score_judge=float(judge_sc),
                                    match_ratio=float(base._match_ratio(pt_k.tolist(), pt_idx.tolist())),
                                    key_idx=key_list,
                                    plaintext_idx=pt_k.astype(int).tolist(),
                                )
                            )

                    if not bool(STAGE3_TWO_PHASE_ENABLED):
                        t_run = time.time()
                        sol3 = run(
                            text=ct_idx.tolist(),
                            cipher=by_name.cipher("periodic_columnar", period=tier.period, columns=tier.columns, order=ORDER, alphabet_size=ALPHABET_SIZE),
                            key=KeySpec.periodic_columnar(period=tier.period, columns=tier.columns, alphabet_size=ALPHABET_SIZE),
                            solver=SolverSpec.kaeding(**solver_stage3_cfg),
                            scorer_params=scorer_full,
                            wli_data=[],
                            encoding_dir=direction,
                            telemetry_on=True,
                            force_no_wli=True,
                            initial_keys=init3,
                        )
                        dt3 += float(time.time() - t_run)
                        ev3 += int((getattr(sol3, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
                        pt3 = np.asarray(getattr(sol3, "plaintext_idx", []) or [], dtype=np.uint8).reshape(-1)
                        k3_arr = np.asarray(getattr(sol3, "key", []) or [], dtype=np.int16).reshape(-1)
                        if k3_arr.size == int(key_len):
                            best3_key = k3_arr.astype(int).tolist()
                        best3_match = base._match_ratio(pt3.tolist(), pt_idx.tolist())
                        best3_score = float(getattr(sol3, "score", float("nan")))
                        tele3 = (getattr(sol3, "meta", {}) or {}).get("telemetry", {})
                        kaeding3 = tele3.get("kaeding", {}) if isinstance(tele3, dict) else {}
                        mm = _extract_kaeding_metrics(kaeding3)
                        slip_count = int(mm["slip_count"])
                        slip_accept_count = int(mm["slip_accept_count"])
                        slip_accept_rate = float(mm["slip_accept_rate"])
                        accept_rate = float(mm["accept_rate"])
                        phase_attempts_total = int(mm["phase_attempts_total"])
                        phase_improves_total = int(mm["phase_improves_total"])
                        phase_best_delta_max = float(mm["phase_best_delta_max"])
                        _append_stage3_topk(kaeding3)
                    else:
                        base_seed = int(solver_stage3_cfg.get("seed", SOLVER_STAGE3.get("seed", 2026)))
                        phaseA_cfg = dict(solver_stage3_cfg)
                        phaseA_cfg.update(dict(stage3_phaseA_cfg))
                        phaseA_cfg["restarts"] = 1
                        phaseA_cfg["seed_restarts"] = 0

                        phaseA_rows: List[Dict[str, Any]] = []
                        phaseA_seed_keys = [list(map(int, seed_key)) for seed_key in init3]
                        phaseA_start_pts, phaseA_start_scores, _phaseA_batch_stats = decrypt_and_score_keys_chunked(
                            cipher=full_cipher,
                            ciphertext=ct_idx,
                            keys=phaseA_seed_keys,
                            scorer=scorer_full_runtime,
                            wli=None,
                            chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                            require_batch=bool(REQUIRE_BATCH_SCORING),
                        )
                        for restart_idx, seed_key in enumerate(init3):
                            seed_key_arr = np.asarray(seed_key, dtype=np.int16).reshape(-1)
                            start_pt = (
                                np.asarray(phaseA_start_pts[restart_idx], dtype=np.uint8).reshape(-1)
                                if restart_idx < len(phaseA_start_pts)
                                else np.asarray(
                                    full_cipher.decrypt_single(ciphertext=ct_idx, key=seed_key_arr),
                                    dtype=np.uint8,
                                ).reshape(-1)
                            )
                            start_score = (
                                float(phaseA_start_scores[restart_idx])
                                if restart_idx < int(phaseA_start_scores.size)
                                else float("nan")
                            )
                            start_hash = _key_hash16(seed_key_arr.astype(int).tolist())
                            seed_offset = int((restart_idx + 1) * 10007)

                            cfg_i = dict(phaseA_cfg)
                            cfg_i["seed"] = int(base_seed + seed_offset)

                            t_run = time.time()
                            sol_i = run(
                                text=ct_idx.tolist(),
                                cipher=by_name.cipher("periodic_columnar", period=tier.period, columns=tier.columns, order=ORDER, alphabet_size=ALPHABET_SIZE),
                                key=KeySpec.periodic_columnar(period=tier.period, columns=tier.columns, alphabet_size=ALPHABET_SIZE),
                                solver=SolverSpec.kaeding(**cfg_i),
                                scorer_params=scorer_full,
                                wli_data=[],
                                encoding_dir=direction,
                                telemetry_on=True,
                                force_no_wli=True,
                                initial_keys=[seed_key_arr.astype(int).tolist()],
                            )
                            dt_run = float(time.time() - t_run)
                            dt3 += float(dt_run)
                            ev_i = int((getattr(sol_i, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
                            ev3 += int(ev_i)

                            pt_i = np.asarray(getattr(sol_i, "plaintext_idx", []) or [], dtype=np.uint8).reshape(-1)
                            k_i_arr = np.asarray(getattr(sol_i, "key", []) or [], dtype=np.int16).reshape(-1)
                            end_key_list = seed_key_arr.astype(int).tolist()
                            if k_i_arr.size == int(key_len):
                                end_key_list = k_i_arr.astype(int).tolist()
                            end_hash = _key_hash16(end_key_list)
                            end_score = float(getattr(sol_i, "score", float("nan")))
                            end_match = float(base._match_ratio(pt_i.tolist(), pt_idx.tolist())) if pt_i.size > 0 else float("nan")
                            best_delta = float(end_score - start_score) if np.isfinite(end_score) and np.isfinite(start_score) else float("nan")

                            tele_i = (getattr(sol_i, "meta", {}) or {}).get("telemetry", {})
                            kaeding_i = tele_i.get("kaeding", {}) if isinstance(tele_i, dict) else {}
                            mm_i = _extract_kaeding_metrics(kaeding_i)

                            phaseA_rows.append(
                                dict(
                                    restart_idx=int(restart_idx),
                                    seed_offset=int(seed_offset),
                                    start_hash=str(start_hash),
                                    end_hash=str(end_hash),
                                    start_score=float(start_score),
                                    end_score=float(end_score),
                                    best_delta=float(best_delta),
                                    end_match=float(end_match),
                                    end_key=list(map(int, end_key_list)),
                                    end_plaintext=pt_i.astype(int).tolist(),
                                    metrics=mm_i,
                                )
                            )
                            stages.append(
                                dict(
                                    tier=tier.name,
                                    text_id=int(text_id),
                                    key_seed=int(key_seed),
                                    stage="stage3_phaseA_restart",
                                    restart_idx=int(restart_idx),
                                    seed_offset=int(seed_offset),
                                    start_hash=str(start_hash),
                                    end_hash=str(end_hash),
                                    start_score=float(start_score),
                                    end_score=float(end_score),
                                    score=float(end_score),
                                    best_delta=float(best_delta),
                                    match_ratio=float(end_match),
                                    seconds=round(dt_run, 3),
                                    evals=int(ev_i),
                                    slip_count=int(mm_i["slip_count"]),
                                    slip_accept_count=int(mm_i["slip_accept_count"]),
                                    slip_accept_rate=float(mm_i["slip_accept_rate"]),
                                    accept_rate=float(mm_i["accept_rate"]),
                                )
                            )

                        phaseA_start_scores = [float(r["start_score"]) for r in phaseA_rows if np.isfinite(float(r["start_score"]))]
                        phaseA_end_scores = [float(r["end_score"]) for r in phaseA_rows if np.isfinite(float(r["end_score"]))]
                        phaseA_deltas = [float(r["best_delta"]) for r in phaseA_rows if np.isfinite(float(r["best_delta"]))]
                        phaseA_best_start_score = float(max(phaseA_start_scores)) if phaseA_start_scores else float("nan")
                        phaseA_best_end_score = float(max(phaseA_end_scores)) if phaseA_end_scores else float("nan")
                        phaseA_best_delta = float(max(phaseA_deltas)) if phaseA_deltas else float("nan")

                        # Keep best observed candidate from phase A as fallback/final.
                        if phaseA_rows:
                            phaseA_best = max(
                                phaseA_rows,
                                key=lambda r: (float(r["end_score"]), float(r["end_match"]) if np.isfinite(float(r["end_match"])) else float("-inf")),
                            )
                            best3_score = float(phaseA_best["end_score"])
                            best3_match = float(phaseA_best["end_match"]) if np.isfinite(float(phaseA_best["end_match"])) else float("nan")
                            best3_key = list(map(int, phaseA_best["end_key"]))
                            pt3 = np.asarray(phaseA_best["end_plaintext"], dtype=np.uint8).reshape(-1)
                            mm_best = dict(phaseA_best["metrics"])
                            slip_count = int(mm_best["slip_count"])
                            slip_accept_count = int(mm_best["slip_accept_count"])
                            slip_accept_rate = float(mm_best["slip_accept_rate"])
                            accept_rate = float(mm_best["accept_rate"])
                            phase_attempts_total = int(mm_best["phase_attempts_total"])
                            phase_improves_total = int(mm_best["phase_improves_total"])
                            phase_best_delta_max = float(mm_best["phase_best_delta_max"])

                        gate_delta = float(stage3_phaseB_gate_delta)
                        gate_end_gain = float(stage3_phaseB_gate_end_gain)
                        gate_skip = (
                            np.isfinite(phaseA_best_delta)
                            and np.isfinite(phaseA_best_start_score)
                            and np.isfinite(phaseA_best_end_score)
                            and (float(phaseA_best_delta) < gate_delta)
                            and (float(phaseA_best_end_score) < float(phaseA_best_start_score) + gate_end_gain)
                        )
                        stages.append(
                            dict(
                                tier=tier.name,
                                text_id=int(text_id),
                                key_seed=int(key_seed),
                                stage="stage3_phaseB_gate",
                                phaseA_best_delta=float(phaseA_best_delta),
                                phaseA_best_start_score=float(phaseA_best_start_score),
                                phaseA_best_end_score=float(phaseA_best_end_score),
                                gate_delta_floor=float(gate_delta),
                                gate_end_gain_floor=float(gate_end_gain),
                                phaseB_skipped=int(1 if gate_skip else 0),
                                phaseB_top_n=int(stage3_phaseB_top_n),
                            )
                        )

                        if gate_skip:
                            phaseB_skipped = 1
                            phaseB_skip_reason = "phaseA_low_progress"
                            stop_reason = "stage3_phaseb_skipped"
                        else:
                            top_n = max(1, int(stage3_phaseB_top_n))
                            ranked = sorted(
                                phaseA_rows,
                                key=lambda r: (
                                    float(r["end_score"]),
                                    float(r["best_delta"]) if np.isfinite(float(r["best_delta"])) else float("-inf"),
                                    -int(r["restart_idx"]),
                                ),
                                reverse=True,
                            )
                            selected: List[Dict[str, Any]] = []
                            seen_basin: set[Tuple[str, str]] = set()
                            for row in ranked:
                                basin_id = (str(row["start_hash"]), str(row["end_hash"]))
                                if basin_id in seen_basin:
                                    continue
                                seen_basin.add(basin_id)
                                selected.append(row)
                                if len(selected) >= top_n:
                                    break
                            if not selected and ranked:
                                selected = [ranked[0]]
                            phaseB_top_n_used = int(len(selected))
                            phaseB_ran = int(1 if selected else 0)
                            if selected:
                                phaseB_init = [list(map(int, row["end_key"])) for row in selected]
                                phaseB_cfg = dict(solver_stage3_cfg)
                                phaseB_cfg.update(dict(stage3_phaseB_cfg))
                                phaseB_cfg["restarts"] = int(max(1, len(phaseB_init)))
                                phaseB_cfg["seed_restarts"] = 0
                                phaseB_cfg["seed"] = int(base_seed + 900001)
                                t_run = time.time()
                                sol_b = run(
                                    text=ct_idx.tolist(),
                                    cipher=by_name.cipher("periodic_columnar", period=tier.period, columns=tier.columns, order=ORDER, alphabet_size=ALPHABET_SIZE),
                                    key=KeySpec.periodic_columnar(period=tier.period, columns=tier.columns, alphabet_size=ALPHABET_SIZE),
                                    solver=SolverSpec.kaeding(**phaseB_cfg),
                                    scorer_params=scorer_full,
                                    wli_data=[],
                                    encoding_dir=direction,
                                    telemetry_on=True,
                                    force_no_wli=True,
                                    initial_keys=phaseB_init,
                                )
                                dt_run = float(time.time() - t_run)
                                dt3 += float(dt_run)
                                ev_b = int((getattr(sol_b, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
                                ev3 += int(ev_b)

                                pt_b = np.asarray(getattr(sol_b, "plaintext_idx", []) or [], dtype=np.uint8).reshape(-1)
                                k_b_arr = np.asarray(getattr(sol_b, "key", []) or [], dtype=np.int16).reshape(-1)
                                best_b_key = best3_key if best3_key is not None else list(map(int, phaseB_init[0]))
                                if k_b_arr.size == int(key_len):
                                    best_b_key = k_b_arr.astype(int).tolist()
                                best_b_score = float(getattr(sol_b, "score", float("nan")))
                                best_b_match = float(base._match_ratio(pt_b.tolist(), pt_idx.tolist())) if pt_b.size > 0 else float("nan")
                                tele_b = (getattr(sol_b, "meta", {}) or {}).get("telemetry", {})
                                kaeding_b = tele_b.get("kaeding", {}) if isinstance(tele_b, dict) else {}
                                mm_b = _extract_kaeding_metrics(kaeding_b)

                                stages.append(
                                    dict(
                                        tier=tier.name,
                                        text_id=int(text_id),
                                        key_seed=int(key_seed),
                                        stage="stage3_phaseB",
                                        phaseB_top_n_used=int(phaseB_top_n_used),
                                        score=float(best_b_score),
                                        match_ratio=float(best_b_match),
                                        seconds=round(dt_run, 3),
                                        evals=int(ev_b),
                                        slip_count=int(mm_b["slip_count"]),
                                        slip_accept_count=int(mm_b["slip_accept_count"]),
                                        slip_accept_rate=float(mm_b["slip_accept_rate"]),
                                        accept_rate=float(mm_b["accept_rate"]),
                                        phase_attempts_total=int(mm_b["phase_attempts_total"]),
                                        phase_improves_total=int(mm_b["phase_improves_total"]),
                                        phase_best_delta_max=float(mm_b["phase_best_delta_max"]),
                                    )
                                )

                                if np.isfinite(best_b_score) and (not np.isfinite(best3_score) or best_b_score > best3_score):
                                    best3_score = float(best_b_score)
                                    best3_match = float(best_b_match)
                                    best3_key = list(map(int, best_b_key))
                                    pt3 = pt_b.copy()
                                    slip_count = int(mm_b["slip_count"])
                                    slip_accept_count = int(mm_b["slip_accept_count"])
                                    slip_accept_rate = float(mm_b["slip_accept_rate"])
                                    accept_rate = float(mm_b["accept_rate"])
                                    phase_attempts_total = int(mm_b["phase_attempts_total"])
                                    phase_improves_total = int(mm_b["phase_improves_total"])
                                    phase_best_delta_max = float(mm_b["phase_best_delta_max"])
                                _append_stage3_topk(kaeding_b)
                    stages.append(
                        dict(
                            tier=tier.name,
                            text_id=int(text_id),
                            key_seed=int(key_seed),
                            stage="stage3_full_refine",
                            score=float(best3_score),
                            match_ratio=float(best3_match),
                            seconds=round(dt3, 3),
                            evals=ev3,
                            stage3_band=stage3_band_name,
                            stage2_gap_to_oracle=float(stage2_gap_to_oracle),
                            slip_count=int(slip_count),
                            slip_accept_count=int(slip_accept_count),
                            slip_accept_rate=float(slip_accept_rate),
                            accept_rate=float(accept_rate),
                            phase_attempts_total=int(phase_attempts_total),
                            phase_improves_total=int(phase_improves_total),
                            phase_best_delta_max=float(phase_best_delta_max),
                            stage3_two_phase=int(bool(STAGE3_TWO_PHASE_ENABLED)),
                            phaseA_best_delta=float(phaseA_best_delta),
                            phaseA_best_start_score=float(phaseA_best_start_score),
                            phaseA_best_end_score=float(phaseA_best_end_score),
                            phaseB_ran=int(phaseB_ran),
                            phaseB_skipped=int(phaseB_skipped),
                            phaseB_skip_reason=str(phaseB_skip_reason),
                            phaseB_top_n_used=int(phaseB_top_n_used),
                        )
                    )
                    if pt3.size > 0:
                        _print_stage_preview(label="stage3_full_refine", pt=pt3.tolist(), wli=wli, match_ratio=float(best3_match))
                    if np.isfinite(best3_match) and best3_match >= SOLVE_MATCH_THRESHOLD:
                        stop_reason = "solved_stage3"
                    elif (best3_match - best2_match) <= STALL_DELTA:
                        # no_wli has one post-Stage2 improvement boundary (Stage2 -> Stage3).
                        # Respect stall-stage-limit semantics without pretending there are more
                        # consecutive boundaries than exist.
                        stop_reason = "stalled_no_improve" if int(STALL_STAGE_LIMIT) <= 1 else "unsolved"
                    else:
                        stop_reason = "unsolved"
                    print(
                        f"[pipeline_no_wli] stage3-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"band={stage3_band_name} match={float(best3_match):.3f} score={float(best3_score):.6f} "
                        f"evals={ev3} two_phase={'on' if bool(STAGE3_TWO_PHASE_ENABLED) else 'off'} "
                        f"phaseB_ran={int(phaseB_ran)} phaseB_skipped={int(phaseB_skipped)} stop={stop_reason}",
                        flush=True,
                    )
                else:
                    stop_reason = "no_stage2_candidate"

                best_match = max(float(best2_match if np.isfinite(best2_match) else 0.0), float(best3_match if np.isfinite(best3_match) else 0.0))
                best_stage = "stage3_full_refine" if np.isfinite(best3_match) and best3_match >= best2_match else "stage2_search"
                status = "solved" if best_match >= SOLVE_MATCH_THRESHOLD else ("stalled" if stop_reason == "stalled_no_improve" else "unsolved")
                dt_i = float(time.time() - t0_i)
                total_evals = int(ev1 + int(stage2_evals_total) + int(ev3))
                final_best_key_idx: List[int] | None = None
                final_best_plaintext_idx: List[int] | None = None
                final_best_score = float("nan")
                if best_stage == "stage3_full_refine" and pt3.size > 0 and best3_key is not None:
                    final_best_key_idx = list(map(int, best3_key))
                    final_best_plaintext_idx = pt3.astype(int).tolist()
                    final_best_score = float(best3_score)
                elif best2_key is not None and best2_pt is not None:
                    final_best_key_idx = list(map(int, best2_key))
                    final_best_plaintext_idx = list(map(int, best2_pt))
                    final_best_score = float(best2_score)
                if best_stage == "stage3_full_refine" and pt3.size > 0:
                    preview_best = base._safe_preview_latin(pt3, wli)
                elif best2_preview:
                    preview_best = best2_preview
                else:
                    preview_best = base._safe_preview_latin(pt3, wli) if pt3.size > 0 else ""
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
                        status=status,
                        stop_reason=stop_reason,
                        solve_threshold=float(SOLVE_MATCH_THRESHOLD),
                        best_stage=best_stage,
                        best_match_ratio=float(best_match),
                        stage1_sub_key_match=float(sub_key_match),
                        stage2_match_ratio=float(best2_match if np.isfinite(best2_match) else np.nan),
                        stage3_match_ratio=float(best3_match if np.isfinite(best3_match) else np.nan),
                        stage2_gap_to_oracle=float(stage2_gap_to_oracle),
                        stage3_band=str(stage3_band_name),
                        total_seconds=round(dt_i, 3),
                        total_evals=total_evals,
                        preview_best_latin=str(preview_best),
                    )
                )
                artifact_payload: Dict[str, Any] = dict(
                    tier=str(tier.name),
                    profile_id=str(PROFILE),
                    mode=str(PIPELINE_RUN_MODE),
                    direction=str(direction.value),
                    order=str(ORDER),
                    alphabet_size=int(ALPHABET_SIZE),
                    text_id=int(text_id),
                    key_seed=int(key_seed),
                    offset_hint=int(off),
                    offset_used=int(offset_used),
                    period=int(tier.period),
                    columns=int(tier.columns),
                    length=int(tier.length),
                    status=str(status),
                    stop_reason=str(stop_reason),
                    best_stage=str(best_stage),
                    best_match_ratio=float(best_match),
                    best_score=float(final_best_score),
                    solve_threshold=float(SOLVE_MATCH_THRESHOLD),
                    ciphertext_idx=np.asarray(ct_idx, dtype=np.uint8).astype(int).tolist(),
                    target_plaintext_idx=np.asarray(pt_idx, dtype=np.uint8).astype(int).tolist(),
                    final_best_key_idx=(list(map(int, final_best_key_idx)) if final_best_key_idx is not None else []),
                    final_best_plaintext_idx=(
                        list(map(int, final_best_plaintext_idx)) if final_best_plaintext_idx is not None else []
                    ),
                    stage2_topk=stage2_topk_payload,
                    stage2_topk_has_best_match=int(1 if stage2_topk_has_best_match else 0),
                    stage3_topk=(stage3_topk_payload if bool(SAVE_STAGE3_TOPK) else []),
                    stage3_diagnostics=dict(
                        init_target=int(stage3_init_target),
                        init_actual=int(stage3_init_actual),
                        promoted_keys=int(stage3_promoted_keys_count),
                        gate_source=str(stage3_gate_source),
                        phaseB_top_n_cfg=int(stage3_phaseB_top_n_cfg),
                        phaseB_gate_delta_cfg=float(stage3_phaseB_gate_delta_cfg),
                        phaseB_gate_end_gain_cfg=float(stage3_phaseB_gate_end_gain_cfg),
                        phaseB_ran=int(phaseB_ran) if "phaseB_ran" in locals() else 0,
                        phaseB_skipped=int(phaseB_skipped) if "phaseB_skipped" in locals() else 0,
                        phaseB_top_n_used=int(phaseB_top_n_used) if "phaseB_top_n_used" in locals() else 0,
                        phaseB_skip_reason=str(phaseB_skip_reason) if "phaseB_skip_reason" in locals() else "",
                        stage3_eval_count=int(ev3),
                        c1_focus=int(1 if (int(tier.columns) <= 1 and bool(STAGE3_C1_FOCUS_ENABLED)) else 0),
                    ),
                )
                artifact_name = f"{tier.name}__text{int(text_id)}__seed{int(key_seed)}.json"
                (final_dir / artifact_name).write_text(json.dumps(artifact_payload, indent=2), encoding="utf-8")

                if best_match > float(best_global["match"]):
                    best_global.update(match=float(best_match), tier=str(tier.name), text_id=int(text_id), key_seed=int(key_seed), stage=str(best_stage), preview=str(preview_best))

                done += 1
                elapsed = time.time() - t0_all
                eta = (elapsed / float(done)) * float(total - done) if done else 0.0
                print(
                    f"[pipeline_no_wli] {done}/{total} tier={tier.name} status={status} best_match={best_match:.3f} "
                    f"run={base._format_seconds(dt_i)} elapsed={base._format_seconds(elapsed)} eta={base._format_seconds(eta)}",
                    flush=True,
                )
                if preview_best:
                    print(f"[pipeline_no_wli] best-instance-preview tier={tier.name} text={text_id} key_seed={key_seed} text=\"{preview_best}\"", flush=True)
                now = time.time()
                if (now - last_hb) >= float(HEARTBEAT_SECONDS):
                    print(
                        f"[pipeline_no_wli] heartbeat elapsed={base._format_seconds(now - t0_all)} done={done}/{total} "
                        f"global_best_match={float(best_global['match']):.3f} tier={best_global['tier']} "
                        f"text={best_global['text_id']} key_seed={best_global['key_seed']} stage={best_global['stage']} "
                        f"preview=\"{best_global['preview']}\"",
                        flush=True,
                    )
                    last_hb = now

    summary: Dict[str, Any] = {"tiers": {}}
    for t in TIERS:
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

    (run_dir / "instances.json").write_text(json.dumps(instances, indent=2), encoding="utf-8")
    (run_dir / "stages.json").write_text(json.dumps(stages, indent=2), encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_csv_rows(run_dir / "instances.csv", instances)
    _write_csv_rows(run_dir / "stages.csv", stages)
    if instances:
        best_instance = max(instances, key=lambda r: float(r.get("best_match_ratio", float("-inf"))))
        (best_dir / "best_instance.json").write_text(json.dumps(best_instance, indent=2), encoding="utf-8")
        (best_dir / "best_preview.txt").write_text(str(best_instance.get("preview_best_latin", "")), encoding="utf-8")

    hist = root / "tools" / "benchmarks" / "solve_proof" / "proven_solve_pipeline_no_wli_log.csv"
    hist.parent.mkdir(parents=True, exist_ok=True)
    hist_rows = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for r in instances:
        hist_rows.append(
            dict(
                timestamp_utc=now_iso,
                run_id=run_dir.name,
                profile_id=PROFILE,
                fixture_id=r["tier"],
                text_id=r["text_id"],
                key_seed=r["key_seed"],
                period=r["period"],
                columns=r["columns"],
                length=r["length"],
                status=r["status"],
                solve_threshold=r["solve_threshold"],
                best_match_ratio=r["best_match_ratio"],
                best_stage=r["best_stage"],
                stage1_sub_key_match=r["stage1_sub_key_match"],
                stage2_match_ratio=r["stage2_match_ratio"],
                stage3_match_ratio=r["stage3_match_ratio"],
                total_seconds=r["total_seconds"],
                total_evals=r["total_evals"],
                notes=r["stop_reason"],
            )
        )
    if hist_rows:
        cols = list(hist_rows[0].keys())
        write_header = (not hist.exists()) or hist.stat().st_size == 0
        with hist.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            if write_header:
                w.writeheader()
            w.writerows(hist_rows)

    print(f"[pipeline_no_wli] completed in {base._format_seconds(time.time() - t0_all)}", flush=True)
    print(f"[pipeline_no_wli] reports: {run_dir.relative_to(root)}", flush=True)
    print(f"[pipeline_no_wli] final_artifacts: {final_dir.relative_to(root)}", flush=True)
    print(f"[pipeline_no_wli] best: {(best_dir / 'best_instance.json').relative_to(root)}", flush=True)
    print(f"[pipeline_no_wli] history: {hist.relative_to(root)} rows={len(hist_rows)}", flush=True)


if __name__ == "__main__":
    main()
