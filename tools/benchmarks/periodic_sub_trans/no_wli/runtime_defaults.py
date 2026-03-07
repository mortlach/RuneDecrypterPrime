from __future__ import annotations

from typing import Any, Dict, List, Tuple


DEFAULT_STAGE3_DYNAMIC_BANDS: List[Dict[str, Any]] = [
    dict(
        name="very_close",
        max_gap=0.010,
        steps=900,
        restarts=1,
        plateau_rounds=140,
        col_batch=96,
        inner_batch=128,
    ),
    dict(
        name="close",
        max_gap=0.030,
        steps=1600,
        restarts=1,
        plateau_rounds=200,
        col_batch=96,
        inner_batch=128,
    ),
    dict(
        name="mid",
        max_gap=0.080,
        steps=2400,
        restarts=2,
        plateau_rounds=260,
        col_batch=112,
        inner_batch=128,
    ),
    dict(
        name="far",
        max_gap=1e9,
        steps=3200,
        restarts=2,
        plateau_rounds=320,
        col_batch=112,
        inner_batch=128,
    ),
]

DEFAULT_STAGE3_PHASEA_CFG: Dict[str, Any] = {
    "steps": 350,
    "restarts": 1,
    "inner_batch": 64,
    "col_every": 1,
    "col_batch": 64,
    "slip_every": 0,
    "slip_swaps": 0,
    "stall_slip_limit": 0,
}

DEFAULT_STAGE3_PHASEB_CFG: Dict[str, Any] = {
    "steps": 1400,
    "inner_batch": 128,
    "col_every": 1,
    "col_batch": 96,
    "slip_every": 70,
    "stall_rounds": 160,
    "stall_slip_limit": 8,
    "slip_swaps": 28,
}

DEFAULT_SCORER_STAGE1: Dict[str, Any] = dict(
    objective="pct.logp.win10",
    include_char=True,
    use_word_breaks=False,
    char_weights={1: 1.0},
    wli_weights={},
    impl="torch",
)

DEFAULT_SCORER_STAGE2: Dict[str, Any] = dict(
    objective="pct.logp.win10",
    include_char=True,
    use_word_breaks=False,
    char_weights={1: 0.4, 2: 0.6},
    wli_weights={},
    impl="torch",
)

DEFAULT_SCORER_FULL: Dict[str, Any] = dict(
    objective="pct.logp.win10",
    include_char=True,
    use_word_breaks=False,
    char_weights={3: 0.2, 4: 0.8},
    wli_weights={},
    impl="torch",
)

DEFAULT_SOLVER_STAGE1: Dict[str, Any] = dict(
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

DEFAULT_SOLVER_STAGE2: Dict[str, Any] = dict(
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

DEFAULT_SOLVER_STAGE3: Dict[str, Any] = dict(
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

DEFAULT_TIERS: List[Tuple[str, int, int, int]] = [
    ("focus_p7_c7_l452", 7, 7, 452),
]
