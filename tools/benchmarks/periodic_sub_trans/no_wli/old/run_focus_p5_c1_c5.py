from __future__ import annotations

"""No-WLI benchmark launcher: period=5, columns=1..5.

This is a thin run-file on top of the no_wli runner with hardcoded knobs for
quick iteration on low-period solveability.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.benchmarks.periodic_sub_trans.no_wli import runner as no_wli


# Primary solve-mode profile for period-5 campaign.
# Keep legacy runner untouched; this launcher applies solve-first overrides only
# in the new periodic_sub_trans framework.
NO_WLI_PROFILE_ID = "no_wli_a1_m34_b34_v1"

# Grid for this launcher.
PERIOD = 5
COLUMNS = [1, 2, 3, 4, 5]
TEXT_LENGTH = 452
TEXT_OFFSETS = [0]
KEY_SEEDS = [111]

# Solve-first budget shaping for this low-period campaign.
STAGE1_SCOUT_RUNS = 3
STAGE1_SEED_RESTARTS = 64
STAGE1_SEED_TOTAL = 128
STAGE1_SCOUT_MIN_STEPS = 600
STAGE1_SUB_CANDIDATES = 96
STAGE12_ARCHIVE_KEEP = 128
STAGE12_PROMOTE_TOP = 48
STAGE2_EXACT_TWO_PASS = False
STAGE2_EXACT_SUB_CANDIDATES = 64
STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS = {
    1: 96,
    2: 96,
    3: 96,
    4: 80,
    5: 80,
}
STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS = {
    1: 1,
    2: 2,
    3: 6,
    4: 24,
    5: 120,
}
STAGE3_INITIAL_KEYS = 24
STAGE3_INITIAL_KEYS_BY_COLUMNS = {
    1: 24,
    2: 24,
    3: 24,
    4: 24,
    5: 24,
}
STAGE3_DYNAMIC_BANDS_SOLVE = [
    {"name": "very_close", "max_gap": 0.010, "steps": 400, "restarts": 8, "plateau_rounds": 120, "col_batch": 64, "inner_batch": 96},
    {"name": "close", "max_gap": 0.030, "steps": 600, "restarts": 12, "plateau_rounds": 140, "col_batch": 64, "inner_batch": 96},
    {"name": "mid", "max_gap": 0.080, "steps": 700, "restarts": 16, "plateau_rounds": 160, "col_batch": 80, "inner_batch": 96},
    {"name": "far", "max_gap": 1e9, "steps": 800, "restarts": 24, "plateau_rounds": 180, "col_batch": 80, "inner_batch": 96},
]
STAGE3_TWO_PHASE_ENABLED = True
STAGE3_PHASEA_CFG = {
    "steps": 350,
    "restarts": 1,
    "inner_batch": 64,
    "col_every": 1,
    "col_batch": 64,
    "slip_every": 0,
    "slip_swaps": 0,
    "stall_slip_limit": 0,
}
STAGE3_PHASEB_CFG = {
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


def main() -> None:
    # Re-apply profile after changing id so scorer/solver defaults match profile.
    no_wli.NO_WLI_PIPELINE_PROFILE_ID = str(NO_WLI_PROFILE_ID)
    no_wli._apply_profile_defaults()

    # Keep run-mode from overriding this launcher's explicit grid.
    no_wli.PIPELINE_RUN_MODE = "full"
    no_wli.PROFILE = f"{NO_WLI_PROFILE_ID}__p{PERIOD}_c1_c5"

    no_wli.TEXT_OFFSETS[:] = list(TEXT_OFFSETS)
    no_wli.KEY_SEEDS[:] = list(KEY_SEEDS)
    no_wli.TIERS[:] = [
        no_wli.Tier(name=f"focus_p{PERIOD}_c{int(c)}_l{TEXT_LENGTH}", period=PERIOD, columns=int(c), length=TEXT_LENGTH)
        for c in COLUMNS
    ]

    # Budget/selection overrides for this campaign.
    no_wli.STAGE12_SCOUT_RUNS = int(STAGE1_SCOUT_RUNS)
    no_wli.STAGE1_SEED_RESTARTS = int(STAGE1_SEED_RESTARTS)
    no_wli.STAGE1_SEED_TOTAL = int(STAGE1_SEED_TOTAL)
    no_wli.STAGE1_SCOUT_MIN_STEPS = int(STAGE1_SCOUT_MIN_STEPS)
    no_wli.STAGE1_SUB_CANDIDATES = int(STAGE1_SUB_CANDIDATES)
    no_wli.STAGE12_ARCHIVE_KEEP = int(STAGE12_ARCHIVE_KEEP)
    no_wli.STAGE12_PROMOTE_TOP = int(STAGE12_PROMOTE_TOP)
    no_wli.STAGE2_EXACT_MAX_COLUMNS = 5
    no_wli.STAGE2_EXACT_TWO_PASS = bool(STAGE2_EXACT_TWO_PASS)
    no_wli.STAGE2_EXACT_SUB_CANDIDATES = int(STAGE2_EXACT_SUB_CANDIDATES)
    no_wli.STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS = {
        int(k): int(v) for k, v in STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS.items()
    }
    no_wli.STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS = {
        int(k): int(v) for k, v in STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS.items()
    }
    no_wli.STAGE3_INITIAL_KEYS = int(STAGE3_INITIAL_KEYS)
    no_wli.STAGE3_INITIAL_KEYS_BY_COLUMNS = {
        int(k): int(v) for k, v in STAGE3_INITIAL_KEYS_BY_COLUMNS.items()
    }
    no_wli.STAGE3_DYNAMIC_BANDS = [dict(b) for b in STAGE3_DYNAMIC_BANDS_SOLVE]
    no_wli.SOLVER_STAGE1 = dict(no_wli.SOLVER_STAGE1, seed_restarts=int(STAGE1_SEED_RESTARTS))
    no_wli.STAGE3_TWO_PHASE_ENABLED = bool(STAGE3_TWO_PHASE_ENABLED)
    no_wli.STAGE3_PHASEA_CFG = dict(STAGE3_PHASEA_CFG)
    no_wli.STAGE3_PHASEB_CFG = dict(STAGE3_PHASEB_CFG)
    no_wli.STAGE3_PHASEB_TOP_N = int(STAGE3_PHASEB_TOP_N)
    no_wli.STAGE3_PHASEB_GATE_DELTA_FLOOR = float(STAGE3_PHASEB_GATE_DELTA_FLOOR)
    no_wli.STAGE3_PHASEB_GATE_END_GAIN_FLOOR = float(STAGE3_PHASEB_GATE_END_GAIN_FLOOR)

    no_wli.main()


if __name__ == "__main__":
    main()
