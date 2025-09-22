# ---- rune_decrypter_prime/ui/api.py
"""
ui/api.py — public, user-facing solve() entrypoint

Scope
-----
- Normalizes user-provided params (aliases allowed *only here*).
- Builds cipher/key/optimizer/scorer objects with strict, internal names.
- Emits run/optimizer progress logs; returns a stable result structure.

Guarantee
---------
Behavior and defaults here are part of the user contract. Do not change without
an accompanying test & doc update.
"""

from __future__ import annotations
import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Literal, Any, Dict

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple, Union, Iterable, List, Sequence

import numpy as np

# Core contracts
from rune_decrypter_prime.core.config import (
    CipherConfig,
    OptimizerConfig,
    RunConfig
)
from rune_decrypter_prime.core.factory import build_solver
from rune_decrypter_prime.core.logging_config import (
    LoggingConfig as CoreLoggingConfig,
    init_logging as init_run_logging,
    current_paths as logging_current_paths,
)
# Local helpers
from .normalize import to_indices, make_single_word_wli
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.ui.wrappers import by_name, cipher_instance
# Ensure generic cipher is registered (side-effect registration of user_map2/3/lookup)
import rune_decrypter_prime.ciphers.generic_map_cipher  # noqa: F401


def _normalize_logging_cfg(logging: Any) -> CoreLoggingConfig:
    """
    Normalise user logging into the canonical core LoggingConfig.

    Accepts:
      - None → CoreLoggingConfig()
      - CoreLoggingConfig → returned as-is
      - dict → alias map + path coercion + unknown-key drop
    """
    if isinstance(logging, CoreLoggingConfig):
        return logging
    if logging is None:
        return CoreLoggingConfig()

    if isinstance(logging, dict):
        cfg: Dict[str, Any] = dict(logging)  # shallow copy

        # Friendly aliases (UI ergonomics)
        alias_map = {
            "trace": "enable_trace",
            "trace_enabled": "enable_trace",
            "traceTop": "trace_top_n",
            "trace_top": "trace_top_n",
            "traceSort": "trace_sort",
            "out": "out_root",
            "output_dir": "out_root",
            "progress": "print_progress",
            # For consistency with other modules; no jsonl_path in this core config
            # 'label' / 'run_kind' already match the core schema
        }
        for old, new in alias_map.items():
            if old in cfg and new not in cfg:
                cfg[new] = cfg.pop(old)

        # Coerce paths where relevant
        for path_key in ("out_root",):
            if path_key in cfg and cfg[path_key] is not None and not isinstance(cfg[path_key], Path):
                try:
                    cfg[path_key] = str(Path(cfg[path_key]).resolve())
                except Exception:
                    cfg.pop(path_key, None)

        # Keep only fields that exist in the core schema
        valid_fields = {
            "verbose", "print_progress", "write_jsonl",
            "repo_root", "out_root", "run_kind", "label", "fixed_run_dir"
        }
        filtered = {k: v for k, v in cfg.items() if k in valid_fields}
        return CoreLoggingConfig(**filtered)

    raise TypeError("logging must be None, a dict, or core.logging_config.LoggingConfig")



# ------------------------------- CipherSpec -------------------------------
@dataclass(slots=True)
class CipherSpec:
    """
    Declarative description of the cipher's *local* transform.

    Kinds:
      - kind="wrapper"   : classic name, mapped to an existing core cipher implementation
      - kind="user_map2" : ct = f(pt, k)           (1 keystream)
      - kind="user_map3" : ct = f(pt, k1, k2)      (2 keystreams)
      - kind="lookup"    : ct ~ M[pt, k]           (table; may be non 1→1)

    Degeneracy:
      - degeneracy="allow" keeps candidate lists per (ct,key) column up to per_pos_limit
      - degeneracy="forbid" uses the first encountered pt for each (ct,key) pair
    """
    name: str
    N: int = 29
    kind: str = "UNKNOWN"

    # generic-map fields
    function: Optional[Callable[..., int]] = None
    table: Optional[Any] = None
    degeneracy: str = "forbid"
    resolver: str = "first"      # "first" | "expand_beam"
    per_pos_limit: int = 1

    # wrapper routing
    wrapper_core: Optional[str] = None

    # misc
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def user_map2(cls, function: Callable[[int, int], int], *,
                  N: int = 29, degeneracy: str = "forbid",
                  resolver: str = "first", per_pos_limit: int = 1,
                  name: Optional[str] = None) -> CipherSpec:
        if not callable(function):
            raise TypeError("user_map2 requires a function(pt, k) -> ct")
        return cls(kind="user_map2", name=name or "user_map2", N=N,
                   function=function, degeneracy=degeneracy,
                   resolver=resolver, per_pos_limit=per_pos_limit)

    @classmethod
    def user_map3(cls, function: Callable[[int, int, int], int], *,
                  N: int = 29, degeneracy: str = "forbid",
                  resolver: str = "first", per_pos_limit: int = 1,
                  name: Optional[str] = None) -> CipherSpec:
        if not callable(function):
            raise TypeError("user_map3 requires a function(pt, k1, k2) -> ct")
        return cls(kind="user_map3", name=name or "user_map3", N=N,
                   function=function, degeneracy=degeneracy,
                   resolver=resolver, per_pos_limit=per_pos_limit)

    @classmethod
    def from_lookup(cls, table: Any, *,
                    N: int = 29, degeneracy: str = "allow",
                    resolver: str = "first", per_pos_limit: int = 4,
                    name: Optional[str] = None) -> CipherSpec:
        return cls(kind="lookup", name=name or "lookup", N=N,
                   table=table, degeneracy=degeneracy,
                   resolver=resolver, per_pos_limit=per_pos_limit)

    # internal: built by wrappers
    @classmethod
    def _wrapper(cls, *, name: str, core_name: str, N: int = 29) -> CipherSpec:
        return cls(kind="wrapper", name=name, N=N, wrapper_core=core_name)


# ------------------------------- KeySpec -------------------------------
@dataclass(slots=True)
class KeySpec:
    """
    Declarative keystream plan.

    Plans:
      - "repeat": repeating key of fixed period K (period_hint() == K)
      - "otp":    explicit per-position key stream (period_hint() is None)
      - "const":  constant value replicated to text length (period_hint() is None)
      - "keystream": function-defined stream (advanced)
    """
    plan: str
    params: Dict[str, Any] = field(default_factory=dict)
    _align_offset: Optional[Union[int, Tuple[str, int, int]]] = None  # e.g., ("search",-3,3)

    # --- factories ---
    @classmethod
    def repeat(cls, *, len: int) -> KeySpec:
        if int(len) <= 0:
            raise ValueError("KeySpec.repeat requires len > 0")
        return cls(plan="repeat", params={"len": int(len)})

    @classmethod
    def repeat_range(cls, *, min: int, max: int) -> KeySpec:
        return cls(plan="repeat_range", params={"min": int(min), "max": int(max)})

    @classmethod
    def block(cls, *, size: int, pattern=None) -> KeySpec:
        return cls(plan="block", params={"size": int(size), "pattern": pattern})

    @classmethod
    def otp(cls, *, stream: Iterable[int]) -> KeySpec:
        arr = np.asarray(list(stream), dtype=np.uint8).reshape(-1)
        if arr.size == 0:
            raise ValueError("KeySpec.otp requires a non-empty stream")
        return cls(plan="otp", params={"stream": arr.tolist()})

    @classmethod
    def const(cls, *, value: int) -> KeySpec:
        return cls(plan="const", params={"value": int(value)})

    @classmethod
    def keystream(cls, *, fn: Callable[..., np.ndarray], params: Optional[Dict[str, Any]] = None) -> KeySpec:
        return cls(plan="keystream", params={"fn": fn, "params": params or {}})

    @classmethod
    def permutation(cls, *, len: int) -> KeySpec:
        if int(len) <= 0:
            raise ValueError("KeySpec.permutation requires len > 0")
        return cls(plan="perm", params={"len": int(len)})

    @classmethod
    def matrix2x2(cls, *, A: int = 29) -> KeySpec:
        return cls(plan="matrix2x2", params={"A": int(A)})

    @classmethod
    def affine(cls, *, A: int = 29) -> KeySpec:
        return cls(plan="affine", params={"A": int(A)})

    # --- modifiers ---
    def align(self, *, offset: Union[int, Tuple[str, int, int]]) -> KeySpec:
        self._align_offset = offset
        return self

    # --- utils ---
    def period_hint(self) -> Optional[int]:
        if self.plan == "repeat":
            return int(self.params.get("len", 0)) or None
        return None

    def to_telemetry(self) -> Dict[str, Any]:
        t = {"plan": self.plan, **{k: v for k, v in self.params.items() if k != "stream"}}
        if self._align_offset is not None:
            t["align"] = self._align_offset
        return t


# ------------------------------- SolveSpec -------------------------------
@dataclass
class SolveSpec:
    """
    Search/optimizer budget. Maps to core OptimizerConfig unchanged.
    """
    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    seed: Optional[int] = None



    @classmethod
    def beam(cls, **params: Any) -> "SolveSpec":
        """
        Beam search (UI builder).
        Friendly keys accepted: width -> beam_width.
        Canonicalised keys passed downstream: beam_width (int), plus any passthroughs.
        """
        from rune_decrypter_prime.ui._resolve import resolve_optimizer_aliases as _resolve_opt
        canon: Dict[str, Any] = _resolve_opt("beam", dict(params))
        return cls(name="beam", params=canon)

    @classmethod
    def ga(cls, **params: Any) -> "SolveSpec":
        """
        Genetic algorithm (UI builder).
        Friendly keys accepted: population/pop -> pop_size; iterations/iters -> generations (pure GA).
        Canonicalised keys passed downstream: pop_size, generations.
        """
        from rune_decrypter_prime.ui._resolve import resolve_optimizer_aliases as _resolve_opt
        canon: Dict[str, Any] = _resolve_opt("ga", dict(params))
        return cls(name="ga", params=canon)

    @classmethod
    def sa(cls, **params: Any) -> "SolveSpec":
        """
        Simulated annealing (UI builder).
        Friendly keys accepted: iters/iterations -> sa_iters.
        Canonicalised keys passed downstream: sa_iters (+ sa_init_temp, sa_min_temp, sa_cooling if provided).
        """
        from rune_decrypter_prime.ui._resolve import resolve_optimizer_aliases as _resolve_opt
        canon: Dict[str, Any] = _resolve_opt("sa", dict(params))
        return cls(name="sa", params=canon)

    @classmethod
    def hybrid(cls, **params: Any) -> "SolveSpec":
        """
        Hybrid optimiser (UI builder) = optional Beam warm start + GA explore + SA polish.

        Policy (to remove ambiguity):
          - GA MUST use 'generations'/'gens'. (In hybrid only, GA will not consume 'iterations'/'iters'.)
          - SA uses 'sa_iters' OR friendly 'iters'/'iterations'.

        Canonicalised keys passed downstream:
          - beam_width (if any), pop_size/generations (GA), sa_iters (+ SA temps/cooling), plus passthroughs.
        """
        from rune_decrypter_prime.ui._resolve import resolve_optimizer_aliases as _resolve_opt
        canon: Dict[str, Any] = _resolve_opt("hybrid", dict(params))
        return cls(name="hybrid", params=canon)


# -------------------------------- run API --------------------------------
class run:
    """
    High-level entrypoint:

      run.solve(text, cipher, key, solve, *,
                device="cpu",
                scorer="rune",
                scorer_params=None,
                logging=None)

    - Normalizes 'text' to indices and builds WLI.
    - Adapts CipherSpec/KeySpec to CipherConfig/OptimizerConfig.
    - Calls build_solver(RunConfig(...)).solve() and returns Solution.
    """
    # @classmethod
    # def solve(cls,
    #           text: Union[str, np.ndarray, list, tuple],
    #           cipher: CipherSpec,
    #           key: Union[KeySpec, Tuple[KeySpec, KeySpec]],
    #           solve: SolveSpec,
    #           *,
    #           device: str = "cpu",
    #           scorer: str = "rune",
    #           scorer_params: Optional[Dict[str, Any]] = None,
    #           logging: Optional[Dict[str, Any]] = None
    #           ):
    #     """
    #     Solve a ciphertext with the given cipher spec, key spec, and optimizer budget.
    #     (Interface and behaviour unchanged; refactored for clarity.)
    #     """
    #
    #     # 1) Normalise ciphertext & WLI
    #     ct, wli, L = _normalize_ct_and_wli(text)
    #
    #     # 2) Wrapper vs Generic map routing, with known-key fast path for otp/const
    #     if cipher.kind == "wrapper":
    #         cfg_cipher = _build_cipher_config_wrapper(cipher, key, ct, wli, device)
    #     else:
    #         # Fast path (otp/const) returns early if taken
    #         fast = _maybe_solve_known_key_fastpath(cipher, key if isinstance(key, KeySpec) else key[0],
    #                                                ct, wli, L, device, scorer, scorer_params, logging)
    #         if fast is not None:
    #             return fast
    #         cfg_cipher = _build_cipher_config_generic(cipher, key, ct, wli, L, device)
    #
    #     # 3) Scorer params with UI defaults
    #     sp = _scorer_params_with_defaults(scorer_params)
    #
    #     # 4) Optimizer config (with centralised alias resolution)
    #     # todo move up to top
    #     from rune_decrypter_prime.ui._resolve import \
    #         resolve_optimizer_aliases as _resolve_opt  # local import to avoid top churn
    #     params_canon = _resolve_opt(solve.name, dict(solve.params))
    #     cfg_opt = OptimizerConfig(name=solve.name, params=params_canon)
    #
    #     # 5) Assemble RunConfig & solve
    #     run_cfg = RunConfig(
    #         cipher=cfg_cipher,
    #         scorer_name=scorer,
    #         scorer_params=sp,
    #         optimizer=cfg_opt,
    #         logging=_normalize_logging_cfg(logging),
    #     )
    #     engine = build_solver(run_cfg)
    #     res = engine.solve()
    #
    #     # 6) Ensure plaintext is a rune string (keep convenience attachments)
    #     return _ensure_plaintext_rune(res)

    @classmethod
    def solve(cls,
              text: Union[str, np.ndarray, list[int], tuple[int, ...]],
              cipher: CipherSpec,
              key: Union[KeySpec, tuple[KeySpec, KeySpec]],
              solve: SolveSpec,
              *,
              device: str = "cpu",
              scorer: str = "rune",
              scorer_params: Optional[Dict[str, Any]] = None,
              logging: Optional[Dict[str, Any]] = None,
              wli_data: Optional[Sequence[Sequence[int]]] = None,
              force_no_wli: Optional[bool] = None,
              initial_keys: Optional[List[List[int]]] = None,
              ):
        """
        Solve a ciphertext with the given cipher spec, key spec, and optimizer budget.

        Accepted ciphertext forms
        -------------------------
        • Rune string (29-alphabet, with spaces optional)
        • English string (26 letters; converted via Runeglish.translate_to_gematria)
        • Sequence of ints (already rune indices 0..28)

        Normalisation
        -------------
        • Always converted to np.ndarray[uint8] of rune indices
        • WLI:
            - If caller provides `wli_data`, we trust it
            - Else if input was a string, infer word lengths from spaces
            - Else (indices), default to single-word WLI
        """
        from rune_decrypter_prime.ui.normalize import normalize_ciphertext, wli_from_text

        ct, wli = normalize_ciphertext(text, wli_data)
        if force_no_wli: wli = None
        L = int(ct.size)

        # --- 2) Canonicalise scorer/optimizer params ---
        from rune_decrypter_prime.ui._resolve import (
            resolve_optimizer_aliases as _resolve_opt,
            resolve_scorer_aliases as _resolve_score,
        )
        sp_canon = _resolve_score(scorer_params)
        sp = _scorer_params_with_defaults(sp_canon)

        params_in = dict(solve.params) if getattr(solve, "params", None) else {}
        params_canon = _resolve_opt(solve.name, params_in)

        # Attach initial_keys into optimizer params (UI contract)
        if initial_keys is not None:
            params_canon["initial_keys"] = initial_keys

        cfg_opt = OptimizerConfig(name=solve.name, params=params_canon)

        # --- 3) Cipher config ---
        if cipher.kind == "wrapper":
            cfg_cipher = _build_cipher_config_wrapper(cipher, key, ct, wli, device)
        else:
            fast = _maybe_solve_known_key_fastpath(
                cipher,
                key if isinstance(key, KeySpec) else key[0],
                ct, wli, L,
                device,
                scorer,
                sp,
                logging
            )
            if fast is not None:
                return fast
            cfg_cipher = _build_cipher_config_generic(cipher, key, ct, wli, L, device)

        # --- 4) Assemble run config + solve ---
        run_cfg = RunConfig(
            cipher=cfg_cipher,
            scorer_name=scorer,
            scorer_params=sp,
            optimizer=cfg_opt,
            logging=_normalize_logging_cfg(logging),
        )


        engine = build_solver(run_cfg)
        res = engine.solve()

        # attach telemetry if present
        tel = getattr(engine, "telemetry", None)
        if tel is not None and hasattr(tel, "optimizer"):
            try:
                res.meta = dict(getattr(res, "meta", {}) or {})
                res.meta["telemetry"] = tel.to_dict() if hasattr(tel, "to_dict") else dict(tel)
            except Exception:
                pass

        return _ensure_plaintext_rune(res)

    # @classmethod
    # def solve(cls,
    #           text: Union[str, np.ndarray, list, tuple],
    #           cipher: CipherSpec,
    #           key: Union[KeySpec, Tuple[KeySpec, KeySpec]],
    #           solve: SolveSpec,
    #           *,
    #           device: str = "cpu",
    #           scorer: str = "rune",
    #           scorer_params: Optional[Dict[str, Any]] = None,
    #           logging: Optional[Dict[str, Any]] = None,
    #           wli_data: Optional[Sequence[Sequence[int]]] = None
    #           ):
    #     """
    #     Solve a ciphertext with the given cipher spec, key spec, and optimizer budget.
    #     Interface and behaviour unchanged; refactored for clarity.
    #
    #     Pipeline
    #     --------
    #     1) Normalise ciphertext & WLI.
    #     2) Canonicalise UI-only params:
    #          - Scorer params: alias -> canonical, then apply UI defaults.
    #          - Optimiser params: alias -> canonical (defensive, idempotent).
    #     3) Route cipher (wrapper vs generic), attempt known-key fast path where applicable.
    #     4) Assemble RunConfig.
    #     5) Solve & post-process plaintext format.
    #     """
    #
    #     # 1) Normalise ciphertext & WLI
    #     ct, wli, L = _normalize_ct_and_wli(text, wli_override=wli_data)
    #
    #     # 2) Canonicalise UI-only params (scorer + optimiser)
    #     #    Keep imports local to minimise header churn.
    #     from rune_decrypter_prime.ui._resolve import (
    #         resolve_optimizer_aliases as _resolve_opt,
    #         resolve_scorer_aliases as _resolve_score,
    #     )
    #
    #     # Scorer: aliases -> canonical, then apply your UI defaults
    #     sp_canon = _resolve_score(scorer_params)
    #     sp = _scorer_params_with_defaults(sp_canon)
    #
    #     # Optimiser: aliases -> canonical (defensive even if SolveSpec builders already did it)
    #     params_in = dict(solve.params) if getattr(solve, "params", None) else {}
    #     params_canon = _resolve_opt(solve.name, params_in)
    #     cfg_opt = OptimizerConfig(name=solve.name, params=params_canon)
    #
    #     # 3) Wrapper vs Generic map routing, with known-key fast path for otp/const
    #     if cipher.kind == "wrapper":
    #         cfg_cipher = _build_cipher_config_wrapper(cipher, key, ct, wli, device)
    #     else:
    #         # Fast path (otp/const) returns early if taken.
    #         # NOTE: pass canonical+defaulted scorer params 'sp' so aliases work in fast path too.
    #         fast = _maybe_solve_known_key_fastpath(
    #             cipher,
    #             key if isinstance(key, KeySpec) else key[0],
    #             ct, wli, L,
    #             device,
    #             scorer,
    #             sp,            # <- canonical + defaults applied
    #             logging
    #         )
    #         if fast is not None:
    #             return fast
    #         cfg_cipher = _build_cipher_config_generic(cipher, key, ct, wli, L, device)
    #
    #     # 4) Assemble RunConfig & solve
    #     run_cfg = RunConfig(
    #         cipher=cfg_cipher,
    #         scorer_name=scorer,
    #         scorer_params=sp,
    #         optimizer=cfg_opt,
    #         logging=_normalize_logging_cfg(logging),
    #     )
    #     engine = build_solver(run_cfg)
    #     res = engine.solve()
    #
    #     # After solve, pull optimizer telemetry from engine
    #     tel = getattr(engine, "telemetry", None)
    #     if tel is not None and hasattr(tel, "optimizer"):
    #         try:
    #             res.meta = dict(getattr(res, "meta", {}) or {})
    #             res.meta["telemetry"] = tel.to_dict() if hasattr(tel, "to_dict") else dict(tel)
    #         except Exception:
    #             pass
    #     # 5) Ensure plaintext is a rune string (keep convenience attachments)
    #     return _ensure_plaintext_rune(res)


# ---------------- Top-level UX helpers ----------------
def define_map(*, N: int = 29, function: Optional[Callable[..., int]] = None,
               table: Optional[Any] = None, degeneracy: str = "forbid",
               resolver: str = "first", per_pos_limit: int = 1, name: Optional[str] = None) -> CipherSpec:
    """
    Define a cipher map (function or lookup).
    """
    if function is not None and table is not None:
        raise ValueError("Provide either function or table, not both.")
    if function is not None:
        import inspect
        n = len(inspect.signature(function).parameters)
        if n == 2:
            return CipherSpec.user_map2(function=function, N=N, degeneracy=degeneracy,
                                        resolver=resolver, per_pos_limit=per_pos_limit, name=name)
        elif n == 3:
            return CipherSpec.user_map3(function=function, N=N, degeneracy=degeneracy,
                                        resolver=resolver, per_pos_limit=per_pos_limit, name=name)
        else:
            raise ValueError("Mapping function must take 2 or 3 parameters (plaintext, key[, key2]).")
    if table is not None:
        return CipherSpec.from_lookup(table=table, N=N, degeneracy=degeneracy,
                                      resolver=resolver, per_pos_limit=per_pos_limit, name=name)
    raise ValueError("Either function or table must be provided to define_map.")


def define_cipher(*, name: Optional[str] = None, function: Optional[Callable[..., int]] = None,
                  table: Optional[Any] = None, key: Optional[KeySpec] = None,
                  key_len: Optional[int] = None, N: int = 29,
                  degeneracy: str = "forbid", resolver: str = "first", per_pos_limit: int = 1):
    """
    Convenience to get (CipherSpec, KeySpec).
    """
    if name:
        spec, default_key = by_name.cipher_with_key(
            name,
            **({"key_len": key_len} if key_len is not None else {}),
            default_key=True,
        )
        ks = key if key is not None else (default_key if default_key is not None else KeySpec.repeat(len=key_len or 1))
        return spec, ks
    else:
        spec = define_map(N=N, function=function, table=table,
                          degeneracy=degeneracy, resolver=resolver, per_pos_limit=per_pos_limit, name=None)
        ks = key if key is not None else KeySpec.repeat(len=int(key_len) if key_len is not None else 1)
        return spec, ks


def preview(text: Union[str, np.ndarray, list, tuple], *, cipher: CipherSpec, key: KeySpec,
            direction: str = "decrypt", device: str = "cpu") -> str:
    """
    Apply the cipher once with a fully specified key (OTP/const). Deterministic, device-agnostic.
    """
    arr = to_indices(text)
    L = int(arr.size)

    # Build known key stream
    if key.plan == "otp":
        stream = np.asarray(key.params["stream"], dtype=np.uint8).reshape(-1)
    elif key.plan == "const":
        val = int(key.params.get("value", 0))
        stream = np.full(L, val, dtype=np.uint8)
    else:
        raise ValueError("preview requires a concrete key (KeySpec.otp or KeySpec.const)")
    stream = _apply_align_offset_if_any(stream, getattr(key, "_align_offset", None), L)

    # CipherConfig (attach spec for generic maps)
    cfg_cipher = CipherConfig(
        ciphertext=(arr if direction.lower() == "decrypt" else np.zeros(L, dtype=np.uint8)),
        wli_data=make_single_word_wli(L),
        key_length=int(stream.size),
        text_transposition="fwd",
        device=device,
        name=(cipher.kind if cipher.kind in ("user_map2", "user_map3", "lookup") else (cipher.wrapper_core or cipher.name)),
    )
    if cipher.kind in ("user_map2", "user_map3", "lookup"):
        setattr(cfg_cipher, "spec", cipher)

    # Minimal RunConfig so factory builds the cipher; optimizer in single-key test mode
    cfg_opt = OptimizerConfig(name="beam", params={"beam_width": 1, "test_key": stream.tolist()})
    run_cfg = RunConfig(cipher=cfg_cipher, scorer_name="rune", scorer_params={"objective": "pct.logp.win10", "n_char": 2, "n_wli": 2, "win": 10},
                        optimizer=cfg_opt, logging=_normalize_logging_cfg())
    engine = build_solver(run_cfg)

    # Directly use the instantiated cipher for transform
    cipher_impl = getattr(engine, "cipher", engine)
    if direction.lower() == "decrypt":
        out = cipher_impl.decrypt(ciphertext=arr, key=stream)
    elif direction.lower() == "encrypt":
        out = cipher_impl.encrypt(plaintext=arr, key=stream)
    else:
        raise ValueError("direction must be 'decrypt' or 'encrypt'.")

    result_idx = out[0] if isinstance(out, tuple) else out
    result_idx = np.asarray(result_idx, dtype=np.uint8).reshape(-1)

    # Pretty print using Runeglish segments
    wli = make_single_word_wli(result_idx.size)
    return Runeglish.to_rune(result_idx, wli)


# --------------------------- internal helpers ---------------------------
def _apply_align_offset_if_any(stream: np.ndarray, offset: Optional[Union[int, Tuple[str, int, int]]], L: int) -> np.ndarray:
    s = np.asarray(stream, dtype=np.uint8).reshape(-1)
    if isinstance(offset, int):
        if offset >= 0:
            if offset >= s.size:
                raise ValueError("Key offset exceeds key length.")
            s = s[offset:]
        else:
            if abs(offset) > s.size:
                raise ValueError("Negative key offset exceeds key length.")
            s = s[: s.size + offset]
    # fit to length L
    if s.size < L:
        s = np.resize(s, L)
    elif s.size > L:
        s = s[:L]
    return s

# --------------------------- internal helpers (added) ---------------------------
# in ui/api.py
def _normalize_ct_and_wli(
    text: Union[str, np.ndarray, list, tuple],
    wli_override: Optional[Sequence[Sequence[int]]] = None,
) -> tuple[np.ndarray, list[list[int]], int]:
    """Normalise ciphertext to indices and build WLI (word-breaks) as PLAIN LISTS."""
    from rune_decrypter_prime.ui.normalize import to_indices, make_single_word_wli, wli_from_text

    ct = to_indices(text)
    L = int(ct.size)

    if wli_override is not None:
        # Coerce override to a nested Python list of [i, L]
        wli_list = [[int(r[0]), int(r[1])] for r in wli_override]
    else:
        if isinstance(text, str):
            # Respect spaces for strings → multi-word WLI
            wli_list = wli_from_text(text)
        else:
            # list[int]/array path → single-word WLI by default
            wli_list = make_single_word_wli(L)

    # Fit WLI to length (truncate/pad with zeros if needed) while staying as lists
    if len(wli_list) != L:
        if len(wli_list) > L:
            wli_list = wli_list[:L]
        else:
            pad = [[0, 0]] * (L - len(wli_list))
            wli_list = wli_list + pad

    return ct, wli_list, L



from typing import Dict, Any, Optional

def _scorer_params_with_defaults(scorer_params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply the UI-level scorer defaults, but never overwrite
    caller-provided keys. Caller values always win.
    """
    # 1. Start with a dict of defaults
    d = {
        "objective": "pct.logp.win10",
        "char_weights": {2:1.0},   # e.g., {2:0.4, 3:0.6}
        "wli_weights": {2:1.0},    # e.g., {2:0.4, 3:0.6}
        "win": 10,
    }

    # 2. Overlay caller values (only overwriting defaults if explicitly given)
    if scorer_params:
        for k, v in scorer_params.items():
            if v is not None:   # keep explicit None optional
                d[k] = v

    return d


def _build_cipher_config_wrapper(cipher: CipherSpec, key: KeySpec,
                                 ct: np.ndarray, wli: np.ndarray, device: str) -> CipherConfig:
    """Wrapper path (currently Vigenère + Columnar)."""
    if cipher.wrapper_core == "vigenere":
        ...
    elif cipher.wrapper_core == "columnar":
        if key.plan != "perm":
            raise ValueError("Columnar requires KeySpec.permutation(len=K)")
        key_length = int(key.params.get("len", 0))
        if key_length <= 0:
            raise ValueError("Columnar requires permutation key with len>0")
        return CipherConfig(
            ciphertext=ct,
            wli_data=wli,
            key_length=key_length,
            text_transposition="fwd",
            device=device,
            name="columnar",
        )
    elif cipher.wrapper_core == "substitution":
        # Determine K (permutation length).
        # 1) Prefer K from KeySpec.permutation(len=K) if provided.
        K = None
        try:
            if key is not None and getattr(key, "plan", None) == "perm":
                K = int(key.params.get("len", 0) or 0)
        except Exception:
            K = None

        # 2) Otherwise fall back to the wrapper’s declared alphabet size.
        if not K or K <= 0:
            K = (getattr(cipher, "alphabet", None)
                 or getattr(cipher, "N", None)
                 or 29)  # default Rune/Cicada29

        # Build the config. key_length carries K for permutation ops; period is not used by the cipher.
        return CipherConfig(
            ciphertext=ct,
            wli_data=wli,
            key_length=int(K),  # <- IMPORTANT: K for PermutationOps / any legacy readers
            device=device,
            name="substitution",
        )
    else:
        raise NotImplementedError(f"Wrapper core '{cipher.wrapper_core}' not supported yet.")


def _maybe_solve_known_key_fastpath(cipher: CipherSpec, key: KeySpec,
                                    ct: np.ndarray, wli: np.ndarray, L: int,
                                    device: str,
                                    scorer: str,
                                    scorer_params: Optional[Dict[str, Any]],
                                    logging: Optional[Dict[str, Any]]):
    """
    Known-key fast path for otp/const.
    Returns a Solution if taken; else returns None.
    """
    if not isinstance(key, KeySpec) or key.plan not in ("otp", "const"):
        return None

    # Build concrete key stream
    if key.plan == "otp":
        stream = np.asarray(key.params["stream"], dtype=np.uint8).reshape(-1)
    else:
        val = int(key.params.get("value", 0))
        stream = np.full(L, val, dtype=np.uint8)
    stream = _apply_align_offset_if_any(stream, key._align_offset, L)

    # Cipher config (attach spec for generic maps)
    cfg_cipher = CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=int(stream.size),
        text_transposition="fwd",
        device=device,
        name=cipher.kind,
    )
    setattr(cfg_cipher, "spec", cipher)

    # Single-key evaluation via width-1 beam + test_key
    cfg_opt = OptimizerConfig(name="beam", params={"beam_width": 1, "test_key": stream.tolist()})
    sp = _scorer_params_with_defaults(scorer_params)
    run_cfg = RunConfig(cipher=cfg_cipher,
                        scorer_name=scorer,
                        scorer_params=sp,
                        optimizer=cfg_opt,
                        logging=_normalize_logging_cfg(logging))
    engine = build_solver(run_cfg)
    return engine.solve()

def _build_cipher_config_generic(
    cipher: CipherSpec,
    key: Union[KeySpec, Tuple[KeySpec, KeySpec]],
    ct: np.ndarray,
    wli: np.ndarray,
    L: int,
    device: str,
) -> CipherConfig:
    """
    Generic map / lookup path. Validates KeySpec(s) and returns CipherConfig.

    Rules:
      - user_map3 → expects a tuple of two KeySpec (often repeats or permutations)
      - user_map2 → single KeySpec (repeat, perm, affine, matrix2x2, scalar, const, otp)
      - user_mapN fallback → require at least one valid KeySpec
    """
    period: Optional[int] = None
    key_length: Optional[int] = None

    # --- handle user_map3 with tuple of keys (e.g., affine, foursquare)
    if cipher.kind == "user_map3":
        if not isinstance(key, tuple) or len(key) != 2:
            raise ValueError("user_map3 requires a tuple of two KeySpecs.")
        k1, k2 = key
        # Common case: two repeat keys of same length
        if k1.plan == "repeat" and k2.plan == "repeat":
            p1, p2 = k1.period_hint(), k2.period_hint()
            if not p1 or not p2 or int(p1) != int(p2):
                raise ValueError("user_map3 repeat keys must have equal positive length.")
            key_length = int(p1)
        # Otherwise accept heterogeneous plans (permutation+permutation for foursquare, etc.)
        else:
            # Pick a meaningful length hint if available
            key_length = k1.period_hint() or k2.period_hint()

    # --- handle user_map2 with single key
    elif cipher.kind.startswith("user_map"):
        if isinstance(key, tuple):
            raise ValueError(f"{cipher.kind} expects a single KeySpec, got tuple.")
        # Dispatch by plan
        if key.plan == "repeat":
            period = key.period_hint()
            if not period or int(period) <= 0:
                raise ValueError("repeat key requires len > 0")
            key_length = int(period)

        elif key.plan == "perm":
            # permutation length is explicit
            key_length = int(key.params["len"])

        elif key.plan == "matrix2x2":
            key_length = 4  # flattened 2x2

        elif key.plan == "affine":
            key_length = 2  # (a, b)

        elif key.plan in ("scalar", "const"):
            key_length = 1

        elif key.plan == "otp":
            # OTP has explicit stream, not periodic
            key_length = None

        elif key.plan == "block":
            # block keys have fixed size
            key_length = int(key.params["size"])

        elif key.plan == "keystream":
            key_length = None  # function-driven, not known

        else:
            raise ValueError(f"Unsupported KeySpec plan: {key.plan}")
    # --- handle user_map2 with single key
    elif cipher.kind.startswith("lookup"):
        # todo this is a degeneracy option for refactoring in when implemented
        pass
    else:
        raise ValueError(f"Unsupported cipher kind for generic builder: {cipher.kind}")

    # --- build config
    cfg_cipher = CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=key_length,
        text_transposition="fwd",
        device=device,
        name=cipher.kind,
    )
    setattr(cfg_cipher, "spec", cipher)
    return cfg_cipher


def _ensure_plaintext_rune(res):
    """
    Post-process result to ensure rune string plaintext; attach extras as today.
    """
    pt = getattr(res, "plaintext", None)
    if isinstance(pt, (list, tuple, np.ndarray)):
        arr = np.asarray(pt, dtype=np.uint8).reshape(-1)
        res.plaintext = Runeglish.to_rune(arr, make_single_word_wli(arr.size))
        # keep these convenience fields for callers relying on them
        res.plaintext_str = res.plaintext
        res.plaintext_idx = arr
    return res

