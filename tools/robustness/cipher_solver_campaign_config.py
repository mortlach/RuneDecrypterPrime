"""Single tuning surface for the cipher/solver robustness campaign."""

from pathlib import Path

CAMPAIGN_SEED = 20260822
CAMPAIGN_MODE = "pilot"  # "pilot" or "full"
BOOKS = ("13124.txt", "42770-0.txt", "46808.txt", "58447-0.txt", "736-0.txt")
DIRECTIONS = ("ltr", "rtl")
TARGET_RUNES = 300
RUNE_TOLERANCE = 30
PILOT_TRIALS_PER_ORDINARY_FAMILY = 4
FULL_TRIALS_PER_FAMILY = 20  # Not run until separately authorised.
TRIALS_PER_MODE = {
    "pilot": PILOT_TRIALS_PER_ORDINARY_FAMILY,
    "full": FULL_TRIALS_PER_FAMILY,
}

# REVIEW is informative during pilots. During full qualification, REVIEW in a
# STANDARD or SPECIALIST family blocks success; DEVELOPMENT remains evidence.
BLOCKING_REVIEW_GROUPS = {
    "pilot": (),
    "full": ("STANDARD", "SPECIALIST"),
}

FAMILY_GROUPS = {
    "vigenere_beam": "STANDARD",
    "railfence_beam": "STANDARD",
    "columnar_hybrid": "STANDARD",
    "mono_ga": "STANDARD",
    "vigenere_interruptors_beam": "STANDARD",
    "generic_map_multiply_beam": "STANDARD",
    "scheduled_stream_beam": "STANDARD",
    "autokey_beam": "STANDARD",
    "two_period_cribs": "SPECIALIST",
}

# Keep the original problem stream when a family label changes because its
# solver changes. This makes before/after solver evidence directly comparable.
CASE_SEED_NAMESPACES = {
    "autokey_beam": "autokey_ga",
}

DEFAULT_SCORER = {
    "objective": "pct.logp.win10", "include_char": True,
    "use_word_breaks": True, "char_weights": {2: 0.3},
    "wli_weights": {2: 0.7},
}
AUTOKEY_SCORER = {
    "objective": "pct.logp.win10", "include_char": False,
    "use_word_breaks": True, "char_weights": {},
    "wli_weights": {1: 0.3, 2: 0.7},
}
MONO_CANDIDATE_SCORER = {
    "objective": "pct.logp.win10", "include_char": True,
    "use_word_breaks": True, "char_weights": {2: 0.30},
    "wli_weights": {1: 0.21, 2: 0.49},
}

CIPHER_RANGES = {
    "vigenere_beam": {"key_length": (6, 14)},
    "railfence_beam": {"rails": (4, 10)},
    "autokey_beam": {"seed_length": (6, 12)},
    "columnar_hybrid": {"columns": (7, 9)},
    "mono_ga": {"alphabet_size": 29},
    "vigenere_interruptors_beam": {
        "key_length": (6, 10), "pool_size": (8, 10), "interruptor_count": (2, 3),
    },
    "generic_map_multiply_beam": {"key_length": (6, 14)},
    "scheduled_stream_beam": {"period": (6, 12)},
}

# Permanent campaign recipe authority. Scoring, solver work, independent
# attempts, attempt selection and truth acceptance live together so a run
# cannot accidentally combine parts from different experiments.
CAMPAIGN_RECIPES = {
    "vigenere_beam": {
        "recipe_id": "vigenere_char2_wli2_beam_v1",
        "scorer": DEFAULT_SCORER,
        "solver_budget": {
            "beam_width": 96, "max_children_per_parent": 29,
            "plateau_rounds": 12,
        },
        "attempt_count": 1,
        "selection": "highest_valid_solver_score",
        "acceptance_rule": {"plaintext_match": 1.0},
    },
    "railfence_beam": {
        "recipe_id": "railfence_corrected_char2_wli2_beam_v1",
        "scorer": DEFAULT_SCORER,
        "solver_budget": {"beam_width": 64, "plateau_rounds": 40},
        "attempt_count": 1,
        "selection": "highest_valid_solver_score",
        "acceptance_rule": {"plaintext_match": 1.0},
    },
    "columnar_hybrid": {
        "recipe_id": "columnar_char2_wli2_hybrid_v1",
        "scorer": DEFAULT_SCORER,
        "solver_budget": {
            "use_beam": True, "beam_width": 96, "rounds": 6,
            "expand_mode": "sample", "sample_per_parent": 48,
            "top_parents_factor": 0.4,
            "ga": {
                "pop_size": 96, "generations": 40, "elite_frac": 0.10,
                "cx_frac": 0.85, "mut_prob": 0.30, "tournament_k": 3,
                "plateau_rounds": 12,
            },
            "sa": {
                "iters": 3000, "T0": 0.95, "Tmin": 1e-4,
                "cool": 0.997, "plateau_rounds": 300,
            },
            "plateau_rounds": 8,
        },
        "attempt_count": 1,
        "selection": "highest_valid_solver_score",
        "acceptance_rule": {"plaintext_match": 1.0},
    },
    "mono_ga": {
        "recipe_id": "mono_char2_wli12_3start_v1",
        "scorer": MONO_CANDIDATE_SCORER,
        "solver_budget": {
            "seed_keys": 160, "seed_swaps": 2, "pop_size": 128,
            "generations": 160, "elite_frac": 0.08, "cx_frac": 0.85,
            "mut_prob": 0.25, "tournament_k": 4, "plateau_rounds": 30,
        },
        "attempt_count": 3,
        "selection": "highest_valid_solver_score",
        "acceptance_rule": {"plaintext_match": 0.97},
    },
    "vigenere_interruptors_beam": {
        "recipe_id": "vigenere_interruptors_char2_wli2_beam3_v1",
        "scorer": DEFAULT_SCORER,
        "solver_budget": {
            "beam_width": 64, "restarts": 3,
            "expand_mode": "sweep", "plateau_rounds": 10,
        },
        "attempt_count": 1,
        "selection": "highest_valid_solver_score",
        "acceptance_rule": {
            "plaintext_match": 1.0, "require_interruptor_match": True,
        },
    },
    "generic_map_multiply_beam": {
        "recipe_id": "generic_map_multiply_char2_wli2_beam_v1",
        "scorer": DEFAULT_SCORER,
        "solver_budget": {
            "beam_width": 64, "max_children_per_parent": 29,
            "plateau_rounds": 12,
        },
        "attempt_count": 1,
        "selection": "highest_valid_solver_score",
        "acceptance_rule": {"plaintext_match": 1.0},
    },
    "scheduled_stream_beam": {
        "recipe_id": "scheduled_stream_char2_wli2_beam_v1",
        "scorer": DEFAULT_SCORER,
        "solver_budget": {
            "beam_width": 64, "max_children_per_parent": 29,
            "plateau_rounds": 12,
        },
        "attempt_count": 1,
        "selection": "highest_valid_solver_score",
        "acceptance_rule": {"plaintext_match": 1.0},
    },
    "autokey_beam": {
        "recipe_id": "autokey_wli12_beam_v1",
        "scorer": AUTOKEY_SCORER,
        "solver_budget": {
            "beam_width": 96, "rounds": 32, "restarts": 3,
            "expand_mode": "sweep", "plateau_rounds": 0,
        },
        "attempt_count": 1,
        "selection": "highest_valid_solver_score",
        "acceptance_rule": {"plaintext_match": 1.0},
    },
    "two_period_cribs": {
        "recipe_id": "two_period_cribs_specialist_v1",
        "scorer": DEFAULT_SCORER,
        "solver_budget": {},
        "attempt_count": 1,
        "selection": "highest_valid_solver_score",
        "acceptance_rule": {"plaintext_match": 1.0},
    },
}

OUTPUT_ROOT = (
    Path(__file__).resolve().parents[4]
    / "run_outputs" / "robustness" / "cipher_solver_campaign"
)
