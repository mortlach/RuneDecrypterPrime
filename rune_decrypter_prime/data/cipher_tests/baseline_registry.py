# ============================================================
# tests/baseline_registry.py
# ============================================================
"""
Canonical baseline registry for Rune Decrypter Prime tests.

Purpose
-------
This module defines the *single source of truth* for:
  • RNG seed(s) used in reproducible test/benchmark runs.
  • Default key lengths (e.g., K=12 for Vigenère baselines).
  • Per-optimizer budget dictionaries (Beam, GA, SA, Hybrid).
  • Supported devices (numpy, torch, cuda).

Why this matters
----------------
- Ensures **determinism**: all tests/benchmarks start from the same RNG state.
- Ensures **comparability**: telemetry, trace, and unused-report outputs
  reflect identical ciphertexts and keys across runs.
- Prevents drift: scattered seeds/budgets in individual tests cause
  small differences that undermine benchmark reproducibility.

How to use
----------
Tests should **import from this registry** instead of hard-coding
seeds or budgets. Example:

    from rune_decrypter_prime.tests.baseline_registry import BASELINE

    rng = np.random.default_rng(BASELINE["seed"])
    K   = BASELINE["key_length"]
    budgets = BASELINE["budgets"]["beam"]

Developers can override these in *experimental tests*,
but baseline CI and benchmark traces should stick to these values.
"""
#
# from __future__ import annotations
#
# # Central seed for deterministic runs (frozen from 12/12 real Vigenère solves)
# SEED: int = 20250823
#
# # Canonical Vigenère key length (baseline problems)
# KEY_LENGTH: int = 12
#
# # Per-optimizer default configs (modest but robust budgets)
# BUDGETS: dict[str, dict] = {
#     "beam": dict(
#         beam_width=128,
#         stop_score=0.98,
#         verbose=False,
#     ),
#     "ga": dict(
#         pop_size=128,
#         generations=60,
#         elite_frac=0.05,
#         cx_frac=0.70,
#         mut_prob=0.30,
#         stop_score=0.98,
#         verbose=False,
#     ),
#     "sa": dict(
#         sa_init_temp=1.0,
#         sa_min_temp=1e-3,
#         sa_cooling=0.995,
#         sa_iters=80_000,
#         stop_score=0.98,
#         verbose=False,
#     ),
#     "hybrid": dict(
#         use_beam=True,
#         beam_width=96,
#         beam_stop_score=0.98,
#         pop_size=128,
#         generations=40,
#         elite_frac=0.05,
#         cx_frac=0.70,
#         mut_prob=0.30,
#         sa_init_temp=0.6,
#         sa_min_temp=1e-3,
#         sa_cooling=0.998,
#         sa_iters=4_000,
#         stop_score=0.98,
#         verbose=False,
#     ),
# }
#
# # Supported devices for parity tests
# DEVICES: list[str | None] = [None, "torch", "cuda"]
#
# # Export as a single dict for convenience
# BASELINE: dict[str, object] = {
#     "seed": SEED,
#     "key_length": KEY_LENGTH,
#     "budgets": BUDGETS,
#     "devices": DEVICES,
# }
# tests/baseline_registry.py
from __future__ import annotations

# Single source of truth for ALL tests: seed, devices, key length, budgets,
# and default config knobs for logging/scoring/optimizer.
BASELINE: dict = {
    # Deterministic seed (env TEST_SEED overrides)
    "seed": 12345,
    #
    # """
    #     Which logical devices to try; availability checked at runtime
    #       None -> 'cpu'
    #       'torch' -> 'torch_cpu' (if torch importable)
    #       'cuda'  -> 'cuda'      (if torch.cuda.is_available())
    #
    # CPU Means: run everything with plain NumPy on the host CPU.
    #     Pros: deterministic, always available, no external deps.
    #     Telemetry: scorer.impl = "numpy", scorer.device = "cpu".
    #     Mandatory baseline: Tier-A tests must always include CPU.
    #
    # Torch-CPU (device="torch") Means: use PyTorch as the backend, but on the CPU (not GPU).
    #                            Why: parity checks, and it exercises the Torch scorer code path without CUDA hardware.
    #                            Telemetry: scorer.impl = "torch", scorer.device = "cpu".
    #                            Useful for: catching bugs where the Torch and NumPy implementations diverge.
    #
    # CUDA (device="cuda" or "cuda:0") Means: run with PyTorch on an NVIDIA GPU, using CUDA kernels.
    #                                  Telemetry: scorer.impl = "torch", scorer.device = "cuda" (or cuda:0, cuda:1). This is “real GPU acceleration” path.
    # """
    
    # Canonical key length for vigenere tier-A tests
    "key_length": 7,
    "enable_telemetry": True,
    "budgets": {
          "beam": {"beam_width": 8, "verbose": False, "stop_score": 0.98},
          "ga": {"population": 64, "generations": 50},
    },
    "logging": {"write_jsonl": True, "verbose": True, "print_progress": True},
    "devices": ["cpu", "torch", "cuda"],
    # Default config knobs (mapped to dataclasses by helpers)
    "scoring": {
        "impl": "auto",
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": True,
        "n_char": 2,
        "n_wli": 2,
        "win": 10,
        "maximize": True,
        "model_root": None,
        "encoding_dir" : "fwd"
    },
    # hmmm todo
    "optimizer": {
        "name": "beam",
        "params": {
            # beam_width will be clamped/overridden by Tier-A fixture
        },
    },
    "cipher": {
        "device": "cpu",
        "name": "vigenere",
        "key_length": 7,
        "ciphertext": [],
        "wli_data": [],
        "text_transposition": "fwd",
        "key_transposition": "fwd",
    }
}
