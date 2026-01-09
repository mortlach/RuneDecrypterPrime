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
    SolverConfig,
    RunConfig
)
from rune_decrypter_prime.core.types import Device, KEY_DTYPE
# Local helpers
# Ensure generic cipher is registered (side-effect registration of user_map2/3/lookup)
import rune_decrypter_prime.ciphers.generic_map_cipher  # noqa: F401

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
      - resolver_limit caps the number of full plaintext candidates scored per key
    """
    name: str
    N: int = 29
    kind: str = "UNKNOWN"

    # generic-map fields
    function: Optional[Callable[..., int]] = None
    table: Optional[Any] = None
    degeneracy: str = "forbid"
    resolver: str = "expand_beam"      # "first" | "expand_beam"
    per_pos_limit: int = 29
    resolver_limit: int = 8193

    # wrapper routing
    wrapper_core: Optional[str] = None
    device: Optional[str, Device] = Device.CPU

    # misc
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def user_map2(cls, function: Callable[[int, int], int], *,
                  N: int = 29, degeneracy: str = "forbid",
                  resolver: str = "expand_beam", per_pos_limit: int = 29,
                  resolver_limit: int = 8193,
                  name: Optional[str] = None) -> CipherSpec:
        if not callable(function):
            raise TypeError("user_map2 requires a function(pt, k) -> ct")
        return cls(kind="user_map2", name=name or "user_map2", N=N,
                   function=function, degeneracy=degeneracy,
                   resolver=resolver, per_pos_limit=per_pos_limit,
                   resolver_limit=resolver_limit)

    @classmethod
    def user_map3(cls, function: Callable[[int, int, int], int], *,
                  N: int = 29, degeneracy: str = "forbid",
                  resolver: str = "expand_beam", per_pos_limit: int = 29,
                  resolver_limit: int = 8193,
                  name: Optional[str] = None) -> CipherSpec:
        if not callable(function):
            raise TypeError("user_map3 requires a function(pt, k1, k2) -> ct")
        return cls(kind="user_map3", name=name or "user_map3", N=N,
                   function=function, degeneracy=degeneracy,
                   resolver=resolver, per_pos_limit=per_pos_limit,
                   resolver_limit=resolver_limit)

    @classmethod
    def from_lookup(cls, table: Any, *,
                    N: int = 29, degeneracy: str = "allow",
                    resolver: str = "expand_beam", per_pos_limit: int = 29,
                    resolver_limit: int = 8193,
                    name: Optional[str] = None) -> CipherSpec:
        return cls(kind="lookup", name=name or "lookup", N=N,
                   table=table, degeneracy=degeneracy,
                   resolver=resolver, per_pos_limit=per_pos_limit,
                   resolver_limit=resolver_limit)

    # internal: built by wrappers
    @classmethod
    def _wrapper(cls, *, name: str, core_name: str, N: int = 29) -> CipherSpec:
        return cls(kind="wrapper", name=name, N=N, wrapper_core=core_name)


# ---------------------------------------------------------------------------
# UI KeySpec (front-door)
# ---------------------------------------------------------------------------
# This is the ONLY KeySpec in the project. It is a declarative, user-facing
# factory that spells intent (repeat, permutation, matrix, etc). Internally,
# the UI KeySpec resolves to concrete implementations provided by the
# rune_decrypter_prime/keyops/ package (MatrixKey, PermutationKeyOps, ...),
# via the keyops registry.
#
# IMPORTANT:
# - Do NOT define another KeySpec anywhere else (e.g., under keyops/).
# - The UI layer stays stable and friendly; keyops can evolve behind it.
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
        arr = np.asarray(list(stream), dtype=KEY_DTYPE).reshape(-1)
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
    def matrix(cls, *, n: int, A: int = 29) -> "KeySpec":
        """
        Square matrix key of size n×n over Z_A, flattened row-major.
        Key length implied downstream = n*n.
        """
        n = int(n)
        if n <= 1:
            raise ValueError("KeySpec.matrix requires n >= 2")
        return cls(plan="matrix", params={"n": n, "A": int(A)})



    @classmethod
    def affine(cls, *, A: int = 29) -> KeySpec:
        return cls(plan="affine", params={"A": int(A)})

    @classmethod
    def scalar(cls, *, max_val: int | None = None) -> "KeySpec":
        """
        Scalar key (length 1). `max_val` is optional UI metadata for UIs/prompts;
        the core only cares that key_length == 1.
        """
        p = {}
        if max_val is not None:
            p["max_val"] = int(max_val)
        return cls(plan="scalar", params=p)


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


# ------------------------------- SolverSpec -------------------------------
@dataclass
class SolverSpec:
    """
    Search/solver budget. Maps to core SolverConfig unchanged.
    """
    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    seed: Optional[int] = None



    @classmethod
    def beam(cls, **params: Any) -> "SolverSpec":
        """
        Beam search (UI builder).
        Friendly keys accepted: width -> beam_width.
        Canonicalised keys passed downstream: beam_width (int), plus any passthroughs.
        Plateau: use plateau_rounds / plateau_min_delta (patience_* aliases accepted).
        """
        from rune_decrypter_prime.api._resolve import resolve_optimizer_aliases as _resolve_opt
        seed = params.pop("seed", None)
        canon: Dict[str, Any] = _resolve_opt("beam", dict(params))
        return cls(name="beam", params=canon, seed=seed)

    @classmethod
    def ga(cls, **params: Any) -> "SolverSpec":
        """
        Genetic algorithm (UI builder).
        Friendly keys accepted: population/pop -> pop_size; iterations/iters -> generations (pure GA).
        Plateau: use plateau_rounds / plateau_min_delta (plateau_gens, patience_* aliases accepted).
        Canonicalised keys passed downstream: pop_size, generations.
        """
        from rune_decrypter_prime.api._resolve import resolve_optimizer_aliases as _resolve_opt
        seed = params.pop("seed", None)
        canon: Dict[str, Any] = _resolve_opt("ga", dict(params))
        return cls(name="ga", params=canon, seed=seed)

    @classmethod
    def sa(cls, **params: Any) -> "SolverSpec":
        """
        Simulated annealing (UI builder).
        Friendly keys accepted: iters/iterations -> sa_iters.
        Plateau: use plateau_rounds / plateau_min_delta (patience_* aliases accepted).
        Canonicalised keys passed downstream: iters (+ T0, Tmin, cool if provided).
        """
        from rune_decrypter_prime.api._resolve import resolve_optimizer_aliases as _resolve_opt
        seed = params.pop("seed", None)
        canon: Dict[str, Any] = _resolve_opt("sa", dict(params))
        return cls(name="sa", params=canon, seed=seed)

    @classmethod
    def hybrid(cls, **params: Any) -> "SolverSpec":
        """
        Hybrid optimiser (UI builder) = optional Beam warm start + GA explore + SA polish.

        Policy (to remove ambiguity):
          - GA MUST use 'generations'/'gens'. (In hybrid only, GA will not consume 'iterations'/'iters'.)
          - SA uses 'sa_iters' OR friendly 'iters'/'iterations'.

        Canonicalised keys passed downstream:
          - beam_width (if any), pop_size/generations (GA), sa_iters (+ SA temps/cooling), plus passthroughs.
        """
        from rune_decrypter_prime.api._resolve import resolve_optimizer_aliases as _resolve_opt

        def _coerce_mapping(value: Any) -> Dict[str, Any]:
            if value is None:
                return {}
            if isinstance(value, dict):
                return dict(value)
            if dataclasses.is_dataclass(value):
                return dataclasses.asdict(value)
            return dict(getattr(value, "__dict__", {}))

        def _pop_prefixed(src: Dict[str, Any], prefix: str) -> Dict[str, Any]:
            picked: Dict[str, Any] = {}
            for key in list(src.keys()):
                if key.startswith(prefix):
                    picked[key[len(prefix):]] = src.pop(key)
            return picked

        # Extract nested GA/SA configs before normalising top-level keys
        ga_inline = _pop_prefixed(params, "ga_")
        sa_inline = _pop_prefixed(params, "sa_")
        ga_raw = params.pop("ga", None)
        sa_raw = params.pop("sa", None)
        seed = params.pop("seed", None)

        # Canonicalize ONLY the hybrid top-level keys (beam knobs, passthroughs).
        canon_top: Dict[str, Any] = _resolve_opt("hybrid", dict(params))

        def _merge_ga_payload() -> Dict[str, Any]:
            payload: Dict[str, Any] = {}
            for source in (ga_raw, ga_inline):
                data = _coerce_mapping(source)
                payload.update(data)
            return payload

        def _merge_sa_payload() -> Dict[str, Any]:
            payload: Dict[str, Any] = {}
            for source in (sa_raw, sa_inline):
                data = _coerce_mapping(source)
                payload.update(data)
            return payload

        ga_payload = _merge_ga_payload()
        if ga_payload:
            canon_ga = _resolve_opt("ga", ga_payload)
            canon_top["ga"] = dict(canon_ga)

        sa_payload = _merge_sa_payload()
        if sa_payload:
            canon_sa = _resolve_opt("sa", sa_payload)
            canon_top["sa"] = dict(canon_sa)

        return cls(name="hybrid", params=canon_top, seed=seed)
