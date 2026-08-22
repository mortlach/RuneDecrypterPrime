from __future__ import annotations
import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Literal, Any, Dict
import json
from numbers import Integral

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

def _strict_int(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{field} must be an integer, not bool")
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text and (text.isdigit() or (text[0] in "+-" and text[1:].isdigit())):
            return int(text)
    raise TypeError(f"{field} must be an integer")


def _json_safe(value: Any, field: str) -> Any:
    """Return a JSON-portable copy or fail without stringifying unknown objects."""
    try:
        encoded = json.dumps(value)
        return json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field} must contain only JSON-portable values") from exc


def _strict_device(value: Any) -> Device:
    if isinstance(value, Device):
        return value
    if not isinstance(value, str):
        raise TypeError("CipherSpec.device must be Device or a supported device string")
    key = value.strip().lower()
    if key in {"cpu", "torch"}:
        return Device.CPU
    if key == "gpu" or key.startswith("cuda"):
        return Device.CUDA
    raise ValueError(f"unsupported CipherSpec.device {value!r}")


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
    device: str | Device | None = Device.CPU

    # misc
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("CipherSpec.name must be a non-empty string")
        self.name = self.name.strip()
        self.N = _strict_int(self.N, "CipherSpec.N")
        if self.N <= 1:
            raise ValueError("CipherSpec.N must be >= 2")

        self.kind = str(self.kind or "").strip().lower()
        if self.kind not in {"wrapper", "user_map2", "user_map3", "lookup"}:
            raise ValueError(f"unsupported CipherSpec.kind {self.kind!r}")
        self.degeneracy = str(self.degeneracy or "").strip().lower()
        if self.degeneracy not in {"allow", "forbid"}:
            raise ValueError("CipherSpec.degeneracy must be 'allow' or 'forbid'")
        self.resolver = str(self.resolver or "").strip().lower()
        if self.resolver not in {"first", "expand_beam"}:
            raise ValueError("CipherSpec.resolver must be 'first' or 'expand_beam'")
        self.per_pos_limit = _strict_int(self.per_pos_limit, "CipherSpec.per_pos_limit")
        self.resolver_limit = _strict_int(self.resolver_limit, "CipherSpec.resolver_limit")
        if self.per_pos_limit <= 0 or self.resolver_limit <= 0:
            raise ValueError("CipherSpec per_pos_limit/resolver_limit must be positive")
        if not isinstance(self.extra, dict):
            raise TypeError("CipherSpec.extra must be a dict")
        self.extra = dict(self.extra)
        if self.device is not None:
            self.device = _strict_device(self.device)

        if self.kind == "wrapper":
            if not isinstance(self.wrapper_core, str) or not self.wrapper_core.strip():
                raise ValueError("wrapper CipherSpec requires a non-empty wrapper_core")
            if self.function is not None or self.table is not None:
                raise ValueError("wrapper CipherSpec cannot define function/table")
            self.wrapper_core = self.wrapper_core.strip()
        elif self.kind == "user_map2":
            if not callable(self.function):
                raise TypeError("user_map2 CipherSpec requires callable function(pt, k)")
            if self.table is not None or self.wrapper_core is not None:
                raise ValueError("user_map2 CipherSpec cannot define table/wrapper_core")
        elif self.kind == "user_map3":
            if not callable(self.function):
                raise TypeError("user_map3 CipherSpec requires callable function(pt, k1, k2)")
            if self.table is not None or self.wrapper_core is not None:
                raise ValueError("user_map3 CipherSpec cannot define table/wrapper_core")
        elif self.kind == "lookup":
            if self.table is None:
                raise ValueError("lookup CipherSpec requires a table")
            if self.function is not None or self.wrapper_core is not None:
                raise ValueError("lookup CipherSpec cannot define function/wrapper_core")
            table = np.asarray(self.table, dtype=object)
            if table.ndim != 2 or int(table.shape[0]) != self.N:
                raise ValueError(
                    f"lookup CipherSpec table must have N rows; got shape {table.shape}, "
                    f"expected ({self.N}, ?)"
                )

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

    @classmethod
    def periodic_substitution(
        cls,
        *,
        period: int,
        alphabet_size: int = 29,
        name: Optional[str] = None,
    ) -> CipherSpec:
        p = _strict_int(period, "CipherSpec.periodic_substitution.period")
        if p <= 0:
            raise ValueError("period must be >= 1")
        A = _strict_int(alphabet_size, "CipherSpec.periodic_substitution.alphabet_size")
        if A <= 0:
            raise ValueError("alphabet_size must be >= 1")
        spec = cls._wrapper(name=name or "periodic_substitution", core_name="periodic_substitution", N=A)
        spec.extra["period"] = p
        spec.extra["alphabet_size"] = A
        return spec

    @classmethod
    def periodic_columnar(
        cls,
        *,
        period: int,
        columns: int,
        alphabet_size: int = 29,
        order: str = "sub_then_col",
        name: Optional[str] = None,
    ) -> CipherSpec:
        p = _strict_int(period, "CipherSpec.periodic_columnar.period")
        c = _strict_int(columns, "CipherSpec.periodic_columnar.columns")
        if p <= 0:
            raise ValueError("period must be >= 1")
        if c <= 0:
            raise ValueError("columns must be >= 1")
        A = _strict_int(alphabet_size, "CipherSpec.periodic_columnar.alphabet_size")
        if A <= 0:
            raise ValueError("alphabet_size must be >= 1")
        spec = cls._wrapper(name=name or "periodic_columnar", core_name="periodic_columnar", N=A)
        spec.extra["period"] = p
        spec.extra["columns"] = c
        spec.extra["alphabet_size"] = A
        spec.extra["order"] = str(order or "sub_then_col")
        return spec


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
      - "periodic_structured": periodic substitution blocks with optional columnar tail
    """
    plan: str
    params: Dict[str, Any] = field(default_factory=dict)
    _align_offset: Optional[Union[int, Tuple[str, int, int]]] = None  # e.g., ("search",-3,3)

    def __post_init__(self) -> None:
        self.plan = str(self.plan or "").strip().lower()
        allowed = {
            "repeat", "repeat_range", "block", "otp", "const", "keystream",
            "perm", "periodic_structured", "matrix2x2", "matrix", "affine", "scalar",
        }
        if self.plan not in allowed:
            raise ValueError(f"unsupported KeySpec.plan {self.plan!r}")
        if not isinstance(self.params, dict):
            raise TypeError("KeySpec.params must be a dict")
        self.params = dict(self.params)
        allowed_params = {
            "repeat": {"len"},
            "repeat_range": {"min", "max"},
            "block": {"size", "pattern"},
            "otp": {"stream"},
            "const": {"value"},
            "keystream": {"fn", "params"},
            "perm": {"len"},
            "periodic_structured": {"period", "alphabet_size", "columns"},
            "matrix2x2": {"A"},
            "matrix": {"n", "A"},
            "affine": {"A"},
            "scalar": {"max_val"},
        }[self.plan]
        unknown = sorted(set(self.params) - allowed_params)
        if unknown:
            raise ValueError(f"KeySpec.{self.plan} does not accept parameter(s): {unknown}")

        if self.plan in {"repeat", "perm"}:
            length = _strict_int(self.params.get("len"), f"KeySpec.{self.plan}.len")
            if length <= 0:
                raise ValueError(f"KeySpec.{self.plan} requires len > 0")
            self.params = {"len": length}
        elif self.plan == "repeat_range":
            low = _strict_int(self.params.get("min"), "KeySpec.repeat_range.min")
            high = _strict_int(self.params.get("max"), "KeySpec.repeat_range.max")
            if low <= 0 or high < low:
                raise ValueError("KeySpec.repeat_range requires 0 < min <= max")
            self.params = {"min": low, "max": high}
        elif self.plan == "block":
            size = _strict_int(self.params.get("size"), "KeySpec.block.size")
            if size <= 0:
                raise ValueError("KeySpec.block requires size > 0")
            pattern = self.params.get("pattern")
            if pattern is not None:
                pattern = _json_safe(pattern, "KeySpec.block.pattern")
            self.params = {"size": size, "pattern": pattern}
        elif self.plan == "otp":
            stream = self.params.get("stream")
            if isinstance(stream, (str, bytes)) or stream is None:
                raise TypeError("KeySpec.otp stream must be a sequence of integers")
            values = [_strict_int(value, "KeySpec.otp.stream") for value in stream]
            if not values:
                raise ValueError("KeySpec.otp requires a non-empty stream")
            self.params = {"stream": values}
        elif self.plan == "const":
            self.params = {"value": _strict_int(self.params.get("value"), "KeySpec.const.value")}
        elif self.plan == "keystream":
            fn = self.params.get("fn")
            if not callable(fn):
                raise TypeError("KeySpec.keystream requires callable fn")
            runtime_params = self.params.get("params", {})
            if not isinstance(runtime_params, dict):
                raise TypeError("KeySpec.keystream params must be a dict")
            _json_safe(runtime_params, "KeySpec.keystream params")
            self.params = {"fn": fn, "params": dict(runtime_params)}
        elif self.plan == "periodic_structured":
            period = _strict_int(self.params.get("period"), "KeySpec.periodic_structured.period")
            alphabet = _strict_int(self.params.get("alphabet_size", 29), "KeySpec.periodic_structured.alphabet_size")
            if period <= 0 or alphabet <= 0:
                raise ValueError("periodic_structured requires period/alphabet_size >= 1")
            out = {"period": period, "alphabet_size": alphabet}
            if self.params.get("columns") is not None:
                columns = _strict_int(self.params.get("columns"), "KeySpec.periodic_structured.columns")
                if columns <= 0:
                    raise ValueError("periodic_structured columns must be >= 1")
                out["columns"] = columns
            self.params = out
        elif self.plan in {"matrix2x2", "affine"}:
            alphabet = _strict_int(self.params.get("A", 29), f"KeySpec.{self.plan}.A")
            if alphabet <= 1:
                raise ValueError(f"KeySpec.{self.plan} requires A >= 2")
            self.params = {"A": alphabet}
        elif self.plan == "matrix":
            n = _strict_int(self.params.get("n"), "KeySpec.matrix.n")
            alphabet = _strict_int(self.params.get("A", 29), "KeySpec.matrix.A")
            if n < 2 or alphabet <= 1:
                raise ValueError("KeySpec.matrix requires n >= 2 and A >= 2")
            self.params = {"n": n, "A": alphabet}
        elif self.plan == "scalar":
            if self.params.get("max_val") is None:
                self.params = {}
            else:
                max_val = _strict_int(self.params.get("max_val"), "KeySpec.scalar.max_val")
                if max_val <= 0:
                    raise ValueError("KeySpec.scalar max_val must be > 0")
                self.params = {"max_val": max_val}

        if self._align_offset is not None:
            raw_align = self._align_offset
            self._align_offset = None
            self.align(offset=raw_align)

    # --- factories ---
    @classmethod
    def repeat(cls, *, len: int) -> KeySpec:
        length = _strict_int(len, "KeySpec.repeat.len")
        if length <= 0:
            raise ValueError("KeySpec.repeat requires len > 0")
        return cls(plan="repeat", params={"len": length})

    @classmethod
    def repeat_range(cls, *, min: int, max: int) -> KeySpec:
        return cls(plan="repeat_range", params={
            "min": _strict_int(min, "KeySpec.repeat_range.min"),
            "max": _strict_int(max, "KeySpec.repeat_range.max"),
        })

    @classmethod
    def block(cls, *, size: int, pattern=None) -> KeySpec:
        return cls(plan="block", params={"size": _strict_int(size, "KeySpec.block.size"), "pattern": pattern})

    @classmethod
    def otp(cls, *, stream: Iterable[int]) -> KeySpec:
        values = [_strict_int(value, "KeySpec.otp.stream") for value in stream]
        if not values:
            raise ValueError("KeySpec.otp requires a non-empty stream")
        arr = np.asarray(values, dtype=KEY_DTYPE).reshape(-1)
        return cls(plan="otp", params={"stream": arr.tolist()})

    @classmethod
    def const(cls, *, value: int) -> KeySpec:
        return cls(plan="const", params={"value": _strict_int(value, "KeySpec.const.value")})

    @classmethod
    def keystream(cls, *, fn: Callable[..., np.ndarray], params: Optional[Dict[str, Any]] = None) -> KeySpec:
        return cls(plan="keystream", params={"fn": fn, "params": params or {}})

    @classmethod
    def permutation(cls, *, len: int) -> KeySpec:
        length = _strict_int(len, "KeySpec.permutation.len")
        if length <= 0:
            raise ValueError("KeySpec.permutation requires len > 0")
        return cls(plan="perm", params={"len": length})

    @classmethod
    def periodic_structured(
        cls,
        *,
        period: int,
        alphabet_size: int = 29,
        columns: int | None = None,
    ) -> "KeySpec":
        p = _strict_int(period, "KeySpec.periodic_structured.period")
        if p <= 0:
            raise ValueError("period must be >= 1")
        A = _strict_int(alphabet_size, "KeySpec.periodic_structured.alphabet_size")
        if A <= 0:
            raise ValueError("alphabet_size must be >= 1")
        params: Dict[str, Any] = {"period": p, "alphabet_size": A}
        if columns is not None:
            c = _strict_int(columns, "KeySpec.periodic_structured.columns")
            if c <= 0:
                raise ValueError("columns must be >= 1")
            params["columns"] = c
        return cls(plan="periodic_structured", params=params)

    @classmethod
    def periodic_substitution(
        cls,
        *,
        period: int,
        alphabet_size: int = 29,
    ) -> "KeySpec":
        return cls.periodic_structured(period=period, alphabet_size=alphabet_size, columns=None)

    @classmethod
    def periodic_columnar(
        cls,
        *,
        period: int,
        columns: int,
        alphabet_size: int = 29,
    ) -> "KeySpec":
        return cls.periodic_structured(period=period, columns=columns, alphabet_size=alphabet_size)

    @classmethod
    def matrix2x2(cls, *, A: int = 29) -> KeySpec:
        return cls(plan="matrix2x2", params={"A": _strict_int(A, "KeySpec.matrix2x2.A")})

    @classmethod
    def matrix(cls, *, n: int, A: int = 29) -> "KeySpec":
        """
        Square matrix key of size n×n over Z_A, flattened row-major.
        Key length implied downstream = n*n.
        """
        n = _strict_int(n, "KeySpec.matrix.n")
        if n <= 1:
            raise ValueError("KeySpec.matrix requires n >= 2")
        return cls(plan="matrix", params={"n": n, "A": _strict_int(A, "KeySpec.matrix.A")})



    @classmethod
    def affine(cls, *, A: int = 29) -> KeySpec:
        return cls(plan="affine", params={"A": _strict_int(A, "KeySpec.affine.A")})

    @classmethod
    def scalar(cls, *, max_val: int | None = None) -> "KeySpec":
        """
        Scalar key (length 1). `max_val` is optional UI metadata for UIs/prompts;
        the core only cares that key_length == 1.
        """
        p = {}
        if max_val is not None:
            p["max_val"] = _strict_int(max_val, "KeySpec.scalar.max_val")
        return cls(plan="scalar", params=p)


    # --- modifiers ---
    def align(self, *, offset: Union[int, Tuple[str, int, int]]) -> KeySpec:
        if isinstance(offset, bool):
            raise TypeError("KeySpec.align offset cannot be bool")
        if isinstance(offset, int):
            self._align_offset = int(offset)
            return self
        if not isinstance(offset, (tuple, list)) or len(offset) != 3:
            raise TypeError("KeySpec.align offset must be an integer or ('search', min, max)")
        mode, low, high = offset
        if str(mode).strip().lower() != "search":
            raise ValueError("KeySpec.align tuple mode must be 'search'")
        low_i = _strict_int(low, "KeySpec.align.min")
        high_i = _strict_int(high, "KeySpec.align.max")
        if low_i > high_i:
            raise ValueError("KeySpec.align requires min <= max")
        self._align_offset = ("search", low_i, high_i)
        return self

    # --- utils ---
    def period_hint(self) -> Optional[int]:
        if self.plan == "repeat":
            return int(self.params.get("len", 0)) or None
        return None

    def to_telemetry(self) -> Dict[str, Any]:
        t: Dict[str, Any] = {"plan": self.plan}
        if self.plan == "keystream":
            fn = self.params["fn"]
            t["params"] = _json_safe(self.params.get("params", {}), "KeySpec.keystream params")
            t["runtime_callable"] = {
                "module": str(getattr(fn, "__module__", "") or ""),
                "qualname": str(getattr(fn, "__qualname__", getattr(fn, "__name__", type(fn).__name__))),
            }
        else:
            for key, value in self.params.items():
                if key == "stream":
                    continue
                t[key] = _json_safe(value, f"KeySpec.{self.plan}.{key}")
        if self._align_offset is not None:
            t["align"] = _json_safe(self._align_offset, "KeySpec.align")
        return _json_safe(t, "KeySpec telemetry")


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
    def two_period_cribs(
        cls,
        *,
        fixed_cribs: Sequence[tuple[str, int]] = (),
        candidate_words: Sequence[str] = (),
        candidate_positions: Optional[Dict[str, Sequence[int]]] = None,
        starts: int = 96,
        seed: Optional[int] = None,
    ) -> "SolverSpec":
        """Solve an additive two-period Vigenere overlay from complete-word cribs."""
        from rune_decrypter_prime.api.two_period_cribs import build_two_period_cribs_spec

        return build_two_period_cribs_spec(
            fixed_cribs=fixed_cribs,
            candidate_words=candidate_words,
            candidate_positions=candidate_positions,
            starts=starts,
            seed=seed,
        )



    @classmethod
    def beam(cls, **params: Any) -> "SolverSpec":
        """
        Beam search (UI builder).
        Friendly keys accepted: width -> beam_width.
        Canonicalised keys passed downstream: beam_width and restarts, plus any passthroughs.
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

    @classmethod
    def kaeding(cls, **params: Any) -> "SolverSpec":
        """
        Kaeding-style structured solver (periodic structured keys).
        Canonicalised keys passed downstream: steps, restarts, inner_batch, slip/col params.
        """
        from rune_decrypter_prime.api._resolve import resolve_optimizer_aliases as _resolve_opt
        seed = params.pop("seed", None)
        canon: Dict[str, Any] = _resolve_opt("kaeding", dict(params))
        return cls(name="kaeding", params=canon, seed=seed)
