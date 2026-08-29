"""Typed tuning authority for the cipher/solver robustness campaign."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol
from rdp import api

CAMPAIGN_SEED = 20260822
CAMPAIGN_MODE = "pilot"
BOOKS = ("13124.txt", "42770-0.txt", "46808.txt", "58447-0.txt", "736-0.txt")
DIRECTIONS = (api.TextDirection.LEFT_TO_RIGHT, api.TextDirection.RIGHT_TO_LEFT)
TARGET_RUNES = 300
RUNE_TOLERANCE = 30
PILOT_TRIALS_PER_ORDINARY_FAMILY = 4
FULL_TRIALS_PER_FAMILY = 20
TRIALS_PER_MODE = {"pilot": PILOT_TRIALS_PER_ORDINARY_FAMILY, "full": FULL_TRIALS_PER_FAMILY}
BLOCKING_REVIEW_GROUPS = {"pilot": (), "full": ("STANDARD", "SPECIALIST")}
FAMILY_GROUPS = {
    "vigenere_beam": "STANDARD", "railfence_beam": "STANDARD",
    "columnar_hybrid": "STANDARD", "mono_ga": "STANDARD",
    "vigenere_interruptors_beam": "STANDARD", "generic_map_multiply_beam": "STANDARD",
    "scheduled_stream_beam": "STANDARD", "autokey_beam": "STANDARD",
    "two_period_cribs": "SPECIALIST",
}
CASE_SEED_NAMESPACES = {"autokey_beam": "autokey_ga"}
CIPHER_RANGES = {
    "vigenere_beam": {"key_length": (6, 14)}, "railfence_beam": {"rails": (4, 10)},
    "autokey_beam": {"seed_length": (6, 12)}, "columnar_hybrid": {"columns": (7, 9)},
    "mono_ga": {"alphabet_size": 29},
    "vigenere_interruptors_beam": {"key_length": (6, 10), "pool_size": (8, 10), "interruptor_count": (2, 3)},
    "generic_map_multiply_beam": {"key_length": (6, 14)}, "scheduled_stream_beam": {"period": (6, 12)},
}

class SolverPlan(Protocol):
    def build(self, seed: int) -> api.SolverSpec: ...

@dataclass(frozen=True, slots=True)
class BeamPlan:
    width: int
    rounds: int = 0
    restarts: int = 1
    expansion: api.advanced.BeamExpansionMode = api.advanced.BeamExpansionMode.SWEEP
    maximum_children_per_parent: int | None = None
    plateau_rounds: int | None = None
    def build(self, seed: int) -> api.SolverSpec:
        return api.SolverSpec.beam_search(
            width=self.width, rounds=self.rounds, restarts=self.restarts, expansion=self.expansion,
            maximum_children_per_parent=self.maximum_children_per_parent,
            plateau_rounds=self.plateau_rounds, seed=seed,
        )

@dataclass(frozen=True, slots=True)
class GeneticPlan:
    population_size: int
    generations: int
    elite_fraction: float
    crossover_fraction: float
    mutation_probability: float
    tournament_size: int
    plateau_generations: int | None = None
    seed_keys: int = 0
    seed_swaps: int = 0
    def build(self, seed: int) -> api.SolverSpec:
        return api.SolverSpec.genetic_algorithm(
            population_size=self.population_size, generations=self.generations,
            elite_fraction=self.elite_fraction, crossover_fraction=self.crossover_fraction,
            mutation_probability=self.mutation_probability, tournament_size=self.tournament_size,
            plateau_generations=self.plateau_generations, seed=seed,
        )

@dataclass(frozen=True, slots=True)
class HybridPlan:
    genetic_algorithm: GeneticPlan
    simulated_annealing_iterations: int
    beam_width: int
    beam_rounds: int
    beam_expansion: api.advanced.BeamExpansionMode
    sample_per_parent: int
    top_parents_fraction: float
    plateau_rounds: int
    def build(self, seed: int) -> api.SolverSpec:
        ga = self.genetic_algorithm.build(seed)
        sa = api.SolverSpec.simulated_annealing(iterations=self.simulated_annealing_iterations, seed=seed)
        return api.SolverSpec.hybrid(
            genetic_algorithm=ga, simulated_annealing=sa, use_beam_search=True,
            beam_width=self.beam_width, beam_rounds=self.beam_rounds,
            beam_expansion=self.beam_expansion, sample_per_parent=self.sample_per_parent,
            top_parents_fraction=self.top_parents_fraction, plateau_rounds=self.plateau_rounds, seed=seed,
        )

@dataclass(frozen=True, slots=True)
class AcceptanceRule:
    plaintext_match: float
    require_interruptor_match: bool = False

@dataclass(frozen=True, slots=True)
class CampaignRecipe:
    recipe_id: str
    scoring: api.ScoringConfig
    solver: SolverPlan | None
    attempt_count: int
    selection: str
    acceptance: AcceptanceRule

DEFAULT_SCORING = api.ScoringConfig(
    character_lane_enabled=True, word_length_lane_enabled=True,
    character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7},
    objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10),
)
AUTOKEY_SCORING = api.ScoringConfig(
    character_lane_enabled=False, word_length_lane_enabled=True,
    character_order_weights={}, word_length_order_weights={1: 0.3, 2: 0.7},
    objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10),
)
MONO_SCORING = api.ScoringConfig(
    character_lane_enabled=True, word_length_lane_enabled=True,
    character_order_weights={2: 0.30}, word_length_order_weights={1: 0.21, 2: 0.49},
    objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10),
)

CAMPAIGN_RECIPES: dict[str, CampaignRecipe] = {
    "vigenere_beam": CampaignRecipe("vigenere_char2_wli2_beam_v1", DEFAULT_SCORING, BeamPlan(96, maximum_children_per_parent=29, plateau_rounds=12), 1, "highest_valid_solver_score", AcceptanceRule(1.0)),
    "railfence_beam": CampaignRecipe("railfence_corrected_char2_wli2_beam_v1", DEFAULT_SCORING, BeamPlan(64, plateau_rounds=40), 1, "highest_valid_solver_score", AcceptanceRule(1.0)),
    "autokey_beam": CampaignRecipe("autokey_wli12_beam_v1", AUTOKEY_SCORING, BeamPlan(96, rounds=32, restarts=3, plateau_rounds=0), 1, "highest_valid_solver_score", AcceptanceRule(1.0)),
    "columnar_hybrid": CampaignRecipe("columnar_char2_wli2_hybrid_v1", DEFAULT_SCORING, HybridPlan(GeneticPlan(96, 40, 0.10, 0.85, 0.30, 3, 12), 3000, 96, 6, api.advanced.BeamExpansionMode.SAMPLE, 48, 0.4, 8), 1, "highest_valid_solver_score", AcceptanceRule(1.0)),
    "mono_ga": CampaignRecipe("mono_char2_wli12_3start_v1", MONO_SCORING, GeneticPlan(128, 160, 0.08, 0.85, 0.25, 4, 30, 160, 2), 3, "highest_valid_solver_score", AcceptanceRule(0.97)),
    "vigenere_interruptors_beam": CampaignRecipe("vigenere_interruptors_char2_wli2_beam3_v1", DEFAULT_SCORING, BeamPlan(64, restarts=3, plateau_rounds=10), 1, "highest_valid_solver_score", AcceptanceRule(1.0, True)),
    "generic_map_multiply_beam": CampaignRecipe("generic_map_multiply_char2_wli2_beam_v1", DEFAULT_SCORING, BeamPlan(64, maximum_children_per_parent=29, plateau_rounds=12), 1, "highest_valid_solver_score", AcceptanceRule(1.0)),
    "scheduled_stream_beam": CampaignRecipe("scheduled_stream_char2_wli2_beam_v1", DEFAULT_SCORING, BeamPlan(64, maximum_children_per_parent=29, plateau_rounds=12), 1, "highest_valid_solver_score", AcceptanceRule(1.0)),
    "two_period_cribs": CampaignRecipe("two_period_cribs_specialist_v1", DEFAULT_SCORING, None, 1, "highest_valid_solver_score", AcceptanceRule(1.0)),
}

def scoring_to_dict(value: api.ScoringConfig) -> dict[str, object]:
    return {
        "objective": "pct.logp.win10", "include_char": value.character_lane_enabled,
        "use_word_breaks": value.word_length_lane_enabled,
        "char_weights": dict(value.character_order_weights or {}),
        "wli_weights": dict(value.word_length_order_weights or {}),
    }

def recipe_to_dict(value: CampaignRecipe) -> dict[str, object]:
    return {
        "recipe_id": value.recipe_id, "scorer": scoring_to_dict(value.scoring),
        "solver": None if value.solver is None else asdict(value.solver),
        "attempt_count": value.attempt_count, "selection": value.selection,
        "acceptance_rule": asdict(value.acceptance),
    }

OUTPUT_ROOT = Path(__file__).resolve().parents[4] / "run_outputs" / "robustness" / "cipher_solver_campaign"
