# ============================================================
# rune_decrypter_prime/core/solver_engine.py
# Config-first orchestrator: builds cipher, scorer, optimizer
# from config; aggregates telemetry and lightweight run logs.
# ============================================================
"""
Config-first solver engine: wiring ciphers, scorers, and optimizers.

Overview
--------
The solver engine is a thin, configuration-driven orchestrator. It builds
three components from config only:

  • Cipher (pipeline owner of interruptors/transpositions)
  • Scorer (backend selected by `s_cfg.impl`, device by `c_cfg.device`)
  • Optimizer (search strategy; receives the full OptimizerConfig)

Responsibilities:
  - Resolve component classes from registries.
  - Enforce clear CPU/CUDA rules for scorers (no silent downgrades).
  - Normalise telemetry and attach it to the final Solution.
  - Keep all behaviour in config (no ad-hoc argument threading).

Design notes
------------
The engine does not implement cipher maths, scoring, or optimisation; it
simply builds and connects them. The cipher pipeline is treated as the
single source of truth for interruptors and transpositions. Optimisers may
optionally receive structure-search knobs via opt-in hooks.
"""

from __future__ import annotations
from typing import Any, Dict, Type
from collections.abc import Mapping
import numpy as np

from rune_decrypter_prime.core.config import Solution, RunConfig
from rune_decrypter_prime.core.problem import DecryptionProblem
from rune_decrypter_prime.io.run_logger import RunLogger
from rune_decrypter_prime.core.logging_config import LoggingConfig
from rune_decrypter_prime.ciphers import registry as cipher_registry
from rune_decrypter_prime.core.config import OptimizerConfig

# ---------- Legacy static registry (kept for back-compat) ----------
# TODO: In a future tidy, prefer `cipher_registry` (single source of truth).
from rune_decrypter_prime.ciphers.vigenere_cipher import RuneVigenereCipher
from rune_decrypter_prime.ciphers.substitution_cipher import SubstitutionCipher
from rune_decrypter_prime.ciphers.columnar_transposition_cipher import ColumnarTranspositionCipher
from rune_decrypter_prime.ciphers.hill_cipher import HillCipherMod29
from rune_decrypter_prime.ciphers.affine_cipher import AffineCipherMod29
from rune_decrypter_prime.ciphers.railfence_cipher2 import RailFenceCipher
from rune_decrypter_prime.ciphers.beaufort_cipher import VariantBeaufortCipher, BeaufortCipher
from rune_decrypter_prime.ciphers.block_permutation_cipher import BlockPermutationCipher
from rune_decrypter_prime.ciphers.route_cipher2 import RouteCipher
#from rune_decrypter_prime.ciphers.legacy.mono import MonoCipher
from rune_decrypter_prime.io.telemetry_utils import dump_telemetry
from rune_decrypter_prime.scoring.unified_rune_scorer import UnifiedRuneScorer

CIPHERS: Dict[str, Type] = {
    "vigenere": RuneVigenereCipher,
    "substitution": SubstitutionCipher,
    "columnar": ColumnarTranspositionCipher,
    "hill": HillCipherMod29,
    "affine": AffineCipherMod29,
    "railfence": RailFenceCipher,
    "beaufort": BeaufortCipher,
    "variant_beaufort": VariantBeaufortCipher,
    "blockperm": BlockPermutationCipher,
    "route": RouteCipher,
}

SCORERS: Dict[str, Type] = {
    "rune": UnifiedRuneScorer,
}

from rune_decrypter_prime.optimizers.beam_optimizer import BeamSearchOptimizer
from rune_decrypter_prime.optimizers.ga_optimizer import GAOptimizer
from rune_decrypter_prime.optimizers.sa_optimizer import SAOptimizer
from rune_decrypter_prime.optimizers.hybrid_optimizer import HybridOptimizer
OPTIMIZERS: Dict[str, Type] = {
    "beam": BeamSearchOptimizer,
    "ga": GAOptimizer,
    "sa": SAOptimizer,
    "hybrid": HybridOptimizer,
}

# ---------- Builders (pure config in, objects out) ----------
def build_cipher(cfg_cipher) -> Any:
    """Construct a cipher instance from a cipher config.

    Contract
    --------
    - Pure config in, object out (no defaults hidden in the engine).
    - If a registered cipher exists under `cfg_cipher.name`, it is preferred.
    - Falls back to the legacy `CIPHERS` mapping for back-compat.

    Parameters
    ----------
    cfg_cipher : object
        Dataclass/namespace with at least `.name`. The cipher’s pipeline
        reads interruptor/transposition settings from this object.

    Returns
    -------
    Any
        A cipher instance whose `__init__` accepts the full cipher config.

    Notes
    -----
    The returned cipher is annotated with `.cfg = cfg_cipher` if not already
    present to preserve downstream expectations.
    """
    name = getattr(cfg_cipher, "name", "vigenere").lower()
    if cipher_registry.has(name):  # currently empty; legacy mapping remains primary
        CipherCtor = cipher_registry.get(name)
        cipher = CipherCtor(cfg_cipher)
        if not hasattr(cipher, "cfg"):
            setattr(cipher, "cfg", cfg_cipher)
        return cipher

    CipherCls = CIPHERS[name]
    cipher = CipherCls(cfg_cipher)
    if not hasattr(cipher, "cfg"):  # soft back-compat
        setattr(cipher, "cfg", cfg_cipher)
    return cipher


def build_scorer(c_cfg, s_cfg):
    """Select and construct a scorer backend.

    Semantics
    ---------
    - Backend family from `s_cfg.impl`:
        "numpy"   → RuneScorer (CPU only)
        "torch"   → RuneScorerTorch (CPU/CUDA chosen internally from `c_cfg.device`)
        "unified" → UnifiedRuneScorer
        "auto"    → "torch" iff device is CUDA, else "numpy"
    - Hardware target from `c_cfg.device`:
        "cpu" or "cuda[:idx]". The string "torch" is rejected (backend, not device).
    - Explicit CUDA requests are validated—no silent fallback to CPU.
    """
    impl_raw = getattr(s_cfg, "impl", None)
    impl = (impl_raw or "auto").strip().lower()

    device_raw = getattr(c_cfg, "device", "cpu")
    device_req = str(device_raw or "cpu").strip().lower()

    # Guard: historical confusion; fail loudly.
    if device_req == "torch":
        raise ValueError(
            'Invalid device value "torch". '
            'Use device="cpu" or "cuda[:idx]" and choose backend with s_cfg.impl ("numpy"|"torch"|"unified"|"auto").'
        )

    # If CUDA explicitly requested, ensure it is actually available.
    if device_req.startswith("cuda"):
        from rune_decrypter_prime.backends.xp import select_backend
        dev_name, _ = select_backend("cuda")  # raises if CUDA not available
        assert dev_name == "cuda", f"Expected CUDA backend, got {dev_name!r}"

    # Resolve 'auto' backend choice based on hardware.
    if impl == "auto":
        impl = "torch" if device_req.startswith("cuda") else "numpy"

    # Import concrete implementations.
    from rune_decrypter_prime.scoring.rune_scorer import RuneScorer
    from rune_decrypter_prime.scoring.torch_rune_scorer import RuneScorerTorch
    from rune_decrypter_prime.scoring.unified_rune_scorer import UnifiedRuneScorer

    if impl == "numpy":
        return RuneScorer(c_cfg, s_cfg)
    elif impl == "torch":
        return RuneScorerTorch(c_cfg, s_cfg)
    elif impl == "unified":
        return UnifiedRuneScorer(c_cfg, s_cfg)
    else:
        raise ValueError(f"Unknown scorer impl: {impl_raw!r}")


def build_optimizer(problem: DecryptionProblem, optimizer_cfg: OptimizerConfig) -> Any:
    """Construct an optimizer from its config."""
    if not isinstance(optimizer_cfg, OptimizerConfig):
        raise TypeError(f"optimizer_cfg must be an OptimizerConfig, not {type(optimizer_cfg)}")
    name = optimizer_cfg.name.lower()
    OptCls = OPTIMIZERS[name]
    return OptCls(problem, optimizer_cfg)


# ---------- Engine (config is the API) ----------
class RuneSolverEngine:
    """High-level solver that wires cipher, scorer, and optimizer from config.

    Golden rules
    ------------
    • The configuration is the single source of truth.
    • Fixed interruptors and transpositions live in the cipher pipeline.
    • Optimisers may opt-in to structure search knobs (interrupt pools, modes).
    • Telemetry is best-effort and never blocks solving.
    """

    def __init__(self, cfg: RunConfig):
        """Initialise the engine with a run configuration."""
        self.cfg = cfg
        self._seed = cfg.seed
        self._telemetry_on = bool(getattr(cfg, "enable_telemetry", True))

        # 1) Cipher (pipeline reads interrupters/transpositions from cfg.cipher)
        self.cipher = build_cipher(cfg.cipher)

        # 2) Scorer & Problem
        self.scorer = build_scorer(cfg.cipher, cfg.scorer_params)
        self.problem = DecryptionProblem(cipher=self.cipher, scorer=self.scorer, c_cfg=cfg.cipher)
        self.encoding_dir = getattr(cfg.scorer_params, "encoding_dir", "fwd")

        # Attach scorer telemetry (impl/device/dtype) if exposed
        try:
            sc_tel = getattr(self.scorer, "telemetry_scorer", None)
            if isinstance(sc_tel, dict) and getattr(self.problem, "telemetry", None) is not None:
                self.problem.telemetry.scorer = dict(sc_tel)
        except Exception:
            pass  # non-fatal

        # [LOGGER — begin]
        log_cfg = getattr(self.cfg, "logging", None)
        if not isinstance(log_cfg, LoggingConfig):
            log_cfg = LoggingConfig(verbose=True, print_progress=True, write_jsonl=True)

        self._logger = RunLogger(
            out_dir=getattr(log_cfg, "out_dir", None),
            echo=bool(getattr(log_cfg, "print_progress", True)),
        ) if bool(getattr(log_cfg, "verbose", True)) else None

        if self._logger:
            dev_str = getattr(self.cfg.cipher, "device", None) or "numpy"
            self._logger.log_event({
                "type": "run_start",
                "seed": self._seed,
                "cipher": getattr(self.cfg.cipher, "name", "unknown"),
                "optimizer": getattr(getattr(self.cfg, "optimizer", None), "name", None),
                "device": dev_str,
            })
        # [LOGGER — end]

        # 3) Optimizer (pure config)
        self.optimizer = build_optimizer(self.problem, cfg.optimizer)

        # ---- Optional handoffs for structure search (future-ready) ----
        intr_exact = getattr(cfg.cipher, "interruptors_exact", None)
        intr_legacy = getattr(cfg.cipher, "interruptors", None)
        fixed_interrupt_idx = intr_exact if intr_exact is not None else intr_legacy

        if hasattr(self.optimizer, "set_interrupt_idx"):
            self.optimizer.set_interrupt_idx(
                np.asarray(fixed_interrupt_idx, dtype=np.intp) if fixed_interrupt_idx is not None else None
            )

        pool = getattr(cfg.cipher, "interruptors_pool", None)
        imax = getattr(cfg.cipher, "interruptors_max", None)
        if hasattr(self.optimizer, "set_interrupt_search_space"):
            self.optimizer.set_interrupt_search_space(
                pool=np.asarray(pool, dtype=np.intp) if pool is not None else None,
                max_count=int(imax) if imax is not None else None,
            )

        t_modes = getattr(cfg.cipher, "transposition_search_modes", None)
        if hasattr(self.optimizer, "set_transposition_modes"):
            self.optimizer.set_transposition_modes(t_modes)

    def _scorer_telemetry_dict(self) -> dict:
        """Return a normalised scorer telemetry dict with safe defaults."""
        sc = getattr(self, "scorer", None)
        out = {}
        if sc and hasattr(sc, "telemetry"):
            out.update(sc.telemetry() or {})
        out.setdefault("impl", "numpy")
        out.setdefault("device", "cpu")
        out.setdefault("dtype", "float32")
        return out

    # TODO: Many versions of this exist; centralise in scorer later.
    def _extract_direction_from_scorer(self) -> str | None:
        """Infer scoring direction from the scorer’s config, if present."""
        sc = getattr(self, "scorer", None)
        if sc is None:
            return None
        s_cfg = getattr(sc, "s_cfg", None)
        val = None
        if isinstance(s_cfg, dict):
            val = s_cfg.get("encoding_dir") or s_cfg.get("dir")
        else:
            val = getattr(s_cfg, "encoding_dir", None) or getattr(s_cfg, "dir", None)
        if isinstance(val, str):
            v = val.lower()
            if v in ("fwd", "rev"):
                return v
        return None

    def _component_telemetry(self, obj) -> dict:
        """Safely call `obj.telemetry()` and normalise the result to a dict."""
        try:
            if obj is not None and hasattr(obj, "telemetry"):
                t = obj.telemetry()
                return dict(t) if isinstance(t, dict) else {}
        except Exception:
            pass
        return {}

    def solve(self) -> Solution:
        """Run the optimizer, attach telemetry/summary, and return the Solution."""
        # 1) Run the search (optimizer constructs the Solution)
        sol = self.optimizer.search()

        # 2) Ensure sol.meta is a dict
        if not isinstance(sol.meta, dict):
            sol.meta = {} if sol.meta is None else dict(sol.meta)

        # 3) Telemetry aggregation (only if enabled)
        telemetry_on = bool(getattr(self, "_telemetry_on", True))
        if telemetry_on:
            tel: dict = {}

            # 3a) Problem-level counters if present
            problem = getattr(self, "problem", None)
            prob_tel_obj = getattr(problem, "telemetry", None)
            if prob_tel_obj is not None and hasattr(prob_tel_obj, "to_dict"):
                try:
                    base = prob_tel_obj.to_dict()
                    if isinstance(base, dict):
                        tel.update(base)
                except Exception:
                    pass  # non-fatal

            # 3b) Canonical fields
            cfg_dev = str(getattr(self.cfg.cipher, "device", None) or "cpu")
            dev_norm = "cuda" if cfg_dev.lower().startswith("cuda") else cfg_dev.lower()
            tel["device"] = dev_norm
            tel["seed"] = getattr(self, "_seed", None)
            tel["cipher"] = getattr(self.cfg.cipher, "name", "unknown")

            # 3c) Scorer telemetry (authoritative for impl/device/dtype)
            sc_tel = self._component_telemetry(getattr(self, "scorer", None))
            sc_tel.setdefault("impl", "numpy")
            sc_tel.setdefault("device", dev_norm)
            sc_tel.setdefault("dtype", "float32")
            tel["scorer"] = sc_tel

            # 3d) Optimizer telemetry (optional)
            opt_tel = self._component_telemetry(getattr(self, "optimizer", None))
            if opt_tel:
                tel["optimizer"] = opt_tel

            # 3e) Merge with any existing meta.telemetry (preserve our normalised keys)
            existing = sol.meta.get("telemetry")
            if isinstance(existing, dict):
                if "scorer" in existing:
                    tel["scorer"] = {**existing["scorer"], **tel["scorer"]}
                if "optimizer" in existing and "optimizer" in tel:
                    tel["optimizer"] = {**existing["optimizer"], **tel["optimizer"]}
                tel = {**existing, **tel}

            # --- Direction (normalised) ---
            if self.encoding_dir is not None:
                tel["encoding_dir"] = self.encoding_dir
                tel.setdefault("scoring", {})["encoding_dir"] = self.encoding_dir
                tel.setdefault("scorer", {})["encoding_dir"] = self.encoding_dir

            # Robust to dict-or-object s_cfg
            try:
                s_cfg = getattr(self.scorer, "s_cfg", None)
                sdir = (s_cfg.get("dir") if isinstance(s_cfg, Mapping) else getattr(s_cfg, "dir", None))
                if sdir is not None:
                    tel.setdefault("scorer", {})
                    tel["scorer"]["dir"] = sdir
            except Exception:
                pass

            # Bubble up fast-path tags if present
            reason = sol.meta.get("reason")
            if reason is not None:
                tel.setdefault("reason", reason)
                tel.setdefault("fastpath", True)
            opt = sol.meta.get("optimizer")
            if opt is not None:
                tel.setdefault("optimizer", opt)

            sol.meta["telemetry"] = tel

        # 4) Build a compact summary
        pt = getattr(sol, "plaintext", "")
        len_plaintext = int(pt.size) if hasattr(pt, "size") else (len(pt) if pt is not None else 0)
        summary = {
            "cipher": getattr(self.cfg.cipher, "name", "unknown"),
            "device": str(getattr(self.cfg.cipher, "device", None) or "cpu"),
            "optimizer": getattr(getattr(self.cfg, "optimizer", None), "name", None),
            "score": float(getattr(sol, "score", float("nan"))),
            "len_plaintext": len_plaintext,
        }

        tel_meta = sol.meta.get("telemetry") if telemetry_on else None
        if isinstance(tel_meta, dict):
            summary.update({
                "candidates": tel_meta.get("candidates_evaluated"),
                "tokens": tel_meta.get("tokens_processed"),
                "decrypt_time": tel_meta.get("decrypt_time"),
                "score_time": tel_meta.get("score_time"),
            })

        sol.meta["run_meta"] = summary

        # 5) Logging
        if getattr(self, "_logger", None):
            if telemetry_on:
                self._logger.log_event({"type": "run_end", **summary})
                self._logger.log_event({"type": "run_meta", **summary})
            else:
                self._logger.log_event({
                    "type": "run_end",
                    "cipher": summary["cipher"],
                    "device": summary["device"],
                    "score": summary["score"],
                })

        # 6) Optional telemetry dump
        if telemetry_on and getattr(self.cfg, "logging", None) and getattr(self.cfg.logging, "write_jsonl", False):
            try:
                path = dump_telemetry(sol, base_dir="out/logs")
                if getattr(self._logger, "echo", False):
                    print(f"[telemetry dumped] {path}")
            except Exception as e:
                if getattr(self._logger, "echo", False):
                    print(f"[telemetry dump failed] {e}")

        return sol


# ------------------------------------------------------------
# TODO (non-blocking):
# - Prefer `cipher_registry` over the legacy static `CIPHERS` table.
# - Centralise scoring-direction discovery (single helper in scorer).
# - Consider aligning logger defaults with RuneSolver wrapper.
# ------------------------------------------------------------
