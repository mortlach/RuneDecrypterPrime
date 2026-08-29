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
  • Per-solver budget dictionaries (Beam, GA, SA, Hybrid).
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

from __future__ import annotations
from rune_decrypter_prime.core.types import Device, ScorerImpl, Direction

# Single source of truth for ALL tests: seed, devices, key length, budgets,
# and default config knobs for logging/scoring/solver.
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
    "logging": {
        "run_kind": "tests",
        "label": "pytest",
        "write_jsonl": True,
        "verbose": True,
        "print_progress": True,
    },
    "devices": ["cpu", "torch", "cuda"],
    # Default config knobs (mapped to dataclasses by helpers)
    "scoring": {
        "impl": ScorerImpl.AUTO,
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": True,
        "n_char": 2,
        "n_wli": 2,
        "win": 10,
        "maximize": True,
        "model_root": None,
        "encoding_dir": Direction.LTR,
    },
    "solver": {
        "name": "beam",
        "params": {
            # beam_width will be clamped/overridden by Tier-A fixture
        },
    },
    "cipher": {
        "device": Device.CPU,
        "name": "vigenere",
        "key_length": 7,
        "ciphertext": [],
        "wli_data": [],
        "initial_text_permutation_indices": None,
    },
}
