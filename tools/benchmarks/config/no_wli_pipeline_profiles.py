from __future__ import annotations

"""Typed no-WLI pipeline benchmark profiles.

These profiles are benchmark-facing (not solver-core) and are designed to be
imported by specific benchmark scripts. The goal is to keep tuning inputs
explicit, deterministic, and reusable across cipher-method benchmark runners.
"""

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class ScorerSpec:
    """Scoring model definition used by one stage of the pipeline."""

    objective: str
    char_weights: Mapping[int, float]
    include_char: bool = True
    use_word_breaks: bool = False
    avg_window_policy: Optional[str] = None

    def to_params(self) -> Dict[str, Any]:
        params = {
            "objective": str(self.objective),
            "include_char": bool(self.include_char),
            "use_word_breaks": bool(self.use_word_breaks),
            "char_weights": {int(k): float(v) for k, v in self.char_weights.items()},
            "wli_weights": {},
        }
        if self.avg_window_policy is not None:
            params["avg_window_policy"] = str(self.avg_window_policy)
        return params


@dataclass(frozen=True)
class NoWliScorerSchedule:
    """Three-stage scorer schedule for no-WLI runs.

    `A -> M -> B` means:
    - A: fast exploratory scorer (broad basin discovery)
    - M: medium discriminative scorer (candidate rerank/promote)
    - B: strongest scorer used for deep refine/confirmation
    """

    stage1_label: str
    stage2_label: str
    stage3_label: str
    stage1_a: ScorerSpec
    stage2_m: ScorerSpec
    stage3_b: ScorerSpec
    stage2_pass1_primary: Mapping[int, float]
    stage2_pass1_fallback: Mapping[int, float]


@dataclass(frozen=True)
class NoWliPipelineProfile:
    """Full benchmark profile for no-WLI staged periodic+columnar runs."""

    profile_id: str
    description: str
    scorer_schedule: NoWliScorerSchedule

    stage1_sub_candidates: int
    stage3_initial_keys: int
    stage1_sub_candidates_by_columns: Mapping[int, int]
    stage3_initial_keys_by_columns: Mapping[int, int]

    stage2_exact_max_columns: int
    stage2_exact_sub_candidates: int
    stage2_exact_sub_candidates_by_columns: Mapping[int, int]
    stage2_exact_two_pass: bool
    stage2_exact_pass1_top_tails: int
    stage2_exact_pass1_top_tails_by_columns: Mapping[int, int]
    stage2_exact_early_solve_break: bool
    stage2_hybrid_sub_candidates: int
    stage2_hybrid_sub_candidates_by_columns: Mapping[int, int]

    stage1_seed_restarts: int
    stage1_seed_n_blocks: int
    stage1_seed_total: int
    stage1_seed_swaps: int

    stage12_scout_runs: int
    stage12_archive_keep: int
    stage12_promote_top: int
    stage1_scout_step_scale: float
    stage1_scout_restart_scale: float
    stage1_scout_min_steps: int
    stage1_scout_min_restarts: int
    stage1_scout_no_improve_delta: float
    stage1_scout_no_improve_patience: int
    stage1_scout_min_new_archive: int

    stage3_dynamic_bands: tuple[Mapping[str, Any], ...]

    solver_stage1: Mapping[str, Any]
    solver_stage2: Mapping[str, Any]
    solver_stage3: Mapping[str, Any]


_NO_WLI_PROFILES: Dict[str, NoWliPipelineProfile] = {}


def _build_profiles() -> Dict[str, NoWliPipelineProfile]:
    profiles: Dict[str, NoWliPipelineProfile] = {}

    profiles["no_wli_a1_m12_b34_v1"] = NoWliPipelineProfile(
        profile_id="no_wli_a1_m12_b34_v1",
        description="No-WLI staged profile using A_char1 -> M_char12 -> B_char34.",
        scorer_schedule=NoWliScorerSchedule(
            stage1_label="A_char1",
            stage2_label="M_char12",
            stage3_label="B_char34",
            stage1_a=ScorerSpec(objective="pct.logp.win10", char_weights={1: 1.0}),
            stage2_m=ScorerSpec(objective="pct.logp.win10", char_weights={1: 0.4, 2: 0.6}),
            stage3_b=ScorerSpec(objective="pct.logp.win10", char_weights={3: 0.2, 4: 0.8}),
            stage2_pass1_primary={3: 0.2, 4: 0.8},
            stage2_pass1_fallback={2: 1.0},
        ),
        stage1_sub_candidates=24,
        stage3_initial_keys=18,
        stage1_sub_candidates_by_columns={1: 8, 3: 32, 5: 24, 7: 24, 10: 20, 13: 20},
        stage3_initial_keys_by_columns={1: 8, 3: 36, 5: 30, 7: 40, 10: 40, 13: 48},
        stage2_exact_max_columns=7,
        stage2_exact_sub_candidates=4,
        stage2_exact_sub_candidates_by_columns={3: 24, 5: 12, 7: 12},
        stage2_exact_two_pass=True,
        stage2_exact_pass1_top_tails=160,
        stage2_exact_pass1_top_tails_by_columns={3: 6, 5: 120, 7: 768},
        stage2_exact_early_solve_break=True,
        stage2_hybrid_sub_candidates=10,
        stage2_hybrid_sub_candidates_by_columns={10: 10, 13: 8},
        stage1_seed_restarts=96,
        stage1_seed_n_blocks=18,
        stage1_seed_total=256,
        stage1_seed_swaps=3,
        stage12_scout_runs=6,
        stage12_archive_keep=48,
        stage12_promote_top=24,
        stage1_scout_step_scale=0.28,
        stage1_scout_restart_scale=0.25,
        stage1_scout_min_steps=900,
        stage1_scout_min_restarts=1,
        stage1_scout_no_improve_delta=1e-6,
        stage1_scout_no_improve_patience=1,
        stage1_scout_min_new_archive=4,
        stage3_dynamic_bands=(
            {"name": "very_close", "max_gap": 0.010, "steps": 900, "restarts": 1, "plateau_rounds": 140, "col_batch": 96, "inner_batch": 128},
            {"name": "close", "max_gap": 0.030, "steps": 1600, "restarts": 1, "plateau_rounds": 200, "col_batch": 96, "inner_batch": 128},
            {"name": "mid", "max_gap": 0.080, "steps": 2400, "restarts": 2, "plateau_rounds": 260, "col_batch": 112, "inner_batch": 128},
            {"name": "far", "max_gap": 1e9, "steps": 3200, "restarts": 2, "plateau_rounds": 320, "col_batch": 112, "inner_batch": 128},
        ),
        solver_stage1={
            "steps": 2600,
            "restarts": 2,
            "inner_batch": 128,
            "slip_every": 0,
            "slip_blocks": 1,
            "slip_policy": "stall",
            "stall_rounds": 250,
            "stall_slip_limit": 3,
            "slip_swaps": 24,
            "stall_stop_on_limit": True,
            "block_schedule": "round_robin",
            "col_every": 0,
            "col_batch": 0,
            "use_raw_score": False,
            "raw_accept_min_delta": 1e-6,
            "pct_plateau_min_delta": 1e-4,
            "plateau_rounds": 420,
            "plateau_min_delta": 5e-4,
            "delta_window": 200,
            "top_k": 28,
            "progress_pct": 5,
            "print_progress": True,
            "seed": 2026,
            "seed_restarts": 96,
        },
        solver_stage2={
            "use_beam": True,
            "beam_width": 64,
            "rounds": 4,
            "expand_mode": "sample",
            "sample_per_parent": 40,
            "top_parents_factor": 0.4,
            "progress_pct": 10,
            "print_progress": True,
            "ga": {
                "pop_size": 96,
                "generations": 60,
                "elite_frac": 0.1,
                "cx_frac": 0.85,
                "mut_prob": 0.30,
                "tournament_k": 3,
                "plateau_rounds": 16,
                "stop_score": 1.0,
                "print_progress": True,
            },
            "sa": {
                "sa_iters": 2200,
                "sa_init_temp": 0.95,
                "sa_min_temp": 1e-4,
                "sa_cooling": 0.997,
                "plateau_rounds": 240,
                "local_improve_on_accept": True,
                "stop_score": 1.0,
                "print_progress": True,
            },
            "seed": 2026,
            "verbose": True,
            "log_interval": 10,
            "stop_score": 1.0,
        },
        solver_stage3={
            "steps": 3200,
            "restarts": 2,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 128,
            "slip_every": 80,
            "slip_blocks": 1,
            "slip_policy": "stall",
            "stall_rounds": 220,
            "stall_slip_limit": 4,
            "slip_swaps": 40,
            "use_raw_score": False,
            "raw_accept_min_delta": 1e-6,
            "pct_plateau_min_delta": 1e-4,
            "plateau_rounds": 320,
            "plateau_min_delta": 4e-4,
            "delta_window": 200,
            "top_k": 20,
            "progress_pct": 1,
            "print_progress": True,
            "seed": 2026,
        },
    )

    _base = profiles["no_wli_a1_m12_b34_v1"]
    profiles["no_wli_a1_m12_b34_stage3avg_fulltext_v1"] = NoWliPipelineProfile(
        profile_id="no_wli_a1_m12_b34_stage3avg_fulltext_v1",
        description=(
            "No-WLI staged profile using AVG full-text objective family "
            "across all stages with char-order progression."
        ),
        scorer_schedule=NoWliScorerSchedule(
            stage1_label="A_char1_avg_fulltext",
            stage2_label="M_char12_avg_fulltext",
            stage3_label="B_char4_avg_fulltext",
            stage1_a=ScorerSpec(
                objective="avg.logp.win20",
                char_weights={1: 1.0},
                avg_window_policy="full_text",
            ),
            stage2_m=ScorerSpec(
                objective="avg.logp.win20",
                char_weights={1: 0.4, 2: 0.6},
                avg_window_policy="full_text",
            ),
            stage3_b=ScorerSpec(
                objective="avg.logp.win20",
                char_weights={4: 1.0},
                avg_window_policy="full_text",
            ),
            stage2_pass1_primary={4: 1.0},
            stage2_pass1_fallback=_base.scorer_schedule.stage2_pass1_fallback,
        ),
        stage1_sub_candidates=_base.stage1_sub_candidates,
        stage3_initial_keys=64,
        stage1_sub_candidates_by_columns=dict(_base.stage1_sub_candidates_by_columns),
        stage3_initial_keys_by_columns={1: 16, 3: 64, 5: 64, 7: 80, 10: 96, 13: 96},
        stage2_exact_max_columns=_base.stage2_exact_max_columns,
        stage2_exact_sub_candidates=_base.stage2_exact_sub_candidates,
        stage2_exact_sub_candidates_by_columns=dict(_base.stage2_exact_sub_candidates_by_columns),
        stage2_exact_two_pass=_base.stage2_exact_two_pass,
        stage2_exact_pass1_top_tails=_base.stage2_exact_pass1_top_tails,
        stage2_exact_pass1_top_tails_by_columns=dict(_base.stage2_exact_pass1_top_tails_by_columns),
        stage2_exact_early_solve_break=_base.stage2_exact_early_solve_break,
        stage2_hybrid_sub_candidates=_base.stage2_hybrid_sub_candidates,
        stage2_hybrid_sub_candidates_by_columns=dict(_base.stage2_hybrid_sub_candidates_by_columns),
        stage1_seed_restarts=_base.stage1_seed_restarts,
        stage1_seed_n_blocks=_base.stage1_seed_n_blocks,
        stage1_seed_total=_base.stage1_seed_total,
        stage1_seed_swaps=_base.stage1_seed_swaps,
        stage12_scout_runs=_base.stage12_scout_runs,
        stage12_archive_keep=192,
        stage12_promote_top=96,
        stage1_scout_step_scale=_base.stage1_scout_step_scale,
        stage1_scout_restart_scale=_base.stage1_scout_restart_scale,
        stage1_scout_min_steps=_base.stage1_scout_min_steps,
        stage1_scout_min_restarts=_base.stage1_scout_min_restarts,
        stage1_scout_no_improve_delta=_base.stage1_scout_no_improve_delta,
        stage1_scout_no_improve_patience=_base.stage1_scout_no_improve_patience,
        stage1_scout_min_new_archive=_base.stage1_scout_min_new_archive,
        stage3_dynamic_bands=tuple(dict(b) for b in _base.stage3_dynamic_bands),
        solver_stage1=dict(_base.solver_stage1),
        solver_stage2=dict(_base.solver_stage2),
        solver_stage3={
            **dict(_base.solver_stage3),
            "use_raw_score": True,
            "raw_accept_min_delta": 1e-7,
            "pct_plateau_min_delta": 1e-4,
            "plateau_min_delta": 1e-4,
        },
    )
    _avg_fulltext = profiles["no_wli_a1_m12_b34_stage3avg_fulltext_v1"]
    profiles["no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1"] = NoWliPipelineProfile(
        profile_id="no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1",
        description=(
            "No-WLI AVG full-text long-run profile: A_char2 -> M_char4 -> B_char4, "
            "with ~3x Stage-1/3 iteration budget and relaxed scout early-stop guards."
        ),
        scorer_schedule=NoWliScorerSchedule(
            stage1_label="A_char2_avg_fulltext",
            stage2_label="M_char4_avg_fulltext",
            stage3_label="B_char4_avg_fulltext",
            stage1_a=ScorerSpec(
                objective="avg.logp.win20",
                char_weights={2: 1.0},
                avg_window_policy="full_text",
            ),
            stage2_m=ScorerSpec(
                objective="avg.logp.win20",
                char_weights={4: 1.0},
                avg_window_policy="full_text",
            ),
            stage3_b=ScorerSpec(
                objective="avg.logp.win20",
                char_weights={4: 1.0},
                avg_window_policy="full_text",
            ),
            stage2_pass1_primary={4: 1.0},
            stage2_pass1_fallback={4: 1.0},
        ),
        stage1_sub_candidates=_avg_fulltext.stage1_sub_candidates,
        stage3_initial_keys=int(_avg_fulltext.stage3_initial_keys) * 3,
        stage1_sub_candidates_by_columns=dict(_avg_fulltext.stage1_sub_candidates_by_columns),
        stage3_initial_keys_by_columns={
            int(k): int(v) * 3 for k, v in _avg_fulltext.stage3_initial_keys_by_columns.items()
        },
        stage2_exact_max_columns=_avg_fulltext.stage2_exact_max_columns,
        stage2_exact_sub_candidates=_avg_fulltext.stage2_exact_sub_candidates,
        stage2_exact_sub_candidates_by_columns=dict(_avg_fulltext.stage2_exact_sub_candidates_by_columns),
        stage2_exact_two_pass=_avg_fulltext.stage2_exact_two_pass,
        stage2_exact_pass1_top_tails=_avg_fulltext.stage2_exact_pass1_top_tails,
        stage2_exact_pass1_top_tails_by_columns=dict(_avg_fulltext.stage2_exact_pass1_top_tails_by_columns),
        stage2_exact_early_solve_break=_avg_fulltext.stage2_exact_early_solve_break,
        stage2_hybrid_sub_candidates=_avg_fulltext.stage2_hybrid_sub_candidates,
        stage2_hybrid_sub_candidates_by_columns=dict(_avg_fulltext.stage2_hybrid_sub_candidates_by_columns),
        stage1_seed_restarts=int(_avg_fulltext.stage1_seed_restarts) * 3,
        stage1_seed_n_blocks=_avg_fulltext.stage1_seed_n_blocks,
        stage1_seed_total=int(_avg_fulltext.stage1_seed_total) * 3,
        stage1_seed_swaps=_avg_fulltext.stage1_seed_swaps,
        stage12_scout_runs=_avg_fulltext.stage12_scout_runs,
        stage12_archive_keep=_avg_fulltext.stage12_archive_keep,
        stage12_promote_top=_avg_fulltext.stage12_promote_top,
        stage1_scout_step_scale=_avg_fulltext.stage1_scout_step_scale,
        stage1_scout_restart_scale=_avg_fulltext.stage1_scout_restart_scale,
        stage1_scout_min_steps=int(_avg_fulltext.stage1_scout_min_steps) * 3,
        stage1_scout_min_restarts=_avg_fulltext.stage1_scout_min_restarts,
        stage1_scout_no_improve_delta=_avg_fulltext.stage1_scout_no_improve_delta,
        stage1_scout_no_improve_patience=3,
        stage1_scout_min_new_archive=1,
        stage3_dynamic_bands=tuple(
            {
                **dict(b),
                "steps": int(dict(b).get("steps", 0)) * 3,
                "plateau_rounds": int(dict(b).get("plateau_rounds", 0)) * 3,
            }
            for b in _avg_fulltext.stage3_dynamic_bands
        ),
        solver_stage1={
            **dict(_avg_fulltext.solver_stage1),
            "steps": int(dict(_avg_fulltext.solver_stage1).get("steps", 0)) * 3,
            "plateau_rounds": int(dict(_avg_fulltext.solver_stage1).get("plateau_rounds", 0)) * 3,
            "seed_restarts": int(dict(_avg_fulltext.solver_stage1).get("seed_restarts", 0)) * 3,
        },
        solver_stage2=dict(_avg_fulltext.solver_stage2),
        solver_stage3={
            **dict(_avg_fulltext.solver_stage3),
            "steps": int(dict(_avg_fulltext.solver_stage3).get("steps", 0)) * 3,
            "plateau_rounds": int(dict(_avg_fulltext.solver_stage3).get("plateau_rounds", 0)) * 3,
        },
    )
    profiles["no_wli_a1_m34_b34_v1"] = NoWliPipelineProfile(
        profile_id="no_wli_a1_m34_b34_v1",
        description="No-WLI staged profile using A_char1 -> M_char34 -> B_char34.",
        scorer_schedule=NoWliScorerSchedule(
            stage1_label="A_char1",
            stage2_label="M_char34",
            stage3_label="B_char34",
            stage1_a=ScorerSpec(objective="pct.logp.win10", char_weights={1: 1.0}),
            stage2_m=ScorerSpec(objective="pct.logp.win10", char_weights={3: 0.2, 4: 0.8}),
            stage3_b=ScorerSpec(objective="pct.logp.win10", char_weights={3: 0.2, 4: 0.8}),
            stage2_pass1_primary={3: 0.2, 4: 0.8},
            stage2_pass1_fallback={2: 1.0},
        ),
        stage1_sub_candidates=24,
        stage3_initial_keys=18,
        stage1_sub_candidates_by_columns={1: 8, 3: 32, 5: 24, 7: 24, 10: 20, 13: 20},
        stage3_initial_keys_by_columns={1: 8, 3: 36, 5: 30, 7: 40, 10: 40, 13: 48},
        stage2_exact_max_columns=7,
        stage2_exact_sub_candidates=4,
        stage2_exact_sub_candidates_by_columns={3: 24, 5: 12, 7: 12},
        stage2_exact_two_pass=True,
        stage2_exact_pass1_top_tails=160,
        stage2_exact_pass1_top_tails_by_columns={3: 6, 5: 120, 7: 768},
        stage2_exact_early_solve_break=True,
        stage2_hybrid_sub_candidates=10,
        stage2_hybrid_sub_candidates_by_columns={10: 10, 13: 8},
        stage1_seed_restarts=96,
        stage1_seed_n_blocks=18,
        stage1_seed_total=256,
        stage1_seed_swaps=3,
        stage12_scout_runs=6,
        stage12_archive_keep=48,
        stage12_promote_top=24,
        stage1_scout_step_scale=0.28,
        stage1_scout_restart_scale=0.25,
        stage1_scout_min_steps=900,
        stage1_scout_min_restarts=1,
        stage1_scout_no_improve_delta=1e-6,
        stage1_scout_no_improve_patience=1,
        stage1_scout_min_new_archive=4,
        stage3_dynamic_bands=(
            {"name": "very_close", "max_gap": 0.010, "steps": 900, "restarts": 1, "plateau_rounds": 140, "col_batch": 96, "inner_batch": 128},
            {"name": "close", "max_gap": 0.030, "steps": 1600, "restarts": 1, "plateau_rounds": 200, "col_batch": 96, "inner_batch": 128},
            {"name": "mid", "max_gap": 0.080, "steps": 2400, "restarts": 2, "plateau_rounds": 260, "col_batch": 112, "inner_batch": 128},
            {"name": "far", "max_gap": 1e9, "steps": 3200, "restarts": 2, "plateau_rounds": 320, "col_batch": 112, "inner_batch": 128},
        ),
        solver_stage1={
            "steps": 2600,
            "restarts": 2,
            "inner_batch": 128,
            "slip_every": 0,
            "slip_blocks": 1,
            "slip_policy": "stall",
            "stall_rounds": 250,
            "stall_slip_limit": 3,
            "slip_swaps": 24,
            "stall_stop_on_limit": True,
            "block_schedule": "round_robin",
            "col_every": 0,
            "col_batch": 0,
            "use_raw_score": False,
            "raw_accept_min_delta": 1e-6,
            "pct_plateau_min_delta": 1e-4,
            "plateau_rounds": 420,
            "plateau_min_delta": 5e-4,
            "delta_window": 200,
            "top_k": 28,
            "progress_pct": 5,
            "print_progress": True,
            "seed": 2026,
            "seed_restarts": 96,
        },
        solver_stage2={
            "use_beam": True,
            "beam_width": 64,
            "rounds": 4,
            "expand_mode": "sample",
            "sample_per_parent": 40,
            "top_parents_factor": 0.4,
            "progress_pct": 10,
            "print_progress": True,
            "ga": {
                "pop_size": 96,
                "generations": 60,
                "elite_frac": 0.1,
                "cx_frac": 0.85,
                "mut_prob": 0.30,
                "tournament_k": 3,
                "plateau_rounds": 16,
                "stop_score": 1.0,
                "print_progress": True,
            },
            "sa": {
                "sa_iters": 2200,
                "sa_init_temp": 0.95,
                "sa_min_temp": 1e-4,
                "sa_cooling": 0.997,
                "plateau_rounds": 240,
                "local_improve_on_accept": True,
                "stop_score": 1.0,
                "print_progress": True,
            },
            "seed": 2026,
            "verbose": True,
            "log_interval": 10,
            "stop_score": 1.0,
        },
        solver_stage3={
            "steps": 3200,
            "restarts": 2,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 128,
            "slip_every": 80,
            "slip_blocks": 1,
            "slip_policy": "stall",
            "stall_rounds": 220,
            "stall_slip_limit": 4,
            "slip_swaps": 40,
            "use_raw_score": False,
            "raw_accept_min_delta": 1e-6,
            "pct_plateau_min_delta": 1e-4,
            "plateau_rounds": 320,
            "plateau_min_delta": 4e-4,
            "delta_window": 200,
            "top_k": 20,
            "progress_pct": 1,
            "print_progress": True,
            "seed": 2026,
        },
    )
    profiles["no_wli_a34_m34_b34_v1"] = NoWliPipelineProfile(
        profile_id="no_wli_a34_m34_b34_v1",
        description="No-WLI staged profile using A_char34 -> M_char34 -> B_char34.",
        scorer_schedule=NoWliScorerSchedule(
            stage1_label="A_char34",
            stage2_label="M_char34",
            stage3_label="B_char34",
            stage1_a=ScorerSpec(objective="pct.logp.win10", char_weights={3: 0.2, 4: 0.8}),
            stage2_m=ScorerSpec(objective="pct.logp.win10", char_weights={3: 0.2, 4: 0.8}),
            stage3_b=ScorerSpec(objective="pct.logp.win10", char_weights={3: 0.2, 4: 0.8}),
            stage2_pass1_primary={3: 0.2, 4: 0.8},
            stage2_pass1_fallback={2: 1.0},
        ),
        stage1_sub_candidates=24,
        stage3_initial_keys=18,
        stage1_sub_candidates_by_columns={1: 8, 3: 32, 5: 24, 7: 24, 10: 20, 13: 20},
        stage3_initial_keys_by_columns={1: 8, 3: 36, 5: 30, 7: 40, 10: 40, 13: 48},
        stage2_exact_max_columns=7,
        stage2_exact_sub_candidates=4,
        stage2_exact_sub_candidates_by_columns={3: 24, 5: 12, 7: 12},
        stage2_exact_two_pass=True,
        stage2_exact_pass1_top_tails=160,
        stage2_exact_pass1_top_tails_by_columns={3: 6, 5: 120, 7: 768},
        stage2_exact_early_solve_break=True,
        stage2_hybrid_sub_candidates=10,
        stage2_hybrid_sub_candidates_by_columns={10: 10, 13: 8},
        stage1_seed_restarts=96,
        stage1_seed_n_blocks=18,
        stage1_seed_total=256,
        stage1_seed_swaps=3,
        stage12_scout_runs=6,
        stage12_archive_keep=48,
        stage12_promote_top=24,
        stage1_scout_step_scale=0.28,
        stage1_scout_restart_scale=0.25,
        stage1_scout_min_steps=900,
        stage1_scout_min_restarts=1,
        stage1_scout_no_improve_delta=1e-6,
        stage1_scout_no_improve_patience=1,
        stage1_scout_min_new_archive=4,
        stage3_dynamic_bands=(
            {"name": "very_close", "max_gap": 0.010, "steps": 900, "restarts": 1, "plateau_rounds": 140, "col_batch": 96, "inner_batch": 128},
            {"name": "close", "max_gap": 0.030, "steps": 1600, "restarts": 1, "plateau_rounds": 200, "col_batch": 96, "inner_batch": 128},
            {"name": "mid", "max_gap": 0.080, "steps": 2400, "restarts": 2, "plateau_rounds": 260, "col_batch": 112, "inner_batch": 128},
            {"name": "far", "max_gap": 1e9, "steps": 3200, "restarts": 2, "plateau_rounds": 320, "col_batch": 112, "inner_batch": 128},
        ),
        solver_stage1={
            "steps": 2600,
            "restarts": 2,
            "inner_batch": 128,
            "slip_every": 0,
            "slip_blocks": 1,
            "slip_policy": "stall",
            "stall_rounds": 250,
            "stall_slip_limit": 3,
            "slip_swaps": 24,
            "stall_stop_on_limit": True,
            "block_schedule": "round_robin",
            "col_every": 0,
            "col_batch": 0,
            "use_raw_score": False,
            "raw_accept_min_delta": 1e-6,
            "pct_plateau_min_delta": 1e-4,
            "plateau_rounds": 420,
            "plateau_min_delta": 5e-4,
            "delta_window": 200,
            "top_k": 28,
            "progress_pct": 5,
            "print_progress": True,
            "seed": 2026,
            "seed_restarts": 96,
        },
        solver_stage2={
            "use_beam": True,
            "beam_width": 64,
            "rounds": 4,
            "expand_mode": "sample",
            "sample_per_parent": 40,
            "top_parents_factor": 0.4,
            "progress_pct": 10,
            "print_progress": True,
            "ga": {
                "pop_size": 96,
                "generations": 60,
                "elite_frac": 0.1,
                "cx_frac": 0.85,
                "mut_prob": 0.30,
                "tournament_k": 3,
                "plateau_rounds": 16,
                "stop_score": 1.0,
                "print_progress": True,
            },
            "sa": {
                "sa_iters": 2200,
                "sa_init_temp": 0.95,
                "sa_min_temp": 1e-4,
                "sa_cooling": 0.997,
                "plateau_rounds": 240,
                "local_improve_on_accept": True,
                "stop_score": 1.0,
                "print_progress": True,
            },
            "seed": 2026,
            "verbose": True,
            "log_interval": 10,
            "stop_score": 1.0,
        },
        solver_stage3={
            "steps": 3200,
            "restarts": 2,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 128,
            "slip_every": 80,
            "slip_blocks": 1,
            "slip_policy": "stall",
            "stall_rounds": 220,
            "stall_slip_limit": 4,
            "slip_swaps": 40,
            "use_raw_score": False,
            "raw_accept_min_delta": 1e-6,
            "pct_plateau_min_delta": 1e-4,
            "plateau_rounds": 320,
            "plateau_min_delta": 4e-4,
            "delta_window": 200,
            "top_k": 20,
            "progress_pct": 1,
            "print_progress": True,
            "seed": 2026,
        },
    )
    return profiles


def get_no_wli_pipeline_profile(profile_id: str) -> NoWliPipelineProfile:
    """Return a named no-WLI profile, raising on unknown ids."""
    if not _NO_WLI_PROFILES:
        _NO_WLI_PROFILES.update(_build_profiles())
    pid = str(profile_id).strip()
    profile = _NO_WLI_PROFILES.get(pid)
    if profile is None:
        known = ", ".join(sorted(_NO_WLI_PROFILES.keys()))
        raise ValueError(f"Unknown no-WLI profile_id={profile_id!r}. Known: {known}")
    return profile
