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
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

import numpy as np


_ROOT = Path(__file__).resolve().parents[4]
_SRC = _ROOT / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import Direction
from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.ciphers.periodic_substitution_cipher import PeriodicSubstitutionCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import ScorerImpl

from tools.benchmarks.periodic_sub_trans.common import bench_solve_periodic_columnar_kaeding as base
from tools.benchmarks.periodic_sub_trans.common.campaign_run_config import (
    build_campaign_run_config,
)
from tools.benchmarks.periodic_sub_trans.common.core_enums import BenchmarkOrder
from tools.benchmarks.periodic_sub_trans.common.io_reports import (
    append_csv_row as _append_csv_row_common,
    write_csv_rows as _write_csv_rows_common,
    write_json,
    write_pipeline_snapshot_files,
)
from tools.benchmarks.config.no_wli_pipeline_profiles import get_no_wli_pipeline_profile
from tools.benchmarks.periodic_sub_trans.common.paths import make_flavor_run_dir
from tools.benchmarks.periodic_sub_trans.common.runner_types import Tier
from tools.benchmarks.periodic_sub_trans.common.scorer_schedule_apply import (
    apply_no_wli_schedule,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runtime_config import (
    RunModeInfo,
    build_run_mode_overrides as _build_run_mode_overrides_external,
    build_run_mode_info as _build_run_mode_info_external,
    canonical_run_mode as _canonical_run_mode_external,
    is_adaptive_focus_mode as _is_adaptive_focus_mode_external,
    mode_intent as _mode_intent_external,
    mode_stage3_can_skip as _mode_stage3_can_skip_external,
    normalize_oracle_mode as _normalize_oracle_mode_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage2_promotion import (
    build_stage3_promoted_keys as _build_stage3_promoted_keys_external,
    ensure_best_entry_in_promoted as _ensure_best_entry_in_promoted_external,
    ensure_best_entry_in_ranked as _ensure_best_entry_in_ranked_external,
    entry_key_tuple as _entry_key_tuple_external,
    is_better_match_first as _is_better_match_first_external,
    is_better_score_first as _is_better_score_first_external,
    is_better_stage3_candidate_preserving_solve as _is_better_stage3_candidate_preserving_solve_external,
    is_solved_match as _is_solved_match_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage2_search import (
    tail_diversity_collapsed as _tail_diversity_collapsed_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_band_policy import (
    resolve_stage3_gap_and_band as _resolve_stage3_gap_and_band_external,
    select_stage3_band as _select_stage3_band_external,
    select_stage3_default_band as _select_stage3_default_band_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_progress import (
    as_nonneg_float as _as_nonneg_float_external,
    fmt_finite_float as _fmt_finite_float_external,
    scorer_span_counter_summary as _scorer_span_counter_summary_external,
    solution_span_counter_summary as _solution_span_counter_summary_external,
    span_counter_delta as _span_counter_delta_external,
    span_counter_summary_from_obj as _span_counter_summary_from_obj_external,
    stage3_progress_logging as _stage3_progress_logging_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runner_bridges import (
    append_stage3_topk_from_kaeding_bridge as _append_stage3_topk_from_kaeding_bridge_external,
    append_stage3_topk_from_phasea_bridge as _append_stage3_topk_from_phasea_bridge_external,
    build_stage3_runtime_call_context_bridge as _build_stage3_runtime_call_context_bridge_external,
    build_iteration_payloads_bridge as _build_iteration_payloads_bridge_external,
    build_iteration_runtime_bridge as _build_iteration_runtime_bridge_external,
    commit_iteration_outputs_bridge as _commit_iteration_outputs_bridge_external,
    extract_kaeding_metrics_bridge as _extract_kaeding_metrics_bridge_external,
    evaluate_stage3_entry_policy_bridge as _evaluate_stage3_entry_policy_bridge_external,
    finalize_stage2_archive_bridge as _finalize_stage2_archive_bridge_external,
    prepare_stage3_refine_inputs_bridge as _prepare_stage3_refine_inputs_bridge_external,
    run_stage1_substitution_bridge as _run_stage1_substitution_bridge_external,
    run_stage2_search_bridge as _run_stage2_search_bridge_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.oracle_precheck import (
    evaluate_oracle_precheck as _evaluate_oracle_precheck_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage12_pipeline import (
    run_stage12_pipeline as _run_stage12_pipeline_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_outcome import (
    build_stage2_diagnostics as _build_stage2_diagnostics_external,
    build_stage3_diagnostics as _build_stage3_diagnostics_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_summary import (
    build_summary as _build_summary_external,
    derive_outcome_code as _derive_outcome_code_external,
    load_proven_solved_index as _load_proven_solved_index_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_completion import (
    finalize_run_outputs as _finalize_run_outputs_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.oracle_floor_guard import (
    build_oracle_floor_guard_result as _build_oracle_floor_guard_result_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_runtime_calls import (
    Stage3RuntimeCallContext,
)
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_matrix_flow import (
    IterationMatrixConfig,
    IterationMatrixFns,
    run_iteration_matrix as _run_iteration_matrix_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_span_summary import (
    summarize_stage3_span as _summarize_stage3_span_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_iteration_flow import (
    run_stage3_iteration_flow as _run_stage3_iteration_flow_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_finalize import (
    finalize_iteration_and_commit as _finalize_iteration_and_commit_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_pre_stage3 import (
    run_iteration_pre_stage3 as _run_iteration_pre_stage3_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_post_stage3 import (
    finalize_iteration_post_stage3 as _finalize_iteration_post_stage3_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.setup_logging import (
    emit_setup_logging as _emit_setup_logging_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.autoskip_proven import (
    handle_autoskip_proven_iteration as _handle_autoskip_proven_iteration_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.oracle_floor_guard_flow import (
    handle_oracle_floor_guard_if_triggered as _handle_oracle_floor_guard_if_triggered_external,
)


ALPHABET_SIZE = 29
ORDER = BenchmarkOrder.COL_THEN_SUB.value  # keep v1 aligned with the proven pipeline; add both orders in later variants.
PROFILE = "pipeline_no_wli_v1"
# Overnight solve-oriented run: no scan skip guards, Stage-3 always attempted.
PIPELINE_RUN_MODE = "adaptive_focus_v1_p7c3_only"  # "full" | "focus_500_nowli" | "focus_p5_c1_only" | "scan_fast_v1" | "adaptive_scan_v1" | "adaptive_focus_v1" | "adaptive_focus_v1_p7c3_only" | "scan_p5_p7_c1357"(legacy alias) | "smoke"
ENCODING_DIR = "ltr"  # "ltr" | "rtl"
NO_WLI_PIPELINE_PROFILE_ID = "no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1"
# Previous default kept in-file for one-line A/B rollback when needed.
NO_WLI_PIPELINE_PROFILE_ID_PREVIOUS_DEFAULT = "no_wli_a1_m12_b34_stage3avg_fulltext_v1"
NO_WLI_LONGRUN3X_PROFILE_ID = "no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1"
SCORER_STAGE1_LABEL = "A_char1"
SCORER_STAGE2_LABEL = "M_char12"
SCORER_STAGE3_LABEL = "B_char34"
SCORER_IMPL = ScorerImpl.TORCH.value  # Keep scoring/backend consistent across stages for now.
SCORER_STAGE3_IMPL_AVG_FULLTEXT = ScorerImpl.TORCH.value  # Stability guard for AVG full-text.
BATCH_EVAL_CHUNK_SIZE = 256  # Shared chunk size for decrypt+score batching in runner-level loops.
REQUIRE_BATCH_SCORING = True  # Fail fast if scorer can't execute true batch path in perf profiles.
STAGE2_PROMOTE_BY_STAGE3_JUDGE = True  # Bridge into Stage-3 objective basin before refine.
STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE = True  # Use Stage-3 objective for entry-band selection.
STAGE2_JUDGE_POLICY = "search_only"  # "search_only" | "stage3_judge"
REQUIRE_NO_ECDF_FOR_AVG_FULLTEXT = True  # Hard guard: avg.full_text scorers must never touch ECDF.
# Benchmark control: when False, oracle match_ratio is telemetry-only and never used
# for Stage-2/Stage-3 selection/ranking decisions.
ORACLE_ASSIST_SELECTION = False
# Oracle decision mode:
# - off: oracle is telemetry-only and never influences decisions
# - benchmark_only: oracle may influence benchmark decision paths
ORACLE_MODE = "off"  # "off" | "benchmark_only"

# Deterministic scoring experiment profiles (A/B/C).
# - off: keep profile-native scoring untouched.
# - a_baseline: stage3 char4 pct baseline (no span calibration).
# - b_min: stage3 char4 pct + calibrated span, combine=min.
# - c_min_late: same as b_min but activates only after char_pct_min threshold.
SCORING_EXPERIMENT_PROFILE = "c_min_late"  # off | a_baseline | b_min | c_min_late
SCORING_EXPERIMENT_ENFORCE_LOCKS = True
SCORING_EXPERIMENT_SPAN_ASSETS_DIR = Path("output/tools/benchmarks/scoring/span_hamming_nose_assets_v1")
SCORING_EXPERIMENT_SPAN_COVERAGE_MIN = 0.05
SCORING_EXPERIMENT_SPAN_QUALITY_MIN = 0.05
SCORING_EXPERIMENT_C_CHAR_PCT_MIN = 0.70
# Diagnostic override for c_min_late phase-B gate (set to a float like 0.05 for check-A runs).
STAGE3_SPAN_CHAR_PCT_MIN_OVERRIDE = None
ORACLE_STAGE3_FLOOR_GUARD_EPS = 1e-12
# Scan-mode runtime controls (kept hardcoded for deterministic benchmarking).
SCAN_TIER_TIME_CAP_SECONDS = 600.0  # 0 disables cap; applied before Stage-3.
SCAN_STAGE3_GATE_LOW_MATCH = 0.15  # below low -> skip Stage-3 in scan.
SCAN_STAGE3_GATE_HIGH_MATCH = 0.22  # [low, high) -> Phase-A only; >= high -> allow Phase-B.
# Legacy alias kept for backward compatibility in logs/tests.
SCAN_STAGE3_MIN_STAGE2_MATCH = float(SCAN_STAGE3_GATE_LOW_MATCH)
SCAN_STAGE2_CONTINUE_TO_GATE = True  # Keep expanding Stage-2 work until gate/cap.
SCAN_STAGE2_CONTINUE_CAP_SECONDS = 900.0  # 0 disables Stage-2 continuation cap.
_SCAN_TIER_TIME_CAP_SECONDS_DEFAULT = float(SCAN_TIER_TIME_CAP_SECONDS)
_SCAN_STAGE3_GATE_LOW_MATCH_DEFAULT = float(SCAN_STAGE3_GATE_LOW_MATCH)
_SCAN_STAGE3_GATE_HIGH_MATCH_DEFAULT = float(max(SCAN_STAGE3_GATE_LOW_MATCH, SCAN_STAGE3_GATE_HIGH_MATCH))
_SCAN_STAGE3_MIN_STAGE2_MATCH_DEFAULT = float(SCAN_STAGE3_GATE_LOW_MATCH)
_SCAN_STAGE2_CONTINUE_TO_GATE_DEFAULT = bool(SCAN_STAGE2_CONTINUE_TO_GATE)
_SCAN_STAGE2_CONTINUE_CAP_SECONDS_DEFAULT = float(SCAN_STAGE2_CONTINUE_CAP_SECONDS)

# Per-iteration tamper-evident audit chain (for crash/cancel-safe partial runs).
AUDIT_HASH_CHAIN_ENABLED = True
AUDIT_HASH_CHAIN_SEED = "0" * 64
AUDIT_HASH_CHAIN_CSV = "iteration_audit_chain.csv"
AUDIT_HASH_CHAIN_JSONL = "iteration_audit_chain.jsonl"

SOLVE_MATCH_THRESHOLD = 0.90
STALL_DELTA = 0.002
STALL_STAGE_LIMIT = 1
HEARTBEAT_SECONDS = 900
TIER_HEARTBEAT_SECONDS = 60
STAGE3_HEARTBEAT_SECONDS = 30
STAGE3_HEARTBEAT_MIN_STEP = 50
STAGE3_HEARTBEAT_MIN_ELAPSED_SECONDS = 5.0
PREVIEW_CHARS = 240
AUTOSKIP_PROVEN = True  # Skip fixtures already solved in flavor-specific solve_proof history.
AUTOSKIP_PROVEN_MIN_MATCH = SOLVE_MATCH_THRESHOLD  # Minimum historical match to treat as proven.
FORCE_RERUN_PROVEN = True  # If True, ignore proven autoskip and rerun all fixtures.

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
KAEDING_PROGRESS_EVERY_PCT = 1  # Callback cadence for Stage-3 heartbeat (console spam disabled below).
KAEDING_CONSOLE_PROGRESS = False

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
# Explicit span-basin judge pool size (Phase-A endpoints scored by span judge before Phase-B seeding).
# Tune manually for Check-A sweeps (e.g., 32 / 64 / 96).
STAGE3_SPAN_BASIN_JUDGE_K = 32
STAGE3_SPAN_BASIN_JUDGE_REQUIRE_SPAN_ACTIVE = True  # Basins without active span cannot win judge ranking.
STAGE3_SPAN_BASIN_JUDGE_DEDUPE_BY_END_HASH = True  # Judge distinct basin endpoints only.
STAGE3_SPAN_BASIN_JUDGE_TIE_EPS = 0.001  # Keep near-tie basins for Phase-B seeding.
# shoudl depend on siz eof  k,. highe rk hiher vlaue here
STAGE3_SPAN_BASIN_JUDGE_TIE_MAX_SEEDS = 48  # Near-tie expansion cap (applied as max(top_n, cap)).
RUN_STAGE3_SPAN_BASIN_K_SWEEP = True
STAGE3_SPAN_BASIN_K_SWEEP_VALUES = [ 96]

# c1 fast-pass focus overrides (used to solve p5/c1 first without globally over-tuning all tiers).
STAGE3_C1_FOCUS_ENABLED = True
STAGE3_C1_INIT_KEYS = 96
STAGE3_C1_PHASEA_STEPS = 1200
STAGE3_C1_PHASEB_STEPS = 6000
STAGE3_C1_PHASEB_TOP_N = 24
STAGE3_C1_PHASEB_GATE_DELTA_FLOOR = 0.010
STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR = 0.006
# Benchmark-only control: when Stage-3 finds a solved candidate, keep going
# to collect additional solve hits (or stop immediately if set False).
STAGE3_CONTINUE_AFTER_SOLVE = False

# Optional period-aware Stage-3 scaling (used by scan modes to give p7 modest extra time).
STAGE3_PERIOD_INIT_MULT_BY_PERIOD: Dict[int, float] = {}
STAGE3_PERIOD_STEP_MULT_BY_PERIOD: Dict[int, float] = {}
STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD: Dict[int, int] = {}
STAGE3_INIT_KEYS_CAP = 192

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
_STAGE3_CONTINUE_AFTER_SOLVE_DEFAULT = bool(STAGE3_CONTINUE_AFTER_SOLVE)
_STAGE3_PERIOD_INIT_MULT_BY_PERIOD_DEFAULT = dict(STAGE3_PERIOD_INIT_MULT_BY_PERIOD)
_STAGE3_PERIOD_STEP_MULT_BY_PERIOD_DEFAULT = dict(STAGE3_PERIOD_STEP_MULT_BY_PERIOD)
_STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD_DEFAULT = dict(STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD)
_STAGE3_INIT_KEYS_CAP_DEFAULT = int(STAGE3_INIT_KEYS_CAP)
_ORACLE_ASSIST_SELECTION_DEFAULT = bool(ORACLE_ASSIST_SELECTION)

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
    progress_pct=20,
    print_progress=True,
    seed=2026,
)

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
    global STAGE3_CONTINUE_AFTER_SOLVE
    global STAGE3_PERIOD_INIT_MULT_BY_PERIOD, STAGE3_PERIOD_STEP_MULT_BY_PERIOD
    global STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD, STAGE3_INIT_KEYS_CAP
    global ORACLE_ASSIST_SELECTION
    global SCAN_TIER_TIME_CAP_SECONDS, SCAN_STAGE3_GATE_LOW_MATCH, SCAN_STAGE3_GATE_HIGH_MATCH, SCAN_STAGE3_MIN_STAGE2_MATCH
    global SCAN_STAGE2_CONTINUE_TO_GATE, SCAN_STAGE2_CONTINUE_CAP_SECONDS

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
    STAGE3_CONTINUE_AFTER_SOLVE = bool(_STAGE3_CONTINUE_AFTER_SOLVE_DEFAULT)
    STAGE3_PERIOD_INIT_MULT_BY_PERIOD = dict(_STAGE3_PERIOD_INIT_MULT_BY_PERIOD_DEFAULT)
    STAGE3_PERIOD_STEP_MULT_BY_PERIOD = dict(_STAGE3_PERIOD_STEP_MULT_BY_PERIOD_DEFAULT)
    STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD = dict(_STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD_DEFAULT)
    STAGE3_INIT_KEYS_CAP = int(_STAGE3_INIT_KEYS_CAP_DEFAULT)
    ORACLE_ASSIST_SELECTION = bool(_ORACLE_ASSIST_SELECTION_DEFAULT)
    SCAN_TIER_TIME_CAP_SECONDS = float(_SCAN_TIER_TIME_CAP_SECONDS_DEFAULT)
    SCAN_STAGE3_GATE_LOW_MATCH = float(_SCAN_STAGE3_GATE_LOW_MATCH_DEFAULT)
    SCAN_STAGE3_GATE_HIGH_MATCH = float(max(float(SCAN_STAGE3_GATE_LOW_MATCH), float(_SCAN_STAGE3_GATE_HIGH_MATCH_DEFAULT)))
    SCAN_STAGE3_MIN_STAGE2_MATCH = float(SCAN_STAGE3_GATE_LOW_MATCH)
    SCAN_STAGE2_CONTINUE_TO_GATE = bool(_SCAN_STAGE2_CONTINUE_TO_GATE_DEFAULT)
    SCAN_STAGE2_CONTINUE_CAP_SECONDS = float(_SCAN_STAGE2_CONTINUE_CAP_SECONDS_DEFAULT)

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

    _apply_kaeding_progress_settings()


def _apply_kaeding_progress_settings() -> None:
    # Centralized Kaeding progress controls:
    # - progress_pct controls callback/progress bucket cadence
    # - print_progress controls solver-native console spam
    pct = int(max(1, KAEDING_PROGRESS_EVERY_PCT))
    print_progress = bool(KAEDING_CONSOLE_PROGRESS)
    SOLVER_STAGE1["progress_pct"] = int(pct)
    SOLVER_STAGE1["print_progress"] = bool(print_progress)
    SOLVER_STAGE3["progress_pct"] = int(pct)
    SOLVER_STAGE3["print_progress"] = bool(print_progress)
    STAGE3_PHASEA_CFG["progress_pct"] = int(pct)
    STAGE3_PHASEA_CFG["print_progress"] = bool(print_progress)
    STAGE3_PHASEB_CFG["progress_pct"] = int(pct)
    STAGE3_PHASEB_CFG["print_progress"] = bool(print_progress)


def _apply_scorer_impl_override(
    impl: str | None,
    *,
    scorer_stage3_impl_avg_fulltext: str | None = None,
) -> None:
    """Keep scorer impl wiring consistent across stage configs."""
    global SCORER_IMPL, SCORER_STAGE3_IMPL_AVG_FULLTEXT
    resolved = "" if impl is None else str(impl).strip()
    if resolved:
        SCORER_IMPL = resolved
    resolved_stage3 = (
        ""
        if scorer_stage3_impl_avg_fulltext is None
        else str(scorer_stage3_impl_avg_fulltext).strip()
    )
    if resolved_stage3:
        SCORER_STAGE3_IMPL_AVG_FULLTEXT = resolved_stage3
    for cfg in (SCORER_STAGE1, SCORER_STAGE2):
        if isinstance(cfg, dict):
            cfg["impl"] = str(SCORER_IMPL)
    if isinstance(SCORER_FULL, dict):
        SCORER_FULL["impl"] = _effective_stage3_impl(SCORER_FULL)


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
    scorer_stage3_impl_avg_fulltext: str | None = None,
    scorer_schedule: Mapping[str, Any] | None = None,
) -> None:
    """Apply campaign job settings through one explicit runner entrypoint."""
    cfg = build_campaign_run_config(
        run_seed=run_seed,
        period=period,
        columns=columns,
        length=length,
        tier_name=tier_name,
        run_mode=run_mode,
        profile_name=profile_name,
        heartbeat_seconds=heartbeat_seconds,
        autoskip_proven=autoskip_proven,
        force_rerun_proven=force_rerun_proven,
        avoid_repeat_fail=avoid_repeat_fail,
        text_offsets=text_offsets,
        tiers_regex_override=tiers_regex_override,
        scorer_impl=scorer_impl,
        scorer_stage3_impl_avg_fulltext=scorer_stage3_impl_avg_fulltext,
        scorer_schedule=scorer_schedule,
    )

    global AUTOSKIP_PROVEN, FORCE_RERUN_PROVEN
    global PIPELINE_RUN_MODE, PROFILE, HEARTBEAT_SECONDS, TIERS
    global NO_WLI_PIPELINE_PROFILE_ID
    global SCORER_STAGE1_LABEL, SCORER_STAGE2_LABEL, SCORER_STAGE3_LABEL

    AUTOSKIP_PROVEN = bool(cfg.autoskip_proven)
    FORCE_RERUN_PROVEN = bool(cfg.force_rerun_proven)
    PIPELINE_RUN_MODE = str(cfg.run_mode)
    PROFILE = str(cfg.profile_name)
    HEARTBEAT_SECONDS = int(cfg.heartbeat_seconds)
    TEXT_OFFSETS[:] = [int(x) for x in cfg.text_offsets]
    KEY_SEEDS[:] = [int(cfg.run_seed)]
    TIERS[:] = [cfg.tier()]

    profile_id = str(cfg.profile_name or "").strip()
    if profile_id:
        try:
            _ = get_no_wli_pipeline_profile(profile_id)
        except Exception:
            pass
        else:
            NO_WLI_PIPELINE_PROFILE_ID = profile_id
            _apply_profile_defaults()
            TIERS[:] = [cfg.tier()]
            TEXT_OFFSETS[:] = [int(x) for x in cfg.text_offsets]
            KEY_SEEDS[:] = [int(cfg.run_seed)]
            PIPELINE_RUN_MODE = str(cfg.run_mode)
            HEARTBEAT_SECONDS = int(cfg.heartbeat_seconds)

    labels = apply_no_wli_schedule(
        scorer_schedule=cfg.scorer_schedule,
        stage1_cfg=SCORER_STAGE1,
        stage2_cfg=SCORER_STAGE2,
        stage3_cfg=SCORER_FULL,
    )
    if labels.stage1_label is not None:
        SCORER_STAGE1_LABEL = str(labels.stage1_label)
    if labels.stage2_label is not None:
        SCORER_STAGE2_LABEL = str(labels.stage2_label)
    if labels.stage3_label is not None:
        SCORER_STAGE3_LABEL = str(labels.stage3_label)
    _apply_scorer_impl_override(
        cfg.scorer_impl,
        scorer_stage3_impl_avg_fulltext=cfg.scorer_stage3_impl_avg_fulltext,
    )


def _repo_root() -> Path:
    return _ROOT


def _resolve_repo_path(path_like: Path | str | None) -> Path | None:
    if path_like is None:
        return None
    p = Path(path_like).expanduser()
    if not p.is_absolute():
        p = (_repo_root() / p).resolve()
    else:
        p = p.resolve()
    return p


def _to_repo_rel_path(path_like: Path | str | None, *, root: Path) -> str:
    if path_like is None:
        return ""
    p = Path(path_like).expanduser()
    try:
        p = p.resolve()
        return str(p.relative_to(root.resolve())).replace("\\", "/")
    except Exception:
        return str(path_like)


def _scorer_cfg_for_output(cfg: Dict[str, Any], *, root: Path) -> Dict[str, Any]:
    out = dict(cfg)
    if "span_hamming_assets_dir" in out:
        out["span_hamming_assets_dir"] = _to_repo_rel_path(
            out.get("span_hamming_assets_dir"), root=root
        )
    return out


def _scoring_meta_for_output(meta: Dict[str, Any], *, root: Path) -> Dict[str, Any]:
    out = dict(meta)
    if "span_assets_dir" in out:
        out["span_assets_dir"] = _to_repo_rel_path(out.get("span_assets_dir"), root=root)
    return out


def _git_short() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(_repo_root()), stderr=subprocess.DEVNULL)
        return out.decode("utf-8", errors="replace").strip() or "nogit"
    except Exception:
        return "nogit"


def _git_commit() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(_repo_root()), stderr=subprocess.DEVNULL)
        return out.decode("utf-8", errors="replace").strip() or "nogit"
    except Exception:
        return "nogit"


def _git_dirty() -> bool:
    try:
        out = subprocess.check_output(["git", "status", "--porcelain"], cwd=str(_repo_root()), stderr=subprocess.DEVNULL)
        return bool(out.decode("utf-8", errors="replace").strip())
    except Exception:
        return False


def _sanitize_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _sanitize_jsonable(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_sanitize_jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        v = float(value)
        return v if np.isfinite(v) else None
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _sanitize_jsonable(value),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_payload(payload: Dict[str, Any]) -> str:
    return _sha256_text(_canonical_json(payload))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _build_non_scoring_lock_payload() -> Dict[str, Any]:
    mode_info = _build_run_mode_info(PIPELINE_RUN_MODE)
    return dict(
        mode=str(mode_info.mode_canonical),
        mode_raw=str(mode_info.mode_raw),
        mode_intent=str(mode_info.intent),
        stage3_can_skip=bool(mode_info.stage3_can_skip),
        direction=str(ENCODING_DIR),
        order=str(ORDER),
        alphabet_size=int(ALPHABET_SIZE),
        solve_threshold=float(SOLVE_MATCH_THRESHOLD),
        stall_delta=float(STALL_DELTA),
        stall_stage_limit=int(STALL_STAGE_LIMIT),
        scan_controls=dict(
            tier_time_cap_seconds=float(SCAN_TIER_TIME_CAP_SECONDS),
            stage2_continue_to_gate=bool(SCAN_STAGE2_CONTINUE_TO_GATE),
            stage2_continue_cap_seconds=float(SCAN_STAGE2_CONTINUE_CAP_SECONDS),
            stage3_gate_low_match=float(SCAN_STAGE3_GATE_LOW_MATCH),
            stage3_gate_high_match=float(max(float(SCAN_STAGE3_GATE_LOW_MATCH), float(SCAN_STAGE3_GATE_HIGH_MATCH))),
        ),
        text_offsets=[int(x) for x in TEXT_OFFSETS],
        key_seeds=[int(x) for x in KEY_SEEDS],
        tiers=[dict(name=str(t.name), period=int(t.period), columns=int(t.columns), length=int(t.length)) for t in TIERS],
        stage1_search=dict(
            seed_restarts=int(STAGE1_SEED_RESTARTS),
            seed_n_blocks=int(STAGE1_SEED_N_BLOCKS),
            seed_total=int(STAGE1_SEED_TOTAL),
            seed_swaps=int(STAGE1_SEED_SWAPS),
            scout_runs=int(STAGE12_SCOUT_RUNS),
            archive_keep=int(STAGE12_ARCHIVE_KEEP),
            promote_top=int(STAGE12_PROMOTE_TOP),
            scout_step_scale=float(STAGE1_SCOUT_STEP_SCALE),
            scout_restart_scale=float(STAGE1_SCOUT_RESTART_SCALE),
            scout_min_steps=int(STAGE1_SCOUT_MIN_STEPS),
            scout_min_restarts=int(STAGE1_SCOUT_MIN_RESTARTS),
            scout_no_improve_delta=float(STAGE1_SCOUT_NO_IMPROVE_DELTA),
            scout_no_improve_patience=int(STAGE1_SCOUT_NO_IMPROVE_PATIENCE),
            scout_min_new_archive=int(STAGE1_SCOUT_MIN_NEW_ARCHIVE),
            scout_early_stop_min_scouts=int(STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS),
            sub_candidates=int(STAGE1_SUB_CANDIDATES),
            sub_candidates_by_columns={str(k): int(v) for k, v in STAGE1_SUB_CANDIDATES_BY_COLUMNS.items()},
        ),
        stage2_search=dict(
            exact_max_columns=int(STAGE2_EXACT_MAX_COLUMNS),
            exact_sub_candidates=int(STAGE2_EXACT_SUB_CANDIDATES),
            exact_sub_by_columns={str(k): int(v) for k, v in STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS.items()},
            exact_two_pass=bool(STAGE2_EXACT_TWO_PASS),
            exact_pass1_top_tails=int(STAGE2_EXACT_PASS1_TOP_TAILS),
            exact_pass1_top_by_columns={str(k): int(v) for k, v in STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS.items()},
            exact_early_solve_break=bool(STAGE2_EXACT_EARLY_SOLVE_BREAK),
            hybrid_sub_candidates=int(STAGE2_HYBRID_SUB_CANDIDATES),
            hybrid_sub_by_columns={str(k): int(v) for k, v in STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS.items()},
            judge_policy=str(STAGE2_JUDGE_POLICY),
            promote_by_stage3_judge=bool(STAGE2_PROMOTE_BY_STAGE3_JUDGE),
            entry_band_by_stage3_judge=bool(STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE),
        ),
        stage3_search=dict(
            solver=dict(SOLVER_STAGE3),
            init_keys=int(STAGE3_INITIAL_KEYS),
            init_by_columns={str(k): int(v) for k, v in STAGE3_INITIAL_KEYS_BY_COLUMNS.items()},
            span_basin_judge_k=int(STAGE3_SPAN_BASIN_JUDGE_K),
            span_basin_judge_require_span_active=bool(STAGE3_SPAN_BASIN_JUDGE_REQUIRE_SPAN_ACTIVE),
            span_basin_judge_dedupe_by_end_hash=bool(STAGE3_SPAN_BASIN_JUDGE_DEDUPE_BY_END_HASH),
            span_basin_judge_tie_eps=float(STAGE3_SPAN_BASIN_JUDGE_TIE_EPS),
            span_basin_judge_tie_max_seeds=int(STAGE3_SPAN_BASIN_JUDGE_TIE_MAX_SEEDS),
            span_basin_judge_k_sweep=dict(
                enabled=bool(RUN_STAGE3_SPAN_BASIN_K_SWEEP),
                values=[int(v) for v in STAGE3_SPAN_BASIN_K_SWEEP_VALUES],
            ),
            dynamic_bands=[dict(b) for b in STAGE3_DYNAMIC_BANDS],
            two_phase_enabled=bool(STAGE3_TWO_PHASE_ENABLED),
            phase_a=dict(STAGE3_PHASEA_CFG),
            phase_b=dict(STAGE3_PHASEB_CFG),
            phase_b_top_n=int(STAGE3_PHASEB_TOP_N),
            phase_b_gate_delta=float(STAGE3_PHASEB_GATE_DELTA_FLOOR),
            phase_b_gate_end_gain=float(STAGE3_PHASEB_GATE_END_GAIN_FLOOR),
            continue_after_solve=bool(STAGE3_CONTINUE_AFTER_SOLVE),
            c1_focus_enabled=bool(STAGE3_C1_FOCUS_ENABLED),
            c1_init_keys=int(STAGE3_C1_INIT_KEYS),
            c1_phase_a_steps=int(STAGE3_C1_PHASEA_STEPS),
            c1_phase_b_steps=int(STAGE3_C1_PHASEB_STEPS),
            c1_phase_b_top_n=int(STAGE3_C1_PHASEB_TOP_N),
            c1_gate_delta=float(STAGE3_C1_PHASEB_GATE_DELTA_FLOOR),
            c1_gate_end_gain=float(STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR),
            period_init_mult={str(k): float(v) for k, v in STAGE3_PERIOD_INIT_MULT_BY_PERIOD.items()},
            period_step_mult={str(k): float(v) for k, v in STAGE3_PERIOD_STEP_MULT_BY_PERIOD.items()},
            period_restart_bonus={str(k): int(v) for k, v in STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD.items()},
            init_keys_cap=int(STAGE3_INIT_KEYS_CAP),
        ),
        logging_controls=dict(
            kaeding_progress_every_pct=int(KAEDING_PROGRESS_EVERY_PCT),
            kaeding_console_progress=int(1 if bool(KAEDING_CONSOLE_PROGRESS) else 0),
            tier_heartbeat_seconds=float(TIER_HEARTBEAT_SECONDS),
            stage3_heartbeat_seconds=float(STAGE3_HEARTBEAT_SECONDS),
            stage3_heartbeat_min_step=int(STAGE3_HEARTBEAT_MIN_STEP),
            stage3_heartbeat_min_elapsed_seconds=float(STAGE3_HEARTBEAT_MIN_ELAPSED_SECONDS),
        ),
    )


def _build_scoring_lock_payload() -> Dict[str, Any]:
    return dict(
        scorer_impl=str(getattr(SCORER_IMPL, "value", SCORER_IMPL)),
        stage1_label=str(SCORER_STAGE1_LABEL),
        stage2_label=str(SCORER_STAGE2_LABEL),
        stage3_label=str(SCORER_STAGE3_LABEL),
        stage1=dict(SCORER_STAGE1),
        stage2=dict(SCORER_STAGE2),
        stage3=dict(SCORER_FULL),
        stage2_pass1_primary={str(k): float(v) for k, v in STAGE2_PASS1_PRIMARY_CHAR_WEIGHTS.items()},
        stage2_pass1_fallback={str(k): float(v) for k, v in STAGE2_PASS1_FALLBACK_CHAR_WEIGHTS.items()},
        oracle_assist_selection=bool(ORACLE_ASSIST_SELECTION),
        require_no_ecdf_for_avg_fulltext=bool(REQUIRE_NO_ECDF_FOR_AVG_FULLTEXT),
        stage3_search_contract=dict(
            objective=(
                str(SCORER_STAGE2.get("objective", "avg.logp.win20"))
                if str(SCORER_STAGE2.get("objective", "avg.logp.win20")).startswith("avg.")
                else "avg.logp.win20"
            ),
            avg_window_policy="full_text",
            char_weights={"4": 1.0},
            span_hamming_enabled=False,
            span_basin_judge_k=int(STAGE3_SPAN_BASIN_JUDGE_K),
            span_basin_judge_require_span_active=bool(STAGE3_SPAN_BASIN_JUDGE_REQUIRE_SPAN_ACTIVE),
            span_basin_judge_dedupe_by_end_hash=bool(STAGE3_SPAN_BASIN_JUDGE_DEDUPE_BY_END_HASH),
            span_basin_judge_tie_eps=float(STAGE3_SPAN_BASIN_JUDGE_TIE_EPS),
            span_basin_judge_tie_max_seeds=int(STAGE3_SPAN_BASIN_JUDGE_TIE_MAX_SEEDS),
            span_basin_judge_k_sweep=dict(
                enabled=bool(RUN_STAGE3_SPAN_BASIN_K_SWEEP),
                values=[int(v) for v in STAGE3_SPAN_BASIN_K_SWEEP_VALUES],
            ),
        ),
        stage3_span_char_pct_min_override=(
            None
            if STAGE3_SPAN_CHAR_PCT_MIN_OVERRIDE is None
            else float(STAGE3_SPAN_CHAR_PCT_MIN_OVERRIDE)
        ),
    )


def _stage3_char4_pct_baseline_cfg() -> Dict[str, Any]:
    return dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=False,
        char_weights={4: 1.0},
        wli_weights={},
        impl=SCORER_IMPL,
    )


def _stage3_char4_avg_fulltext_search_cfg(*, direction: Direction) -> Dict[str, Any]:
    """Stage-3 search scorer contract: avg/full_text char4, no span/ECDF."""
    obj = str(SCORER_STAGE2.get("objective", "avg.logp.win20"))
    if not obj.startswith("avg."):
        obj = "avg.logp.win20"
    return dict(
        objective=str(obj),
        include_char=True,
        use_word_breaks=False,
        char_weights={4: 1.0},
        wli_weights={},
        avg_window_policy="full_text",
        impl=SCORER_STAGE3_IMPL_AVG_FULLTEXT,
        encoding_dir=direction,
        span_hamming_enabled=False,
        span_hamming_mode="off",
        span_hamming_weight=0.0,
    )


def _apply_scoring_experiment_profile() -> Dict[str, Any]:
    """Apply deterministic A/B/C scoring experiment profile via hardcoded constants."""

    global PROFILE, SCORER_STAGE3_LABEL, SCORER_FULL
    profile = str(SCORING_EXPERIMENT_PROFILE).strip().lower()
    if profile in {"", "off", "none"}:
        return dict(profile="off", enabled=False, description="profile-native scoring")

    pre_non_hash = _hash_payload(_build_non_scoring_lock_payload())
    stage3_cfg = _stage3_char4_pct_baseline_cfg()
    desc = ""
    span_assets_dir: Path | None = None

    if profile == "a_baseline":
        SCORER_STAGE3_LABEL = "B_char4_pct_baseline"
        stage3_cfg.update(
            span_hamming_mode="off",
            span_hamming_enabled=False,
            span_hamming_weight=0.0,
        )
        desc = "char4 pct baseline (no span calibrated channel)"
    elif profile in {"b_min", "c_min_late"}:
        SCORER_STAGE3_LABEL = "B_char4_pct_span_min" if profile == "b_min" else "B_char4_pct_span_min_late"
        span_assets_dir = _resolve_repo_path(SCORING_EXPERIMENT_SPAN_ASSETS_DIR)
        if span_assets_dir is None:
            raise ValueError("SCORING_EXPERIMENT_SPAN_ASSETS_DIR cannot be None")
        calib_fp = span_assets_dir / "combined_calibration.json"
        ecdf_root = span_assets_dir / "ecdf" / "span_x"
        if not calib_fp.exists():
            raise FileNotFoundError(f"Missing combined_calibration.json for span experiment: {calib_fp}")
        if not ecdf_root.exists():
            raise FileNotFoundError(f"Missing span ECDF root for span experiment: {ecdf_root}")
        stage3_cfg.update(
            span_hamming_enabled=True,
            span_hamming_mode="calibrated",
            span_hamming_assets_dir=str(span_assets_dir),
            span_hamming_combine_mode="min",
            span_hamming_weight_span=1.0,
            span_hamming_weight_char=1.0,
            span_hamming_coverage_min=float(SCORING_EXPERIMENT_SPAN_COVERAGE_MIN),
            span_hamming_quality_min=float(SCORING_EXPERIMENT_SPAN_QUALITY_MIN),
            span_hamming_gate_fail_policy=("char_only" if profile == "c_min_late" else "score_floor"),
        )
        if profile == "c_min_late":
            stage3_cfg["span_hamming_char_pct_min"] = float(SCORING_EXPERIMENT_C_CHAR_PCT_MIN)
            desc = "char4 pct + calibrated span (min combine, late activation by char pct)"
        else:
            desc = "char4 pct + calibrated span (min combine)"
    else:
        raise ValueError(
            f"Unsupported SCORING_EXPERIMENT_PROFILE={SCORING_EXPERIMENT_PROFILE!r}; "
            "expected off|a_baseline|b_min|c_min_late"
        )

    SCORER_FULL = stage3_cfg
    PROFILE = f"{PROFILE}__{profile}"

    post_non_hash = _hash_payload(_build_non_scoring_lock_payload())
    if bool(SCORING_EXPERIMENT_ENFORCE_LOCKS) and (pre_non_hash != post_non_hash):
        raise RuntimeError(
            "Scoring experiment changed non-scoring knobs; this violates locked A/B/C setup "
            f"(before={pre_non_hash} after={post_non_hash})"
        )

    return dict(
        profile=profile,
        enabled=True,
        description=desc,
        span_assets_dir=_to_repo_rel_path(span_assets_dir, root=_repo_root()),
        non_scoring_hash_before=pre_non_hash,
        non_scoring_hash_after=post_non_hash,
        scoring_hash=_hash_payload(_build_scoring_lock_payload()),
    )


def _build_stage3_experiment_cfg(
    *,
    profile_name: str,
    direction: Direction,
    span_assets_dir: Path | None,
    char_pct_min_override: float | None = None,
    disable_char_pct_gate: bool = False,
) -> Dict[str, Any]:
    """Build per-stage3 scorer config without mutating global scoring experiment state."""
    p = str(profile_name or "").strip().lower()
    cfg = dict(_stage3_char4_pct_baseline_cfg(), encoding_dir=direction)
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
        raise FileNotFoundError(f"Missing combined_calibration.json for stage3 span experiment: {calib_fp}")
    if not ecdf_root.exists():
        raise FileNotFoundError(f"Missing span ECDF root for stage3 span experiment: {ecdf_root}")
    cfg.update(
        span_hamming_enabled=True,
        span_hamming_mode="calibrated",
        span_hamming_assets_dir=str(span_assets_dir),
        span_hamming_combine_mode="min",
        span_hamming_weight_span=1.0,
        span_hamming_weight_char=1.0,
        span_hamming_coverage_min=float(SCORING_EXPERIMENT_SPAN_COVERAGE_MIN),
        span_hamming_quality_min=float(SCORING_EXPERIMENT_SPAN_QUALITY_MIN),
        span_hamming_gate_fail_policy=("char_only" if p == "c_min_late" else "score_floor"),
    )
    if p == "c_min_late":
        if bool(disable_char_pct_gate):
            cfg["span_hamming_gate_fail_policy"] = "score_floor"
            return cfg
        gate = (
            float(char_pct_min_override)
            if char_pct_min_override is not None
            else float(SCORING_EXPERIMENT_C_CHAR_PCT_MIN)
        )
        cfg["span_hamming_char_pct_min"] = float(gate)
    return cfg


def _canonical_run_mode(mode: str | None) -> str:
    return str(_canonical_run_mode_external(mode))


def _mode_intent(mode: str | None) -> str:
    return str(_mode_intent_external(mode))


def _mode_stage3_can_skip(mode: str | None) -> bool:
    return bool(_mode_stage3_can_skip_external(mode))


def _is_adaptive_focus_mode(mode: str | None) -> bool:
    return bool(_is_adaptive_focus_mode_external(mode))


def _build_run_mode_info(mode: str | None) -> RunModeInfo:
    return _build_run_mode_info_external(mode)


def _apply_run_mode() -> None:
    global PROFILE, HEARTBEAT_SECONDS, TIERS, TEXT_OFFSETS, KEY_SEEDS
    global STAGE2_PROMOTE_BY_STAGE3_JUDGE, STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE
    global STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS, STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS
    global ORACLE_ASSIST_SELECTION
    global STAGE1_SEED_RESTARTS, STAGE1_SEED_TOTAL, STAGE1_SCOUT_MIN_STEPS
    global STAGE12_ARCHIVE_KEEP, STAGE12_PROMOTE_TOP
    global STAGE1_SCOUT_NO_IMPROVE_PATIENCE, STAGE1_SCOUT_MIN_NEW_ARCHIVE, STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS
    global STAGE3_INITIAL_KEYS, STAGE3_INITIAL_KEYS_BY_COLUMNS, STAGE3_DYNAMIC_BANDS
    global STAGE3_C1_INIT_KEYS, STAGE3_C1_PHASEA_STEPS, STAGE3_C1_PHASEB_STEPS, STAGE3_C1_PHASEB_TOP_N
    global STAGE3_PHASEB_CFG, STAGE3_PHASEB_TOP_N, STAGE3_PHASEB_GATE_DELTA_FLOOR, STAGE3_PHASEB_GATE_END_GAIN_FLOOR
    global STAGE3_CONTINUE_AFTER_SOLVE
    global STAGE3_PERIOD_INIT_MULT_BY_PERIOD, STAGE3_PERIOD_STEP_MULT_BY_PERIOD
    global STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD, STAGE3_INIT_KEYS_CAP
    global SCORING_EXPERIMENT_PROFILE
    global SCAN_TIER_TIME_CAP_SECONDS, SCAN_STAGE3_GATE_LOW_MATCH, SCAN_STAGE3_GATE_HIGH_MATCH, SCAN_STAGE3_MIN_STAGE2_MATCH
    global SCAN_STAGE2_CONTINUE_TO_GATE, SCAN_STAGE2_CONTINUE_CAP_SECONDS
    overrides = _build_run_mode_overrides_external(
        mode=PIPELINE_RUN_MODE,
        pipeline_profile_id=str(NO_WLI_PIPELINE_PROFILE_ID),
        oracle_assist_selection_default=bool(_ORACLE_ASSIST_SELECTION_DEFAULT),
        stage3_continue_after_solve_default=bool(_STAGE3_CONTINUE_AFTER_SOLVE_DEFAULT),
        stage12_scout_runs=int(STAGE12_SCOUT_RUNS),
        stage3_phaseb_cfg=dict(STAGE3_PHASEB_CFG),
    )
    if not overrides:
        return

    if "PROFILE" in overrides:
        PROFILE = str(overrides["PROFILE"])
    if "HEARTBEAT_SECONDS" in overrides:
        HEARTBEAT_SECONDS = int(overrides["HEARTBEAT_SECONDS"])
    if "TEXT_OFFSETS" in overrides:
        TEXT_OFFSETS[:] = [int(x) for x in list(overrides["TEXT_OFFSETS"])]
    if "KEY_SEEDS" in overrides:
        KEY_SEEDS[:] = [int(x) for x in list(overrides["KEY_SEEDS"])]
    if "STAGE2_PROMOTE_BY_STAGE3_JUDGE" in overrides:
        STAGE2_PROMOTE_BY_STAGE3_JUDGE = bool(overrides["STAGE2_PROMOTE_BY_STAGE3_JUDGE"])
    if "STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE" in overrides:
        STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE = bool(overrides["STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE"])
    if "ORACLE_ASSIST_SELECTION" in overrides:
        ORACLE_ASSIST_SELECTION = bool(overrides["ORACLE_ASSIST_SELECTION"])
    if "STAGE3_CONTINUE_AFTER_SOLVE" in overrides:
        STAGE3_CONTINUE_AFTER_SOLVE = bool(overrides["STAGE3_CONTINUE_AFTER_SOLVE"])
    if "SCORING_EXPERIMENT_PROFILE" in overrides:
        SCORING_EXPERIMENT_PROFILE = str(overrides["SCORING_EXPERIMENT_PROFILE"])
    if "SCAN_TIER_TIME_CAP_SECONDS" in overrides:
        SCAN_TIER_TIME_CAP_SECONDS = float(overrides["SCAN_TIER_TIME_CAP_SECONDS"])
    if "SCAN_STAGE2_CONTINUE_TO_GATE" in overrides:
        SCAN_STAGE2_CONTINUE_TO_GATE = bool(overrides["SCAN_STAGE2_CONTINUE_TO_GATE"])
    if "SCAN_STAGE2_CONTINUE_CAP_SECONDS" in overrides:
        SCAN_STAGE2_CONTINUE_CAP_SECONDS = float(overrides["SCAN_STAGE2_CONTINUE_CAP_SECONDS"])
    if "SCAN_STAGE3_GATE_LOW_MATCH" in overrides:
        SCAN_STAGE3_GATE_LOW_MATCH = float(overrides["SCAN_STAGE3_GATE_LOW_MATCH"])
    if "SCAN_STAGE3_GATE_HIGH_MATCH" in overrides:
        SCAN_STAGE3_GATE_HIGH_MATCH = float(overrides["SCAN_STAGE3_GATE_HIGH_MATCH"])
    if "SCAN_STAGE3_MIN_STAGE2_MATCH" in overrides:
        SCAN_STAGE3_MIN_STAGE2_MATCH = float(overrides["SCAN_STAGE3_MIN_STAGE2_MATCH"])
    if "STAGE1_SEED_RESTARTS" in overrides:
        STAGE1_SEED_RESTARTS = int(overrides["STAGE1_SEED_RESTARTS"])
    if "STAGE1_SEED_TOTAL" in overrides:
        STAGE1_SEED_TOTAL = int(overrides["STAGE1_SEED_TOTAL"])
    if "STAGE1_SCOUT_MIN_STEPS" in overrides:
        STAGE1_SCOUT_MIN_STEPS = int(overrides["STAGE1_SCOUT_MIN_STEPS"])
    if "STAGE12_ARCHIVE_KEEP" in overrides:
        STAGE12_ARCHIVE_KEEP = int(overrides["STAGE12_ARCHIVE_KEEP"])
    if "STAGE12_PROMOTE_TOP" in overrides:
        STAGE12_PROMOTE_TOP = int(overrides["STAGE12_PROMOTE_TOP"])
    if "STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS" in overrides:
        STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS = {
            int(k): int(v)
            for k, v in dict(overrides["STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS"]).items()
        }
    if "STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS" in overrides:
        STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS = {
            int(k): int(v)
            for k, v in dict(overrides["STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS"]).items()
        }
    if "STAGE1_SCOUT_NO_IMPROVE_PATIENCE" in overrides:
        STAGE1_SCOUT_NO_IMPROVE_PATIENCE = int(overrides["STAGE1_SCOUT_NO_IMPROVE_PATIENCE"])
    if "STAGE1_SCOUT_MIN_NEW_ARCHIVE" in overrides:
        STAGE1_SCOUT_MIN_NEW_ARCHIVE = int(overrides["STAGE1_SCOUT_MIN_NEW_ARCHIVE"])
    if "STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS" in overrides:
        STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS = int(overrides["STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS"])
    if "STAGE3_INITIAL_KEYS" in overrides:
        STAGE3_INITIAL_KEYS = int(overrides["STAGE3_INITIAL_KEYS"])
    if "STAGE3_INITIAL_KEYS_BY_COLUMNS" in overrides:
        STAGE3_INITIAL_KEYS_BY_COLUMNS = {
            int(k): int(v)
            for k, v in dict(overrides["STAGE3_INITIAL_KEYS_BY_COLUMNS"]).items()
        }
    if "STAGE3_DYNAMIC_BANDS" in overrides:
        STAGE3_DYNAMIC_BANDS = [dict(b) for b in list(overrides["STAGE3_DYNAMIC_BANDS"])]
    if "STAGE3_C1_INIT_KEYS" in overrides:
        STAGE3_C1_INIT_KEYS = int(overrides["STAGE3_C1_INIT_KEYS"])
    if "STAGE3_C1_PHASEA_STEPS" in overrides:
        STAGE3_C1_PHASEA_STEPS = int(overrides["STAGE3_C1_PHASEA_STEPS"])
    if "STAGE3_C1_PHASEB_STEPS" in overrides:
        STAGE3_C1_PHASEB_STEPS = int(overrides["STAGE3_C1_PHASEB_STEPS"])
    if "STAGE3_C1_PHASEB_TOP_N" in overrides:
        STAGE3_C1_PHASEB_TOP_N = int(overrides["STAGE3_C1_PHASEB_TOP_N"])
    if "STAGE3_PHASEB_TOP_N" in overrides:
        STAGE3_PHASEB_TOP_N = int(overrides["STAGE3_PHASEB_TOP_N"])
    if "STAGE3_PHASEB_GATE_DELTA_FLOOR" in overrides:
        STAGE3_PHASEB_GATE_DELTA_FLOOR = float(overrides["STAGE3_PHASEB_GATE_DELTA_FLOOR"])
    if "STAGE3_PHASEB_GATE_END_GAIN_FLOOR" in overrides:
        STAGE3_PHASEB_GATE_END_GAIN_FLOOR = float(overrides["STAGE3_PHASEB_GATE_END_GAIN_FLOOR"])
    if "STAGE3_PHASEB_CFG" in overrides:
        STAGE3_PHASEB_CFG = dict(overrides["STAGE3_PHASEB_CFG"])
    if "STAGE3_PERIOD_INIT_MULT_BY_PERIOD" in overrides:
        STAGE3_PERIOD_INIT_MULT_BY_PERIOD = {
            int(k): float(v)
            for k, v in dict(overrides["STAGE3_PERIOD_INIT_MULT_BY_PERIOD"]).items()
        }
    if "STAGE3_PERIOD_STEP_MULT_BY_PERIOD" in overrides:
        STAGE3_PERIOD_STEP_MULT_BY_PERIOD = {
            int(k): float(v)
            for k, v in dict(overrides["STAGE3_PERIOD_STEP_MULT_BY_PERIOD"]).items()
        }
    if "STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD" in overrides:
        STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD = {
            int(k): int(v)
            for k, v in dict(overrides["STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD"]).items()
        }
    if "STAGE3_INIT_KEYS_CAP" in overrides:
        STAGE3_INIT_KEYS_CAP = int(overrides["STAGE3_INIT_KEYS_CAP"])
    if "TIERS" in overrides:
        TIERS[:] = [
            Tier(str(name), int(period), int(columns), int(length))
            for name, period, columns, length in list(overrides["TIERS"])
        ]


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


def _is_better_match_first(
    cand_match: float,
    cand_score: float,
    best_match: float,
    best_score: float,
) -> bool:
    return bool(
        _is_better_match_first_external(
            cand_match=float(cand_match),
            cand_score=float(cand_score),
            best_match=float(best_match),
            best_score=float(best_score),
        )
    )


def _is_better_score_first(
    cand_score: float,
    cand_match: float,
    best_score: float,
    best_match: float,
) -> bool:
    return bool(
        _is_better_score_first_external(
            cand_score=float(cand_score),
            cand_match=float(cand_match),
            best_score=float(best_score),
            best_match=float(best_match),
        )
    )


def _is_solved_match(match_ratio: float) -> bool:
    return bool(
        _is_solved_match_external(
            match_ratio=float(match_ratio),
            solve_threshold=float(SOLVE_MATCH_THRESHOLD),
        )
    )


def _is_better_stage3_candidate_preserving_solve(
    cand_score: float,
    cand_match: float,
    best_score: float,
    best_match: float,
    *,
    score_first: bool,
) -> bool:
    return bool(
        _is_better_stage3_candidate_preserving_solve_external(
            cand_score=float(cand_score),
            cand_match=float(cand_match),
            best_score=float(best_score),
            best_match=float(best_match),
            solve_threshold=float(SOLVE_MATCH_THRESHOLD),
            score_first=bool(score_first),
        )
    )


_as_nonneg_float = _as_nonneg_float_external
_span_counter_summary_from_obj = _span_counter_summary_from_obj_external
_span_counter_delta = _span_counter_delta_external
_solution_span_counter_summary = _solution_span_counter_summary_external
_scorer_span_counter_summary = _scorer_span_counter_summary_external
_fmt_finite_float = _fmt_finite_float_external
_stage3_progress_logging = _stage3_progress_logging_external


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


def _objective_space_key(scorer_cfg: Dict[str, Any]) -> str:
    """Coarse objective-space key for cross-stage score comparability checks."""

    obj = str(scorer_cfg.get("objective", "")).strip().lower()
    if obj.startswith("avg."):
        return "avg"
    if obj.startswith("pct.") or obj.startswith("energy."):
        return "pct_energy"
    if obj.startswith("neglogp"):
        return "neglogp"
    return obj.split(".", 1)[0] if obj else "unknown"


def _effective_stage3_impl(scorer_cfg: Dict[str, Any]) -> str:
    if _is_avg_fulltext_scorer(scorer_cfg):
        return str(SCORER_STAGE3_IMPL_AVG_FULLTEXT)
    return str(SCORER_IMPL)


def _stage2_judge_pool_limit(
    *,
    ranked_count: int,
    archive_keep: int,
    stage2_scorer_cfg: Dict[str, Any] | None = None,
    stage3_scorer_cfg: Dict[str, Any],
) -> int:
    ranked_n = max(0, int(ranked_count))
    if ranked_n <= 0:
        return 0
    stage2_stage3_space_match = True
    if stage2_scorer_cfg is not None:
        stage2_stage3_space_match = (
            _objective_space_key(dict(stage2_scorer_cfg))
            == _objective_space_key(dict(stage3_scorer_cfg))
        )
    stage3_span_calibrated = (
        str(stage3_scorer_cfg.get("span_hamming_mode", "off")).strip().lower() == "calibrated"
    )
    if (not bool(STAGE2_PROMOTE_BY_STAGE3_JUDGE)) and (not bool(STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE)):
        # Even when judge is "off", keep a broad bridge pool if Stage-2 and Stage-3
        # optimize different score families so diagnostics/banding are not rank-topK biased.
        if not stage2_stage3_space_match:
            target = max(1, int(archive_keep))
        else:
            target = max(1, int(SAVE_STAGE2_TOPK))
        return max(1, min(ranked_n, target))
    if _is_avg_fulltext_scorer(stage3_scorer_cfg) or stage3_span_calibrated or (not stage2_stage3_space_match):
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
    return tuple(_entry_key_tuple_external(entry))


def _ensure_best_entry_in_ranked(
    *,
    ranked_entries: Sequence[Dict[str, Any]],
    best_entry: Dict[str, Any] | None,
) -> List[Dict[str, Any]]:
    return _ensure_best_entry_in_ranked_external(
        ranked_entries=ranked_entries,
        best_entry=best_entry,
    )


def _ensure_best_entry_in_promoted(
    *,
    promoted_entries: Sequence[Dict[str, Any]],
    best_entry: Dict[str, Any] | None,
    promote_top: int,
) -> Tuple[List[Dict[str, Any]], bool]:
    return _ensure_best_entry_in_promoted_external(
        promoted_entries=promoted_entries,
        best_entry=best_entry,
        promote_top=promote_top,
    )


def _build_stage3_promoted_keys(
    *,
    promoted_entries: Sequence[Dict[str, Any]],
    best_key: Sequence[int] | None,
    key_len: int,
) -> List[List[int]]:
    return _build_stage3_promoted_keys_external(
        promoted_entries=promoted_entries,
        best_key=best_key,
        key_len=key_len,
    )


_apply_profile_defaults()
_RUN_STAGE3_SPAN_BASIN_K_SWEEP_ACTIVE = False


def _tail_diversity_collapsed(tails: List[Tuple[int, ...]], *, columns: int) -> Tuple[bool, Dict[str, float]]:
    return _tail_diversity_collapsed_external(
        tails=tails,
        columns=int(columns),
        min_first_symbols=int(STAGE2_PASS1_DIVERSITY_MIN_FIRST_SYMBOLS),
        min_hamming_factor=float(STAGE2_PASS1_DIVERSITY_MIN_HAMMING_FACTOR),
    )


def _select_stage3_band(gap_to_oracle: float) -> Dict[str, Any]:
    return _select_stage3_band_external(
        dynamic_bands=list(STAGE3_DYNAMIC_BANDS),
        gap_to_oracle=float(gap_to_oracle),
    )


def _select_stage3_default_band() -> Dict[str, Any]:
    return _select_stage3_default_band_external(
        dynamic_bands=list(STAGE3_DYNAMIC_BANDS),
        preferred_name="mid",
    )


def _oracle_mode_normalized() -> str:
    return str(_normalize_oracle_mode_external(ORACLE_MODE))


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
    _write_csv_rows_common(path, rows)


def _append_csv_row(path: Path, row: Dict[str, Any]) -> None:
    _append_csv_row_common(path, row, merge_fieldnames=True)


def _append_jsonl_row(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(_sanitize_jsonable(row), sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n")


def _append_iteration_audit_row(
    *,
    audit_csv: Path,
    audit_jsonl: Path,
    prev_chain_hash: str,
    payload: Dict[str, Any],
) -> str:
    clean_payload = _sanitize_jsonable(payload)
    row_hash = _sha256_text(_canonical_json(clean_payload))
    chain_hash = _sha256_text(f"{str(prev_chain_hash)}|{row_hash}")
    row_out = dict(
        **clean_payload,
        row_hash=str(row_hash),
        prev_chain_hash=str(prev_chain_hash),
        chain_hash=str(chain_hash),
    )
    _append_csv_row(audit_csv, row_out)
    _append_jsonl_row(audit_jsonl, row_out)
    return str(chain_hash)


_derive_outcome_code = _derive_outcome_code_external
_load_proven_solved_index = _load_proven_solved_index_external


def _build_summary(tiers: Sequence[Tier], instances: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return _build_summary_external(
        tiers=tiers,
        instances=instances,
        solve_match_threshold=float(SOLVE_MATCH_THRESHOLD),
        derive_outcome_code_fn=_derive_outcome_code,
    )


def _build_iteration_runtime(
    *,
    tier: Tier,
    pt_idx: np.ndarray,
    key_seed: int,
    direction: Direction,
    span_assets_dir: Path,
    scoring_experiment_meta: Mapping[str, Any],
) -> Dict[str, Any]:
    return _build_iteration_runtime_bridge_external(
        state=globals(),
        tier=tier,
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        key_seed=int(key_seed),
        direction=direction,
        span_assets_dir=span_assets_dir,
        scoring_experiment_meta=scoring_experiment_meta,
    )


def _run_stage1_substitution(
    *,
    tier: Tier,
    text_id: int,
    key_seed: int,
    ct_idx: np.ndarray,
    pt_idx: np.ndarray,
    true_sub: np.ndarray,
    sub_len: int,
    wli: Sequence[Sequence[int]],
    direction: Direction,
    scorer_stage1: Dict[str, Any],
    scorer_stage1_runtime: Any,
    sub_cipher: PeriodicSubstitutionCipher,
    stages: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return _run_stage1_substitution_bridge_external(
        state=globals(),
        tier=tier,
        text_id=int(text_id),
        key_seed=int(key_seed),
        ct_idx=np.asarray(ct_idx, dtype=np.uint8),
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        true_sub=np.asarray(true_sub, dtype=np.int16),
        sub_len=int(sub_len),
        wli=wli,
        direction=direction,
        scorer_stage1=dict(scorer_stage1),
        scorer_stage1_runtime=scorer_stage1_runtime,
        sub_cipher=sub_cipher,
        stages=stages,
    )


def _run_stage2_search(
    *,
    tier: Tier,
    text_id: int,
    key_seed: int,
    ct_idx: np.ndarray,
    pt_idx: np.ndarray,
    wli: Sequence[Sequence[int]],
    sub_candidates: Sequence[Sequence[int]],
    direction: Direction,
    full_cipher: PeriodicColumnarCipher,
    sub_cipher: PeriodicSubstitutionCipher,
    scorer_stage2: Dict[str, Any],
    scorer_stage2_runtime: Any,
    scorer_stage2_pass1_primary_runtime: Any | None,
    scorer_stage2_pass1_fallback_runtime: Any | None,
    stages: List[Dict[str, Any]],
    oracle_assist_selection_effective: bool,
    mark_oracle_decision_use: Callable[[], None],
) -> Dict[str, Any]:
    return _run_stage2_search_bridge_external(
        state=globals(),
        tier=tier,
        text_id=int(text_id),
        key_seed=int(key_seed),
        ct_idx=np.asarray(ct_idx, dtype=np.uint8),
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        wli=wli,
        sub_candidates=sub_candidates,
        direction=direction,
        full_cipher=full_cipher,
        sub_cipher=sub_cipher,
        scorer_stage2=dict(scorer_stage2),
        scorer_stage2_runtime=scorer_stage2_runtime,
        scorer_stage2_pass1_primary_runtime=scorer_stage2_pass1_primary_runtime,
        scorer_stage2_pass1_fallback_runtime=scorer_stage2_pass1_fallback_runtime,
        stages=stages,
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        mark_oracle_decision_use=mark_oracle_decision_use,
    )


def _finalize_stage2_archive(
    *,
    tier: Tier,
    text_id: int,
    key_seed: int,
    stage2_archive: Dict[Tuple[int, ...], Dict[str, Any]],
    stage2_archive_keep: int,
    stage2_promote_top: int,
    best2_key: List[int] | None,
    best2_pt: List[int] | None,
    best2_preview: str,
    best2_score: float,
    best2_match: float,
    scorer_stage2: Dict[str, Any],
    scorer_stage2_judge_cfg: Dict[str, Any],
    scorer_stage2_judge_runtime: Any,
    scorer_full_runtime: Any,
    oracle_assist_selection_effective: bool,
    mark_oracle_decision_use: Callable[[], None],
) -> Dict[str, Any]:
    return _finalize_stage2_archive_bridge_external(
        state=globals(),
        tier=tier,
        text_id=int(text_id),
        key_seed=int(key_seed),
        stage2_archive=stage2_archive,
        stage2_archive_keep=int(stage2_archive_keep),
        stage2_promote_top=int(stage2_promote_top),
        best2_key=best2_key,
        best2_pt=best2_pt,
        best2_preview=str(best2_preview),
        best2_score=float(best2_score),
        best2_match=float(best2_match),
        scorer_stage2=dict(scorer_stage2),
        scorer_stage2_judge_cfg=dict(scorer_stage2_judge_cfg),
        scorer_stage2_judge_runtime=scorer_stage2_judge_runtime,
        scorer_full_runtime=scorer_full_runtime,
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        mark_oracle_decision_use=mark_oracle_decision_use,
    )


def _evaluate_stage3_entry_policy(
    *,
    tier: Tier,
    text_id: int,
    key_seed: int,
    best2_match: float,
    stage2_continue_to_gate: bool,
    stage2_continue_stop_reason: str,
    tier_elapsed_before_stage3: float,
    stages: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return _evaluate_stage3_entry_policy_bridge_external(
        state=globals(),
        tier=tier,
        text_id=int(text_id),
        key_seed=int(key_seed),
        best2_match=float(best2_match),
        stage2_continue_to_gate=bool(stage2_continue_to_gate),
        stage2_continue_stop_reason=str(stage2_continue_stop_reason),
        tier_elapsed_before_stage3=float(tier_elapsed_before_stage3),
        stages=stages,
    )


def _prepare_stage3_refine_inputs(
    *,
    tier: Tier,
    key_len: int,
    key_seed: int,
    best2_key: Sequence[int],
    best2_match: float,
    stage2_promoted: Sequence[Dict[str, Any]],
    stage2_entry_score: float,
    stage2_entry_score_judge: float,
    scorer_stage2: Dict[str, Any],
    scorer_full: Dict[str, Any],
    oracle_s3: float,
    oracle_decision_paths_enabled: bool,
) -> Dict[str, Any]:
    return _prepare_stage3_refine_inputs_bridge_external(
        state=globals(),
        tier=tier,
        key_len=int(key_len),
        key_seed=int(key_seed),
        best2_key=best2_key,
        best2_match=float(best2_match),
        stage2_promoted=stage2_promoted,
        stage2_entry_score=float(stage2_entry_score),
        stage2_entry_score_judge=float(stage2_entry_score_judge),
        scorer_stage2=dict(scorer_stage2),
        scorer_full=dict(scorer_full),
        oracle_s3=float(oracle_s3),
        oracle_decision_paths_enabled=bool(oracle_decision_paths_enabled),
    )


def _build_stage3_runtime_call_context() -> Stage3RuntimeCallContext:
    return _build_stage3_runtime_call_context_bridge_external(
        state=globals(),
    )


def _extract_kaeding_metrics(kaeding_obj: Any) -> Dict[str, float]:
    return _extract_kaeding_metrics_bridge_external(kaeding_obj=kaeding_obj)


def _append_stage3_topk_from_kaeding(
    *,
    payload: List[Dict[str, Any]],
    kaeding_obj: Any,
    key_len: int,
    full_cipher: PeriodicColumnarCipher,
    ciphertext: np.ndarray,
    scorer_full_runtime: Any,
    target_plaintext: np.ndarray,
) -> None:
    _append_stage3_topk_from_kaeding_bridge_external(
        state=globals(),
        payload=payload,
        kaeding_obj=kaeding_obj,
        key_len=int(key_len),
        full_cipher=full_cipher,
        ciphertext=np.asarray(ciphertext, dtype=np.uint8),
        scorer_full_runtime=scorer_full_runtime,
        target_plaintext=np.asarray(target_plaintext, dtype=np.uint8),
    )


def _append_stage3_topk_from_phasea(
    *,
    payload: List[Dict[str, Any]],
    rows: List[Dict[str, Any]],
    key_len: int,
) -> None:
    _append_stage3_topk_from_phasea_bridge_external(
        state=globals(),
        payload=payload,
        rows=rows,
        key_len=int(key_len),
    )


def _build_iteration_payloads(
    *,
    tier: Tier,
    text_id: int,
    key_seed: int,
    off: int,
    offset_used: int,
    status: str,
    stop_reason: str,
    best_stage: str,
    best_match: float,
    sub_key_match: float,
    best2_match: float,
    best3_match: float,
    stage2_gap_to_oracle: float,
    stage3_band_name: str,
    stage3_basin_judge_span_calls_total: int,
    stage3_basin_judge_span_calls_active: int,
    stage3_basin_judge_span_calls_rejected_or_gated: int,
    stage3_basin_judge_span_seconds_total: float,
    stage3_basin_judge_unique_end_hash: int,
    oracle_mode: str,
    oracle_consulted_in_decisions: bool,
    dt_i: float,
    total_evals: int,
    preview_best: str,
    outcome_code: str,
    final_best_score: float,
    oracle_scores: Dict[str, float],
    score_minus_oracle: Dict[str, float],
    ct_idx: np.ndarray,
    pt_idx: np.ndarray,
    final_best_key_idx: List[int] | None,
    final_best_plaintext_idx: List[int] | None,
    stage2_topk_payload: List[Dict[str, Any]],
    stage2_topk_has_best_match: bool,
    stage2_diagnostics: Dict[str, Any],
    stage3_topk_payload: List[Dict[str, Any]],
    stage3_diagnostics: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    return _build_iteration_payloads_bridge_external(
        state=globals(),
        tier=tier,
        text_id=int(text_id),
        key_seed=int(key_seed),
        off=int(off),
        offset_used=int(offset_used),
        status=str(status),
        stop_reason=str(stop_reason),
        best_stage=str(best_stage),
        best_match=float(best_match),
        sub_key_match=float(sub_key_match),
        best2_match=float(best2_match),
        best3_match=float(best3_match),
        stage2_gap_to_oracle=float(stage2_gap_to_oracle),
        stage3_band_name=str(stage3_band_name),
        stage3_basin_judge_span_calls_total=int(stage3_basin_judge_span_calls_total),
        stage3_basin_judge_span_calls_active=int(stage3_basin_judge_span_calls_active),
        stage3_basin_judge_span_calls_rejected_or_gated=int(stage3_basin_judge_span_calls_rejected_or_gated),
        stage3_basin_judge_span_seconds_total=float(stage3_basin_judge_span_seconds_total),
        stage3_basin_judge_unique_end_hash=int(stage3_basin_judge_unique_end_hash),
        oracle_mode=str(oracle_mode),
        oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions),
        dt_i=float(dt_i),
        total_evals=int(total_evals),
        preview_best=str(preview_best),
        outcome_code=str(outcome_code),
        final_best_score=float(final_best_score),
        oracle_scores=dict(oracle_scores),
        score_minus_oracle=dict(score_minus_oracle),
        ct_idx=np.asarray(ct_idx, dtype=np.uint8),
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        final_best_key_idx=final_best_key_idx,
        final_best_plaintext_idx=final_best_plaintext_idx,
        stage2_topk_payload=stage2_topk_payload,
        stage2_topk_has_best_match=bool(stage2_topk_has_best_match),
        stage2_diagnostics=stage2_diagnostics,
        stage3_topk_payload=stage3_topk_payload,
        stage3_diagnostics=stage3_diagnostics,
    )


def _commit_iteration_outputs(
    *,
    run_dir: Path,
    final_dir: Path,
    root: Path,
    hist_path: Path,
    tiers: Sequence[Tier],
    instances: List[Dict[str, Any]],
    stages: List[Dict[str, Any]],
    inst_row: Dict[str, Any],
    artifact_payload: Dict[str, Any],
    done: int,
    total: int,
    t0_all: float,
    last_hb: float,
    heartbeat_seconds: float,
    best_global: Dict[str, Any],
    history_rows_written: int,
    audit_rows_written: int,
    audit_enabled: bool,
    audit_csv: Path,
    audit_jsonl: Path,
    audit_prev_chain_hash: str,
) -> Dict[str, Any]:
    return _commit_iteration_outputs_bridge_external(
        state=globals(),
        run_dir=run_dir,
        final_dir=final_dir,
        root=root,
        hist_path=hist_path,
        tiers=tiers,
        instances=instances,
        stages=stages,
        inst_row=inst_row,
        artifact_payload=artifact_payload,
        done=int(done),
        total=int(total),
        t0_all=float(t0_all),
        last_hb=float(last_hb),
        heartbeat_seconds=float(heartbeat_seconds),
        best_global=dict(best_global),
        history_rows_written=int(history_rows_written),
        audit_rows_written=int(audit_rows_written),
        audit_enabled=bool(audit_enabled),
        audit_csv=audit_csv,
        audit_jsonl=audit_jsonl,
        audit_prev_chain_hash=str(audit_prev_chain_hash),
    )


def main() -> None:
    global STAGE3_SPAN_BASIN_JUDGE_K, _RUN_STAGE3_SPAN_BASIN_K_SWEEP_ACTIVE
    if bool(RUN_STAGE3_SPAN_BASIN_K_SWEEP) and (not bool(_RUN_STAGE3_SPAN_BASIN_K_SWEEP_ACTIVE)):
        sweep_vals: List[int] = []
        for raw_k in list(STAGE3_SPAN_BASIN_K_SWEEP_VALUES):
            try:
                k_i = int(raw_k)
            except Exception:
                continue
            if k_i <= 0:
                continue
            if k_i not in sweep_vals:
                sweep_vals.append(int(k_i))
        if not sweep_vals:
            raise ValueError(
                "RUN_STAGE3_SPAN_BASIN_K_SWEEP enabled but STAGE3_SPAN_BASIN_K_SWEEP_VALUES is empty/invalid."
            )
        print(
            f"[pipeline_no_wli] stage3-span-basin-k-sweep enabled=1 values={sweep_vals} "
            f"mode={_canonical_run_mode(PIPELINE_RUN_MODE)}",
            flush=True,
        )
        _RUN_STAGE3_SPAN_BASIN_K_SWEEP_ACTIVE = True
        try:
            for sweep_idx, k_i in enumerate(sweep_vals, start=1):
                _apply_profile_defaults()
                STAGE3_SPAN_BASIN_JUDGE_K = int(k_i)
                print(
                    f"[pipeline_no_wli] stage3-span-basin-k-sweep run={int(sweep_idx)}/{int(len(sweep_vals))} "
                    f"k={int(STAGE3_SPAN_BASIN_JUDGE_K)}",
                    flush=True,
                )
                main()
        finally:
            _RUN_STAGE3_SPAN_BASIN_K_SWEEP_ACTIVE = False
        return

    _apply_run_mode()
    _apply_kaeding_progress_settings()
    scoring_experiment_meta = _apply_scoring_experiment_profile()
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
    audit_csv = run_dir / str(AUDIT_HASH_CHAIN_CSV)
    audit_jsonl = run_dir / str(AUDIT_HASH_CHAIN_JSONL)
    audit_prev_chain_hash = str(AUDIT_HASH_CHAIN_SEED)
    audit_rows_written = 0
    hist = root / "tools" / "benchmarks" / "solve_proof" / "proven_solve_pipeline_no_wli_log.csv"
    hist.parent.mkdir(parents=True, exist_ok=True)
    autoskip_effective = bool(AUTOSKIP_PROVEN) and (not bool(FORCE_RERUN_PROVEN))
    proven_index = (
        _load_proven_solved_index(hist, min_match=float(AUTOSKIP_PROVEN_MIN_MATCH))
        if autoskip_effective
        else {}
    )
    history_rows_written = 0

    mode_info = _build_run_mode_info(PIPELINE_RUN_MODE)
    mode_raw = str(mode_info.mode_raw)
    mode_canonical = str(mode_info.mode_canonical)
    mode_intent = str(mode_info.intent)
    stage3_can_skip = bool(mode_info.stage3_can_skip)
    oracle_mode = str(_oracle_mode_normalized())
    oracle_decision_paths_enabled = bool(oracle_mode == "benchmark_only")
    oracle_assist_selection_effective = bool(
        oracle_decision_paths_enabled and bool(ORACLE_ASSIST_SELECTION)
    )
    oracle_consulted_in_decisions = False

    def _mark_oracle_decision_use() -> None:
        nonlocal oracle_consulted_in_decisions
        if bool(oracle_decision_paths_enabled):
            oracle_consulted_in_decisions = True

    run_config = dict(
        profile=PROFILE,
        mode=mode_canonical,
        mode_raw=mode_raw,
        mode_intent=mode_intent,
        stage3_can_skip=bool(stage3_can_skip),
        stage3_phase_experiments=(
            dict(
                enabled=bool(_is_adaptive_focus_mode(mode_canonical)),
                phaseA="a_baseline" if _is_adaptive_focus_mode(mode_canonical) else str(scoring_experiment_meta.get("profile", "off")),
                phaseB="c_min_late" if _is_adaptive_focus_mode(mode_canonical) else str(scoring_experiment_meta.get("profile", "off")),
                phaseB_char_pct_min_policy=(
                    "oracle_minus_0.10_clamp_0.30_0.45_not_applied_explicit_basin_judge"
                    if _is_adaptive_focus_mode(mode_canonical)
                    else "static_config"
                ),
            )
        ),
        scoring_experiment=_scoring_meta_for_output(
            dict(scoring_experiment_meta), root=root
        ),
        direction=direction.value,
        order=ORDER,
        alphabet_size=int(ALPHABET_SIZE),
        threshold=float(SOLVE_MATCH_THRESHOLD),
        stall_delta=float(STALL_DELTA),
        stall_stage_limit=int(STALL_STAGE_LIMIT),
        scan_controls=dict(
            tier_time_cap_seconds=float(SCAN_TIER_TIME_CAP_SECONDS),
            stage2_continue_to_gate=bool(SCAN_STAGE2_CONTINUE_TO_GATE),
            stage2_continue_cap_seconds=float(SCAN_STAGE2_CONTINUE_CAP_SECONDS),
            stage3_gate_low_match=float(SCAN_STAGE3_GATE_LOW_MATCH),
            stage3_gate_high_match=float(max(float(SCAN_STAGE3_GATE_LOW_MATCH), float(SCAN_STAGE3_GATE_HIGH_MATCH))),
            stage3_min_stage2_match=float(SCAN_STAGE3_MIN_STAGE2_MATCH),
        ),
        autoskip_proven=bool(autoskip_effective),
        autoskip_proven_requested=bool(AUTOSKIP_PROVEN),
        force_rerun_proven=bool(FORCE_RERUN_PROVEN),
        autoskip_proven_min_match=float(AUTOSKIP_PROVEN_MIN_MATCH),
        autoskip_proven_known=int(len(proven_index)),
        oracle_mode=str(oracle_mode),
        oracle_assist_selection_requested=bool(ORACLE_ASSIST_SELECTION),
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        oracle_consulted_in_decisions=bool(oracle_decision_paths_enabled),
        text_offsets=list(map(int, TEXT_OFFSETS)),
        key_seeds=list(map(int, KEY_SEEDS)),
        tiers=[
            dict(
                name=str(t.name),
                period=int(t.period),
                columns=int(t.columns),
                length=int(t.length),
            )
            for t in TIERS
        ],
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
            scorer=_scorer_cfg_for_output(dict(SCORER_STAGE1), root=root),
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
            scorer=_scorer_cfg_for_output(dict(SCORER_STAGE2), root=root),
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
                policy=str(STAGE2_JUDGE_POLICY),
                topk_default=int(SAVE_STAGE2_TOPK),
                promote_by_stage3_judge=bool(STAGE2_PROMOTE_BY_STAGE3_JUDGE),
                entry_band_by_stage3_judge=bool(STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE),
            ),
        ),
        stage3=dict(
            scorer=_scorer_cfg_for_output(dict(SCORER_FULL), root=root),
            search_scorer=dict(
                _scorer_cfg_for_output(
                    _stage3_char4_avg_fulltext_search_cfg(direction=direction),
                    root=root,
                ),
                encoding_dir=str(direction.value),
            ),
            judge_scorer=_scorer_cfg_for_output(dict(SCORER_FULL), root=root),
            contract=(
                "Stage-3 Kaeding search optimizes avg/full_text char4 only (ECDF-free); "
                "span-hamming is used only in explicit basin-judge ranking of Phase-A endpoints "
                "before selecting Phase-B seeds."
            ),
            solver=dict(SOLVER_STAGE3),
            init_keys=int(STAGE3_INITIAL_KEYS),
            init_by_columns={str(k): int(v) for k, v in STAGE3_INITIAL_KEYS_BY_COLUMNS.items()},
            span_basin_judge=dict(
                enabled=bool(True),
                k=int(STAGE3_SPAN_BASIN_JUDGE_K),
                require_span_active=bool(STAGE3_SPAN_BASIN_JUDGE_REQUIRE_SPAN_ACTIVE),
                dedupe_by_end_hash=bool(STAGE3_SPAN_BASIN_JUDGE_DEDUPE_BY_END_HASH),
                tie_eps=float(STAGE3_SPAN_BASIN_JUDGE_TIE_EPS),
                tie_max_seeds=int(STAGE3_SPAN_BASIN_JUDGE_TIE_MAX_SEEDS),
                disable_char_pct_gate=bool(True),
                gate_fail_policy="score_floor",
            ),
            period_scaling=dict(
                init_mult_by_period={str(k): float(v) for k, v in STAGE3_PERIOD_INIT_MULT_BY_PERIOD.items()},
                step_mult_by_period={str(k): float(v) for k, v in STAGE3_PERIOD_STEP_MULT_BY_PERIOD.items()},
                restart_bonus_by_period={str(k): int(v) for k, v in STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD.items()},
                init_keys_cap=int(STAGE3_INIT_KEYS_CAP),
            ),
            dynamic_bands=[dict(b) for b in STAGE3_DYNAMIC_BANDS],
            two_phase=dict(
                enabled=bool(STAGE3_TWO_PHASE_ENABLED),
                continue_after_solve=bool(STAGE3_CONTINUE_AFTER_SOLVE),
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
    run_config_path = run_dir / "run_config.json"
    write_json(run_config_path, run_config)
    non_scoring_lock_hash = _hash_payload(_build_non_scoring_lock_payload())
    scoring_lock_hash = _hash_payload(_build_scoring_lock_payload())
    run_config_payload_hash = _hash_payload(run_config)
    run_config["lock_hashes"] = dict(
        non_scoring=str(non_scoring_lock_hash),
        scoring=str(scoring_lock_hash),
        run_config_payload=str(run_config_payload_hash),
    )
    run_config["git"] = dict(short=str(_git_short()), commit=str(_git_commit()), dirty=int(1 if _git_dirty() else 0))
    write_json(run_config_path, run_config)
    run_config_hash = _sha256_file(run_config_path)

    span_assets_dir = _resolve_repo_path(str(scoring_experiment_meta.get("span_assets_dir", "")).strip() or None)
    span_combined_calibration_hash = ""
    span_ecdf_audit_hash = ""
    if span_assets_dir is not None and span_assets_dir.exists():
        combined_fp = span_assets_dir / "combined_calibration.json"
        ecdf_audit_fp = span_assets_dir / "ecdf_audit.json"
        if combined_fp.exists():
            span_combined_calibration_hash = _sha256_file(combined_fp)
        if ecdf_audit_fp.exists():
            span_ecdf_audit_hash = _sha256_file(ecdf_audit_fp)

    _stage3_search_cfg_preview = _stage3_char4_avg_fulltext_search_cfg(
        direction=direction
    )
    _emit_setup_logging_external(
        profile=str(PROFILE),
        mode_canonical=str(mode_canonical),
        mode_raw=str(mode_raw),
        mode_intent=str(mode_intent),
        stage3_can_skip=bool(stage3_can_skip),
        direction_value=str(direction.value),
        order=str(ORDER),
        alphabet_size=int(ALPHABET_SIZE),
        oracle_mode=str(oracle_mode),
        oracle_assist_selection_requested=bool(ORACLE_ASSIST_SELECTION),
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        autoskip_effective=bool(autoskip_effective),
        autoskip_requested=bool(AUTOSKIP_PROVEN),
        force_rerun_proven=bool(FORCE_RERUN_PROVEN),
        autoskip_min_match=float(AUTOSKIP_PROVEN_MIN_MATCH),
        proven_known=int(len(proven_index)),
        hist_rel_path=str(hist.relative_to(root)),
        profile_id=str(NO_WLI_PIPELINE_PROFILE_ID),
        profile_previous_default=str(NO_WLI_PIPELINE_PROFILE_ID_PREVIOUS_DEFAULT),
        scorer_impl_stage12=str(getattr(SCORER_IMPL, "value", SCORER_IMPL)),
        scorer_impl_stage3=str(SCORER_FULL.get("impl", SCORER_IMPL)),
        scorer_stage1_label=str(SCORER_STAGE1_LABEL),
        scorer_stage2_label=str(SCORER_STAGE2_LABEL),
        scorer_stage3_label=str(SCORER_STAGE3_LABEL),
        scorer_stage1_summary=str(_scorer_objective_summary(SCORER_STAGE1)),
        scorer_stage2_summary=str(_scorer_objective_summary(SCORER_STAGE2)),
        scorer_stage3_summary=str(_scorer_objective_summary(SCORER_FULL)),
        require_no_ecdf_for_avg_fulltext=bool(REQUIRE_NO_ECDF_FOR_AVG_FULLTEXT),
        stage3_search_summary=str(_scorer_objective_summary(_stage3_search_cfg_preview)),
        stage3_judge_summary=str(_scorer_objective_summary(SCORER_FULL)),
        stage3_basin_judge_k=int(STAGE3_SPAN_BASIN_JUDGE_K),
        scoring_experiment_profile=str(scoring_experiment_meta.get("profile", "off")),
        scoring_experiment_enabled=bool(scoring_experiment_meta.get("enabled", False)),
        scoring_experiment_desc=str(scoring_experiment_meta.get("description", "")),
        phase_experiments_enabled=bool(
            run_config.get("stage3_phase_experiments", {}).get("enabled", False)
        ),
        phase_experiments_phaseA=str(
            run_config.get("stage3_phase_experiments", {}).get("phaseA", "off")
        ),
        phase_experiments_phaseB=str(
            run_config.get("stage3_phase_experiments", {}).get("phaseB", "off")
        ),
        phase_experiments_phaseB_char_gate_policy=str(
            run_config.get("stage3_phase_experiments", {}).get(
                "phaseB_char_pct_min_policy", "static_config"
            )
        ),
        non_scoring_lock_hash=str(non_scoring_lock_hash),
        scoring_lock_hash=str(scoring_lock_hash),
        run_config_hash=str(run_config_hash),
        stage1_seed_restarts=int(STAGE1_SEED_RESTARTS),
        stage1_seed_n_blocks=int(STAGE1_SEED_N_BLOCKS),
        stage1_seed_total=int(STAGE1_SEED_TOTAL),
        stage1_seed_swaps=int(STAGE1_SEED_SWAPS),
        stage12_scout_runs=int(STAGE12_SCOUT_RUNS),
        stage12_archive_keep=int(STAGE12_ARCHIVE_KEEP),
        stage12_promote_top=int(STAGE12_PROMOTE_TOP),
        stage1_scout_step_scale=float(STAGE1_SCOUT_STEP_SCALE),
        stage1_scout_restart_scale=float(STAGE1_SCOUT_RESTART_SCALE),
        stage1_scout_min_steps=int(STAGE1_SCOUT_MIN_STEPS),
        stage1_scout_min_restarts=int(STAGE1_SCOUT_MIN_RESTARTS),
        stage1_scout_no_improve_delta=float(STAGE1_SCOUT_NO_IMPROVE_DELTA),
        stage1_scout_no_improve_patience=int(STAGE1_SCOUT_NO_IMPROVE_PATIENCE),
        stage1_scout_min_new_archive=int(STAGE1_SCOUT_MIN_NEW_ARCHIVE),
        stage1_scout_early_stop_min_scouts=int(STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS),
        stage1_sub_candidates=int(STAGE1_SUB_CANDIDATES),
        stage1_sub_candidates_by_columns=dict(STAGE1_SUB_CANDIDATES_BY_COLUMNS),
        stage3_initial_keys=int(STAGE3_INITIAL_KEYS),
        stage3_initial_keys_by_columns=dict(STAGE3_INITIAL_KEYS_BY_COLUMNS),
        stage3_period_init_mult_by_period=dict(STAGE3_PERIOD_INIT_MULT_BY_PERIOD),
        stage3_period_step_mult_by_period=dict(STAGE3_PERIOD_STEP_MULT_BY_PERIOD),
        stage3_period_restart_bonus_by_period=dict(STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD),
        stage3_init_keys_cap=int(STAGE3_INIT_KEYS_CAP),
        stage2_exact_max_columns=int(STAGE2_EXACT_MAX_COLUMNS),
        stage2_exact_sub_candidates=int(STAGE2_EXACT_SUB_CANDIDATES),
        stage2_exact_sub_candidates_by_columns=dict(STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS),
        stage2_pass1_primary_text=str(_weights_text(STAGE2_PASS1_PRIMARY_CHAR_WEIGHTS)),
        stage2_pass1_fallback_text=str(_weights_text(STAGE2_PASS1_FALLBACK_CHAR_WEIGHTS)),
        stage2_hybrid_sub_candidates=int(STAGE2_HYBRID_SUB_CANDIDATES),
        stage2_hybrid_sub_candidates_by_columns=dict(STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS),
        stage3_two_phase_enabled=bool(STAGE3_TWO_PHASE_ENABLED),
        stage3_phasea_cfg=dict(STAGE3_PHASEA_CFG),
        stage3_phaseb_cfg=dict(STAGE3_PHASEB_CFG),
        stage3_phaseb_top_n=int(STAGE3_PHASEB_TOP_N),
        stage3_continue_after_solve=bool(STAGE3_CONTINUE_AFTER_SOLVE),
        stage3_phaseb_gate_delta_floor=float(STAGE3_PHASEB_GATE_DELTA_FLOOR),
        stage3_phaseb_gate_end_gain_floor=float(STAGE3_PHASEB_GATE_END_GAIN_FLOOR),
        stage3_c1_focus_enabled=bool(STAGE3_C1_FOCUS_ENABLED),
        stage3_c1_init_keys=int(STAGE3_C1_INIT_KEYS),
        stage3_c1_phasea_steps=int(STAGE3_C1_PHASEA_STEPS),
        stage3_c1_phaseb_steps=int(STAGE3_C1_PHASEB_STEPS),
        stage3_c1_phaseb_top_n=int(STAGE3_C1_PHASEB_TOP_N),
        stage3_c1_phaseb_gate_delta_floor=float(STAGE3_C1_PHASEB_GATE_DELTA_FLOOR),
        stage3_c1_phaseb_gate_end_gain_floor=float(STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR),
        scan_tier_time_cap_seconds=float(SCAN_TIER_TIME_CAP_SECONDS),
        scan_stage2_continue_to_gate=bool(SCAN_STAGE2_CONTINUE_TO_GATE),
        scan_stage2_continue_cap_seconds=float(SCAN_STAGE2_CONTINUE_CAP_SECONDS),
        scan_stage3_gate_low_match=float(SCAN_STAGE3_GATE_LOW_MATCH),
        scan_stage3_gate_high_match=float(
            max(float(SCAN_STAGE3_GATE_LOW_MATCH), float(SCAN_STAGE3_GATE_HIGH_MATCH))
        ),
        tiers_count=int(len(TIERS)),
        text_offsets=list(map(int, TEXT_OFFSETS)),
        key_seeds=list(map(int, KEY_SEEDS)),
        reports_rel_path=str(run_dir.relative_to(root)),
        audit_csv_rel_path=str(audit_csv.relative_to(root)),
        audit_jsonl_rel_path=str(audit_jsonl.relative_to(root)),
        log_prefix="[pipeline_no_wli]",
    )

    stages: List[dict] = []
    instances: List[dict] = []
    total = len(TIERS) * len(TEXT_OFFSETS) * len(KEY_SEEDS)
    done = 0
    t0_all = time.time()
    last_hb = float(t0_all)
    status_counts: Dict[str, int] = {
        "solved": 0,
        "stalled": 0,
        "unsolved": 0,
        "skipped_proven": 0,
    }
    run_manifest_path = run_dir / "run_manifest.json"
    run_manifest: Dict[str, Any] = dict(
        kind="bench_solve_pipeline_no_wli",
        version=2,
        run_status="running",
        run_id=str(run_dir.name),
        generated_utc=datetime.now(timezone.utc).isoformat(),
        updated_utc=datetime.now(timezone.utc).isoformat(),
        completed_utc="",
        profile_id=str(PROFILE),
        mode=str(_canonical_run_mode(PIPELINE_RUN_MODE)),
        oracle_mode=str(oracle_mode),
        oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions),
        oracle_assist_selection_requested=bool(ORACLE_ASSIST_SELECTION),
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        direction=str(direction.value),
        order=str(ORDER),
        runtime=dict(
            python=str(sys.version.split()[0]),
            platform=str(platform.platform()),
        ),
        git=dict(
            short=str(_git_short()),
            commit=str(_git_commit()),
            dirty=int(1 if _git_dirty() else 0),
        ),
        scoring_experiment=_scoring_meta_for_output(
            dict(scoring_experiment_meta), root=root
        ),
        lock_hashes=dict(
            non_scoring=str(non_scoring_lock_hash),
            scoring=str(scoring_lock_hash),
            run_config=str(run_config_hash),
        ),
        assets=dict(
            span_assets_dir=_to_repo_rel_path(span_assets_dir, root=root),
            span_combined_calibration_sha256=str(span_combined_calibration_hash),
            span_ecdf_audit_sha256=str(span_ecdf_audit_hash),
        ),
        paths=dict(
            run_config=str(run_config_path.relative_to(root)),
            history_log=str(hist.relative_to(root)),
            final_instances=str(final_dir.relative_to(root)),
            audit_chain_csv=str(audit_csv.relative_to(root)),
            audit_chain_jsonl=str(audit_jsonl.relative_to(root)),
        ),
        audit=dict(
            enabled=int(1 if bool(AUDIT_HASH_CHAIN_ENABLED) else 0),
            chain_algorithm="sha256(prev_chain_hash|row_hash)",
            chain_seed=str(AUDIT_HASH_CHAIN_SEED),
        ),
        progress=dict(
            total_units=int(total),
            done_units=0,
            solved=0,
            stalled=0,
            unsolved=0,
            skipped_proven=0,
            history_rows_written=0,
            audit_rows_written=0,
            audit_last_chain_hash=str(audit_prev_chain_hash),
        ),
    )
    write_json(run_manifest_path, run_manifest)

    def _checkpoint_manifest(*, status_key: str) -> None:
        sk = str(status_key)
        if sk in status_counts:
            status_counts[sk] = int(status_counts[sk]) + 1
        run_manifest["updated_utc"] = datetime.now(timezone.utc).isoformat()
        run_manifest["oracle_consulted_in_decisions"] = bool(
            oracle_consulted_in_decisions
        )
        run_manifest["progress"] = dict(
            total_units=int(total),
            done_units=int(done),
            solved=int(status_counts.get("solved", 0)),
            stalled=int(status_counts.get("stalled", 0)),
            unsolved=int(status_counts.get("unsolved", 0)),
            skipped_proven=int(status_counts.get("skipped_proven", 0)),
            history_rows_written=int(history_rows_written),
            audit_rows_written=int(audit_rows_written),
            audit_last_chain_hash=str(audit_prev_chain_hash),
        )
        write_json(run_manifest_path, run_manifest)

    def _commit_iteration_with_checkpoint(
        *,
        inst_row: Dict[str, Any],
        artifact_payload: Dict[str, Any],
        status_key: str,
    ) -> None:
        nonlocal done, last_hb, best_global, history_rows_written, audit_rows_written, audit_prev_chain_hash

        commit_state = _commit_iteration_outputs(
            run_dir=run_dir,
            final_dir=final_dir,
            root=root,
            hist_path=hist,
            tiers=TIERS,
            instances=instances,
            stages=stages,
            inst_row=dict(inst_row),
            artifact_payload=artifact_payload,
            done=int(done),
            total=int(total),
            t0_all=float(t0_all),
            last_hb=float(last_hb),
            heartbeat_seconds=float(HEARTBEAT_SECONDS),
            best_global=dict(best_global),
            history_rows_written=int(history_rows_written),
            audit_rows_written=int(audit_rows_written),
            audit_enabled=bool(AUDIT_HASH_CHAIN_ENABLED),
            audit_csv=audit_csv,
            audit_jsonl=audit_jsonl,
            audit_prev_chain_hash=str(audit_prev_chain_hash),
        )
        done = int(commit_state["done"])
        last_hb = float(commit_state["last_hb"])
        best_global = dict(commit_state["best_global"])
        history_rows_written = int(commit_state["history_rows_written"])
        audit_rows_written = int(commit_state["audit_rows_written"])
        audit_prev_chain_hash = str(commit_state["audit_prev_chain_hash"])
        _checkpoint_manifest(status_key=str(status_key))

    best_global = {"match": float("-inf"), "tier": "", "text_id": -1, "key_seed": -1, "stage": "", "preview": ""}
    stage3_runtime_call_ctx = _build_stage3_runtime_call_context()
    def _get_oracle_consulted_in_decisions() -> bool:
        return bool(oracle_consulted_in_decisions)

    _run_iteration_matrix_external(
        tiers=TIERS,
        text_offsets=TEXT_OFFSETS,
        key_seeds=KEY_SEEDS,
        pt_base=pt_base,
        wli_base=wli_base,
        direction=direction,
        span_assets_dir=span_assets_dir,
        scoring_experiment_meta=dict(scoring_experiment_meta),
        autoskip_effective=bool(autoskip_effective),
        proven_index=proven_index,
        instances=instances,
        stages=stages,
        stage3_runtime_call_ctx=stage3_runtime_call_ctx,
        config=IterationMatrixConfig(
            stage1_label=str(SCORER_STAGE1_LABEL),
            stage2_label=str(SCORER_STAGE2_LABEL),
            stage3_label=str(SCORER_STAGE3_LABEL),
            stage3_continue_after_solve=bool(STAGE3_CONTINUE_AFTER_SOLVE),
            stage3_phaseb_top_n=int(STAGE3_PHASEB_TOP_N),
            stage3_phaseb_gate_delta_floor=float(STAGE3_PHASEB_GATE_DELTA_FLOOR),
            stage3_phaseb_gate_end_gain_floor=float(STAGE3_PHASEB_GATE_END_GAIN_FLOOR),
            stage3_c1_focus_enabled=bool(STAGE3_C1_FOCUS_ENABLED),
            stage3_span_char_pct_min_override=(
                float(STAGE3_SPAN_CHAR_PCT_MIN_OVERRIDE)
                if STAGE3_SPAN_CHAR_PCT_MIN_OVERRIDE is not None
                else None
            ),
            scoring_experiment_c_char_pct_min=float(SCORING_EXPERIMENT_C_CHAR_PCT_MIN),
            oracle_stage3_floor_guard_eps=float(ORACLE_STAGE3_FLOOR_GUARD_EPS),
            stage3_two_phase_enabled=bool(STAGE3_TWO_PHASE_ENABLED),
            stage3_phasea_cfg_default=dict(STAGE3_PHASEA_CFG),
            stage3_phaseb_cfg_default=dict(STAGE3_PHASEB_CFG),
            solver_stage3_default_cfg=dict(SOLVER_STAGE3),
            stage3_span_basin_judge_k=int(STAGE3_SPAN_BASIN_JUDGE_K),
            tier_heartbeat_seconds=float(TIER_HEARTBEAT_SECONDS),
            solve_match_threshold=float(SOLVE_MATCH_THRESHOLD),
            stall_delta=float(STALL_DELTA),
            stall_stage_limit=int(STALL_STAGE_LIMIT),
            scan_stage3_gate_low_match=float(SCAN_STAGE3_GATE_LOW_MATCH),
            scan_stage3_gate_high_match=float(
                max(float(SCAN_STAGE3_GATE_LOW_MATCH), float(SCAN_STAGE3_GATE_HIGH_MATCH))
            ),
            oracle_mode=str(oracle_mode),
            oracle_decision_paths_enabled=bool(oracle_decision_paths_enabled),
            oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        ),
        fns=IterationMatrixFns(
            slice_word_aligned_fn=base._slice_word_aligned,
            get_oracle_consulted_in_decisions_fn=_get_oracle_consulted_in_decisions,
            handle_autoskip_proven_iteration_fn=_handle_autoskip_proven_iteration_external,
            run_iteration_pre_stage3_fn=_run_iteration_pre_stage3_external,
            run_stage3_iteration_flow_fn=_run_stage3_iteration_flow_external,
            finalize_iteration_post_stage3_fn=_finalize_iteration_post_stage3_external,
            build_iteration_payloads_fn=_build_iteration_payloads,
            derive_outcome_code_fn=_derive_outcome_code,
            commit_iteration_with_checkpoint_fn=_commit_iteration_with_checkpoint,
            build_iteration_runtime_fn=_build_iteration_runtime,
            evaluate_oracle_precheck_fn=_evaluate_oracle_precheck_external,
            handle_oracle_floor_guard_if_triggered_fn=_handle_oracle_floor_guard_if_triggered_external,
            run_stage12_pipeline_fn=_run_stage12_pipeline_external,
            scorer_objective_summary_fn=_scorer_objective_summary,
            oracle_score_for_stage_fn=_oracle_score_for_stage,
            weights_text_fn=_weights_text,
            mark_oracle_decision_use_fn=_mark_oracle_decision_use,
            print_stage_preview_fn=_print_stage_preview,
            build_oracle_floor_guard_result_fn=_build_oracle_floor_guard_result_external,
            run_stage1_substitution_fn=_run_stage1_substitution,
            run_stage2_search_fn=_run_stage2_search,
            finalize_stage2_archive_fn=_finalize_stage2_archive,
            evaluate_stage3_entry_policy_fn=_evaluate_stage3_entry_policy,
            prepare_stage3_refine_inputs_fn=_prepare_stage3_refine_inputs,
            summarize_stage3_span_fn=_summarize_stage3_span_external,
            fmt_finite_float_fn=_fmt_finite_float,
            build_stage2_diagnostics_fn=_build_stage2_diagnostics_external,
            build_stage3_diagnostics_fn=_build_stage3_diagnostics_external,
            finalize_iteration_and_commit_fn=_finalize_iteration_and_commit_external,
            safe_preview_latin_fn=base._safe_preview_latin,
        ),
        log_prefix="[pipeline_no_wli]",
    )

    _finalize_run_outputs_external(
        run_dir=run_dir,
        final_dir=final_dir,
        best_dir=best_dir,
        root=root,
        hist_path=hist,
        t0_all=float(t0_all),
        oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions),
        total=int(total),
        done=int(done),
        status_counts=status_counts,
        history_rows_written=int(history_rows_written),
        audit_rows_written=int(audit_rows_written),
        audit_prev_chain_hash=str(audit_prev_chain_hash),
        tiers=TIERS,
        instances=instances,
        stages=stages,
        run_manifest=run_manifest,
        run_manifest_path=run_manifest_path,
        write_json_fn=write_json,
        write_pipeline_snapshot_files_fn=write_pipeline_snapshot_files,
        build_summary_fn=_build_summary,
        sha256_file_fn=_sha256_file,
        format_seconds_fn=lambda seconds: base._format_seconds(float(seconds)),
        log_prefix="[pipeline_no_wli]",
    )


if __name__ == "__main__":
    main()


