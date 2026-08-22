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
    "autokey_ga": "DEVELOPMENT",
    "two_period_cribs": "SPECIALIST",
}

# The runner supports deterministic multiple attempts without requiring them.
# Keep one attempt for this consolidation pilot; future evidence may justify
# changing selected stochastic families here rather than special-casing seeds.
ATTEMPTS_PER_TRIAL = {family: 1 for family in FAMILY_GROUPS}

DEVELOPMENT_NOTES = {
    "autokey_ga": (
        "Autokey solver qualification remains separate work: define realistic "
        "known information and crib assumptions, review the practical search "
        "strategy, develop a representative solver, benchmark realistic seed "
        "lengths, then reconsider STANDARD campaign status."
    ),
}

SCORER = {
    "objective": "pct.logp.win10", "include_char": True,
    "use_word_breaks": True, "char_weights": {2: 0.3},
    "wli_weights": {2: 0.7},
}
ACCEPTANCE_RULES = {
    "vigenere_beam": {"plaintext_match": 1.0},
    "railfence_beam": {"plaintext_match": 1.0},
    "autokey_ga": {"plaintext_match": 1.0},
    "columnar_hybrid": {"plaintext_match": 1.0},
    "mono_ga": {"plaintext_match": 0.97},
    "vigenere_interruptors_beam": {
        "plaintext_match": 1.0,
        "require_interruptor_match": True,
    },
    "generic_map_multiply_beam": {"plaintext_match": 1.0},
    "scheduled_stream_beam": {"plaintext_match": 1.0},
    "two_period_cribs": {"plaintext_match": 1.0},
}
CIPHER_RANGES = {
    "vigenere_beam": {"key_length": (6, 14)},
    "railfence_beam": {"rails": (4, 10)},
    "autokey_ga": {"seed_length": (6, 12)},
    "columnar_hybrid": {"columns": (7, 9)},
    "mono_ga": {"alphabet_size": 29},
    "vigenere_interruptors_beam": {
        "key_length": (6, 10), "pool_size": (8, 10), "interruptor_count": (2, 3),
    },
    "generic_map_multiply_beam": {"key_length": (6, 14)},
    "scheduled_stream_beam": {"period": (6, 12)},
}
SOLVER_BUDGETS = {
    "vigenere_beam": {"beam_width": 96, "max_children_per_parent": 29, "plateau_rounds": 12},
    "railfence_beam": {"beam_width": 64, "plateau_rounds": 40},
    "autokey_ga": {"pop_size": 192, "generations": 200, "elite_frac": 0.08,
                    "cx_frac": 0.90, "mut_prob": 0.25, "tournament_k": 4,
                    "plateau_rounds": 30},
    "columnar_hybrid": {
        "use_beam": True, "beam_width": 96, "rounds": 6,
        "expand_mode": "sample", "sample_per_parent": 48,
        "top_parents_factor": 0.4,
        "ga": {"pop_size": 96, "generations": 40, "elite_frac": 0.10,
               "cx_frac": 0.85, "mut_prob": 0.30, "tournament_k": 3,
               "plateau_rounds": 12},
        "sa": {"iters": 3000, "T0": 0.95, "Tmin": 1e-4, "cool": 0.997,
               "plateau_rounds": 300},
        "plateau_rounds": 8,
    },
    "mono_ga": {"seed_keys": 160, "seed_swaps": 2, "pop_size": 128,
                "generations": 160, "elite_frac": 0.08, "cx_frac": 0.85,
                "mut_prob": 0.25, "tournament_k": 4, "plateau_rounds": 30},
    "vigenere_interruptors_beam": {"beam_width": 64, "expand_mode": "sweep",
                                    "plateau_rounds": 10},
    "generic_map_multiply_beam": {"beam_width": 64, "max_children_per_parent": 29,
                                   "plateau_rounds": 12},
    "scheduled_stream_beam": {"beam_width": 64, "max_children_per_parent": 29,
                               "plateau_rounds": 12},
}
OUTPUT_ROOT = (
    Path(__file__).resolve().parents[4]
    / "run_outputs" / "robustness" / "cipher_solver_campaign"
)
OUTPUT_PATH = OUTPUT_ROOT / "book_wli_consolidation_pilot.jsonl"
