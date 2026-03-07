from __future__ import annotations


SCAN_MODES = frozenset({"scan_fast_v1", "adaptive_scan_v1"})
ADAPTIVE_FOCUS_MODES = frozenset(
    {"adaptive_focus_v1", "adaptive_focus_v1_p7c3_only", "adaptive_fixture_v1"}
)

SMOKE_TIERS: tuple[tuple[str, int, int, int], ...] = (
    ("smoke_p7_c5_l452", 7, 5, 452),
    ("smoke_p9_c7_l446", 9, 7, 446),
)

FOCUS_P5_C1_ONLY_TIERS: tuple[tuple[str, int, int, int], ...] = (
    ("focus_p5_c1_l1000", 5, 1, 1000),
)

SCAN_P5_P7_C1357_TIERS: tuple[tuple[str, int, int, int], ...] = (
    ("scan_p5_c1_l1000", 5, 1, 1000),
    ("scan_p5_c3_l1000", 5, 3, 1000),
    ("scan_p5_c5_l1000", 5, 5, 1000),
    ("scan_p5_c7_l1000", 5, 7, 1000),
    ("scan_p7_c1_l1000", 7, 1, 1000),
    ("scan_p7_c3_l1000", 7, 3, 1000),
    ("scan_p7_c5_l1000", 7, 5, 1000),
    ("scan_p7_c7_l1000", 7, 7, 1000),
)

ADAPTIVE_FOCUS_V1_TIERS: tuple[tuple[str, int, int, int], ...] = (
    ("focus_p7_c3_l1000", 7, 3, 1000),
    ("focus_p7_c7_l1000", 7, 7, 1000),
)

ADAPTIVE_FOCUS_P7C3_ONLY_TIERS: tuple[tuple[str, int, int, int], ...] = (
    ("focus_p7_c3_l1000", 7, 3, 1000),
)

FOCUS_500_NOWLI_TIERS: tuple[tuple[str, int, int, int], ...] = (
    ("focus_p5_c1_l452", 5, 1, 452),
    ("focus_p5_c3_l452", 5, 3, 452),
    ("focus_p5_c5_l452", 5, 5, 452),
    ("focus_p7_c5_l452", 7, 5, 452),
    ("focus_p7_c7_l452", 7, 7, 452),
    ("focus_p8_c5_l505", 8, 5, 505),
    ("focus_p9_c7_l446", 9, 7, 446),
    ("focus_p14_c7_l452", 14, 7, 452),
    ("focus_p15_c7_l415", 15, 7, 415),
    ("focus_p18_c7_l446", 18, 7, 446),
    ("focus_p21_c7_l483", 21, 7, 483),
)

SCAN_FAST_V1_STAGE2_EXACT_SUB_BY_COLUMNS: dict[int, int] = {
    3: 20,
    5: 20,
    7: 16,
}

SCAN_FAST_V1_STAGE2_EXACT_PASS1_TOP_BY_COLUMNS: dict[int, int] = {
    3: 6,
    5: 180,
    7: 1024,
}

SCAN_FAST_V1_STAGE3_INITIAL_KEYS_BY_COLUMNS: dict[int, int] = {
    1: 40,
    3: 64,
    5: 96,
    7: 128,
    10: 96,
    13: 96,
}

SCAN_FAST_V1_STAGE3_DYNAMIC_BANDS: tuple[dict[str, float | int | str], ...] = (
    {"name": "very_close", "max_gap": 0.010, "steps": 400, "restarts": 1, "plateau_rounds": 80, "col_batch": 96, "inner_batch": 128},
    {"name": "close", "max_gap": 0.030, "steps": 700, "restarts": 1, "plateau_rounds": 120, "col_batch": 96, "inner_batch": 128},
    {"name": "mid", "max_gap": 0.080, "steps": 1100, "restarts": 1, "plateau_rounds": 180, "col_batch": 96, "inner_batch": 128},
    {"name": "far", "max_gap": 1e9, "steps": 1800, "restarts": 1, "plateau_rounds": 240, "col_batch": 96, "inner_batch": 128},
)

SCAN_FAST_V1_STAGE3_PERIOD_INIT_MULT: dict[int, float] = {7: 1.35}
SCAN_FAST_V1_STAGE3_PERIOD_STEP_MULT: dict[int, float] = {7: 1.55}
SCAN_FAST_V1_STAGE3_PERIOD_RESTART_BONUS: dict[int, int] = {7: 1}

ADAPTIVE_SCAN_V1_STAGE2_EXACT_SUB_BY_COLUMNS: dict[int, int] = {
    3: 24,
    5: 24,
    7: 24,
}

ADAPTIVE_SCAN_V1_STAGE2_EXACT_PASS1_TOP_BY_COLUMNS: dict[int, int] = {
    3: 6,
    5: 240,
    7: 1536,
}

ADAPTIVE_SCAN_V1_STAGE3_INITIAL_KEYS_BY_COLUMNS: dict[int, int] = {
    1: 48,
    3: 72,
    5: 128,
    7: 160,
    10: 128,
    13: 128,
}

ADAPTIVE_SCAN_V1_STAGE3_DYNAMIC_BANDS: tuple[dict[str, float | int | str], ...] = (
    {"name": "very_close", "max_gap": 0.010, "steps": 500, "restarts": 1, "plateau_rounds": 100, "col_batch": 96, "inner_batch": 128},
    {"name": "close", "max_gap": 0.030, "steps": 900, "restarts": 1, "plateau_rounds": 150, "col_batch": 96, "inner_batch": 128},
    {"name": "mid", "max_gap": 0.080, "steps": 1500, "restarts": 1, "plateau_rounds": 220, "col_batch": 112, "inner_batch": 128},
    {"name": "far", "max_gap": 1e9, "steps": 2400, "restarts": 2, "plateau_rounds": 320, "col_batch": 112, "inner_batch": 128},
)

ADAPTIVE_SCAN_V1_STAGE3_PERIOD_INIT_MULT: dict[int, float] = {7: 1.55}
ADAPTIVE_SCAN_V1_STAGE3_PERIOD_STEP_MULT: dict[int, float] = {7: 1.85}
ADAPTIVE_SCAN_V1_STAGE3_PERIOD_RESTART_BONUS: dict[int, int] = {7: 2}
