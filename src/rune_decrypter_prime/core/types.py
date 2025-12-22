"""Strict enums and dataclasses shared across the core/engine pipeline."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional

import numpy as np

# Central dtype for key material (needs >255 for bigram/permutation keys)
KEY_DTYPE = np.int16

class Direction(Enum):
    """Canonical text-encoding direction for the pipeline.
    Core uses this Enum only (never raw strings). When serialized to JSON,
    use .value to emit 'ltr' or 'rtl' for readability.
    """
    LTR = "ltr"
    RTL = "rtl"

class Device(Enum):
    """Execution device. Core can branch on this; API remains forgiving."""
    CPU = "cpu"
    CUDA = "cuda"

class ScorerImpl(Enum):
    """Execution device. Core uses this API remains forgiving."""
    NUMPY = "numpy"
    TORCH = "torch"
    UNIFIED = "unified"
    AUTO = "auto"


class ScorerName(Enum):
    """Canonical scorer families recognised by the config layer."""
    RUNE = "rune"

class SolverName(Enum):
    """Optimizer device. Core uses this API remains forgiving."""
    BEAM  = "beam"
    GA  = "ga"
    SA  = "sa"
    HYBRID  = "hybrid"


class CipherKind(Enum):
    """Canonical cipher family for strict branching in the core.
    UI may keep string fields, but the core uses this Enum only.
    """
    WRAPPER = "wrapper"      # Named core cipher exposed via wrappers/registry
    USER_MAP2 = "user_map2"  # ct = f(pt, k)
    USER_MAP3 = "user_map3"  # ct = f(pt, k1, k2)
    LOOKUP = "lookup"        # ct = table[pt, k] or similar

class KeyKind(Enum):
    """Canonical key plan for strict branching in the core.
    Avoid magic strings in engine/cipher builders.
    """
    REPEAT = "repeat"        # periodic stream of length K
    OTP = "otp"              # explicit stream
    CONST = "const"          # broadcast constant value
    PERM = "perm"            # permutation key (bijective)
    MATRIX2X2 = "matrix2x2"  # 2×2 matrix (e.g., Hill-2)
    MATRIX = "matrix"        # general matrix
    AFFINE = "affine"        # (a, b) pair when used as key parts
    SCALAR = "scalar"        # single int modulo N
    BLOCK = "block"          # structured/block key (reserved)
    KEYSTREAM = "keystream"  # pre-generated stream (alias of OTP at core level)

class KeyOpsFamily(Enum):
    """KeyOps families recognised by the core/keyops registry."""
    PERMUTATION = "permutation"
    VECTOR = "vector"
    AFFINE = "affine"
    MATRIX = "matrix"

@dataclass(frozen=True)
class PipelineCfg:
    """Strict pipeline config carried inside core."""
    text_encoding_direction: Direction = Direction.LTR
    # Core expects a true permutation over ciphertext token indices or None.
    # API normalizes various user formats to this canonical list[int] in PR2.
    text_permutation: Optional[list[int]] = None

@dataclass(frozen=True)
class SolveCfg:
    """Strict top-level config for the solver engine (core-facing only)."""
    seed: int = 42
    device: Device = Device.CPU
    telemetry_on: bool = True

    # Budgets/patience standardization (wired in PR12; defined now for clarity)
    eval_budget: int = 10_000
    time_budget_s: float = 10.0
    patience_steps: int = 250
    improvement_threshold: float = 0.0

    # Pipeline (direction & permutation)
    pipeline: PipelineCfg = field(default_factory=PipelineCfg)


def _coerce_enum_value(enum_cls, value, *, aliases=None, param_name="value"):
    if isinstance(value, enum_cls):
        return value
    if value is None:
        raise TypeError(f"{param_name} must be {enum_cls.__name__}, got None")
    aliases = aliases or {}
    key = str(value).strip().lower()
    target = aliases.get(key)
    if target is not None:
        if isinstance(target, enum_cls):
            return target
        key = str(target).strip().lower()
    for member in enum_cls:
        if member.value == key:
            return member
    raise ValueError(f"Unknown {param_name}: {value!r}")


def ensure_direction(value) -> Direction:
    return _coerce_enum_value(Direction, value, aliases={
        "forward": Direction.LTR,
        "fwd": Direction.LTR,
        "reverse": Direction.RTL,
        "rev": Direction.RTL,
    }, param_name="direction")


def ensure_device(value) -> Device:
    if isinstance(value, Device):
        return value
    if value is None:
        raise TypeError("device must be Device or str, got None")
    key = str(value).strip().lower()
    if key.startswith("cuda") or key in {"gpu"}:
        return Device.CUDA
    if key == "torch":
        return Device.CPU
    return Device.CPU


def ensure_solver_name(value) -> SolverName:
    return _coerce_enum_value(SolverName, value, param_name="solver kind")


def ensure_scorer_name(value) -> ScorerName:
    return _coerce_enum_value(ScorerName, value, param_name="scorer name")


def ensure_scorer_impl(value) -> ScorerImpl:
    return _coerce_enum_value(ScorerImpl, value, param_name="scorer impl")


def ensure_keyops_family(value) -> KeyOpsFamily:
    return _coerce_enum_value(KeyOpsFamily, value, aliases={
        "perm": KeyOpsFamily.PERMUTATION,
    }, param_name="keyops family")



def ensure_cipher_kind(value) -> CipherKind:
    return _coerce_enum_value(CipherKind, value, param_name="cipher kind")


def ensure_key_kind(value) -> KeyKind:
    return _coerce_enum_value(KeyKind, value, param_name="key kind")



def parse_optimizer_kind(val) -> SolverName:
    return ensure_solver_name(val)

def parse_device(val) -> Device:
    if val is None:
        return Device.CPU
    return ensure_device(val)



from enum import Enum
from dataclasses import dataclass
from typing import Optional

class SeMode(Enum):
    NOSE = "nose"
    WISE = "wise"

class Channel(Enum):
    CHAR = "char"
    WLI = "wli"

class ObjectiveFamily(Enum):
    PCT = "pct"
    AVG = "avg"
    ENERGY = "energy"     # kept as explicit alias
    NEGLOGP = "neglogp"   # scalar legacy

class Stat(Enum):
    LOGP = "logp"
    ZSUM = "zsum"
    MADSUM = "madsum"

@dataclass(frozen=True)
class ObjectiveSpec:
    family: ObjectiveFamily
    stat: Optional[Stat] = None     # None for NEGLOGP
    win: Optional[int] = None       # required for PCT/ENERGY families


def ensure_se_mode(value) -> SeMode:
    return _coerce_enum_value(SeMode, value, param_name="se_mode")


def ensure_objective_family(value) -> ObjectiveFamily:
    return _coerce_enum_value(ObjectiveFamily, value, param_name="objective family")


def ensure_stat(value) -> Stat:
    return _coerce_enum_value(Stat, value, param_name="stat")
