# ============================================================
# rune_decrypter_prime/ciphers/scheduled_stream_lookup_cipher.py
# Scheduled two-stream lookup cipher for compact RDP experiments.
# ============================================================
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping as AbcMapping, Sequence as AbcSequence
from numbers import Integral
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence, Tuple

import numpy as np

from rune_decrypter_prime.ciphers.ciphers_pipeline import CipherPipelineMixin
from rune_decrypter_prime.ciphers.dev.base_keyed_cipher import KeyedCipherBase
from rune_decrypter_prime.ciphers.registry import register_cipher
from rune_decrypter_prime.core.types import Device, Direction, KeyOpsFamily, ensure_device, ensure_direction

ArrayInt = np.ndarray

# ---------------------------------------------------------------------------
# Private scheduled-stream helpers.
# These stay inside the cipher module so V1 does not add a global RDP concept.
# ---------------------------------------------------------------------------
_ACTIVE_NONE = 0
_ACTIVE_A = 1
_ACTIVE_B = 2
_ACTIVE_AB = 3
_VALID_ACTIVE_STATES = frozenset({_ACTIVE_NONE, _ACTIVE_A, _ACTIVE_B, _ACTIVE_AB})
_ACTIVE_STATE_LABELS = {
    _ACTIVE_NONE: "none",
    _ACTIVE_A: "A",
    _ACTIVE_B: "B",
    _ACTIVE_AB: "A+B",
}

_KNOWN_STREAM_KINDS = frozenset({"primes", "fixed"})
_STREAM_KIND_ALIASES = {
    "prime": "primes",
    # Public/tutorial language may say "sequence"; runtime treats this as a
    # fixed known sequence stream. It is not solved key material.
    "sequence": "fixed",
    "known_sequence": "fixed",
    "fixed_sequence": "fixed",
}
_VALID_STREAM_KINDS = frozenset({"periodic", *_KNOWN_STREAM_KINDS})

_VALID_STREAM_DIRECTIONS = frozenset({"forward", "backward"})
_VALID_STREAM_ANCHORS = frozenset({"start", "end"})
_VALID_STREAM_ADVANCE_MODES = frozenset({"core"})

_VALID_SCHEDULES = frozenset({"overlay", "alternating", "staggered_overlay", "ragged_overlap", "mask"})
_SCHEDULES_REQUIRING_TWO_STREAMS = frozenset({"alternating", "staggered_overlay", "ragged_overlap"})
_VALID_OPERATIONS = frozenset({"add", "add_sub", "sub_add", "beaufort_sum", "xor_mod", "lookup"})
_VALID_DEGENERACY_MODES = frozenset({"forbid", "allow"})
_OPERATIONS_REQUIRING_DEGENERACY_ALLOW = frozenset({"xor_mod", "lookup"})

def normalise_name(value: Any, default: str) -> str:
    """Normalise small user-facing enum names.

    Examples: ``"Two-Period"`` and ``"Two Period"`` both become
    ``"two_period"``.  Empty strings fall back to the supplied default rather
    than becoming a silent invalid value.
    """
    if value is None:
        return default
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    return text or default


def normalise_stream_kind(value: Any) -> str:
    """Return the canonical stream kind name."""
    kind = normalise_name(value, "periodic")
    return _STREAM_KIND_ALIASES.get(kind, kind)


def normalise_stream_direction(value: Any) -> str:
    """Return a valid V1 stream direction."""
    direction = normalise_name(value, "forward")
    if direction not in _VALID_STREAM_DIRECTIONS:
        raise ValueError("stream direction must be 'forward' or 'backward'")
    return direction


def normalise_stream_anchor(value: Any) -> str:
    """Return a valid V1 stream anchor."""
    anchor = normalise_name(value, "start")
    if anchor not in _VALID_STREAM_ANCHORS:
        raise ValueError("stream anchor must be 'start' or 'end'")
    return anchor


def normalise_stream_advance(value: Any) -> str:
    """Return the V1 stream advance mode.

    The config field exists because raw/interrupter-aware stepping is a real LP
    ambiguity.  V1 intentionally supports only compact-core stepping so the
    first production interface stays small and testable.
    """
    advance = normalise_name(value, "core")
    if advance not in _VALID_STREAM_ADVANCE_MODES:
        raise ValueError("scheduled_stream_lookup V1 supports advance='core' only")
    return advance


def normalise_schedule(value: Any) -> str:
    """Return a valid schedule name, or raise a useful error."""
    schedule = normalise_name(value, "overlay")
    if schedule not in _VALID_SCHEDULES:
        raise ValueError(f"unknown scheduled_stream_lookup schedule {schedule!r}")
    return schedule


def normalise_operation(value: Any) -> str:
    """Return a valid operation name, or raise a useful error."""
    operation = normalise_name(value, "add")
    if operation not in _VALID_OPERATIONS:
        raise ValueError(f"unknown scheduled_stream_lookup operation {operation!r}")
    return operation


def normalise_degeneracy(value: Any) -> str:
    """Return a valid degeneracy mode, or raise a useful error."""
    degeneracy = normalise_name(value, "forbid")
    if degeneracy not in _VALID_DEGENERACY_MODES:
        raise ValueError("degeneracy must be 'forbid' or 'allow'")
    return degeneracy


def validate_operation_degeneracy(operation: Any, degeneracy: Any) -> tuple[str, str]:
    """Validate operation and degeneracy together.

    ``xor_mod`` and arbitrary ``lookup`` can be many-to-one.  Running them with
    deterministic first-candidate inverse would look like decryption succeeded
    while silently discarding alternatives, so V1 requires explicit
    ``degeneracy='allow'`` for those operations.
    """
    op = normalise_operation(operation)
    deg = normalise_degeneracy(degeneracy)
    if op in _OPERATIONS_REQUIRING_DEGENERACY_ALLOW and deg != "allow":
        raise ValueError(f"operation {op!r} requires degeneracy='allow'")
    return op, deg


def normalise_alternating_start(value: Any) -> str:
    """Return which stream starts an alternating schedule."""
    start = str("A" if value is None else value).strip().upper()
    if start not in {"A", "B"}:
        raise ValueError("alternating_start must be 'A' or 'B'")
    return start


def config_int(value: Any, name: str) -> int:
    """Return a real integer config value without silent truncation.

    Python's ``int(...)`` is too forgiving for production config: it turns
    ``True`` into ``1`` and ``3.7`` into ``3``.  That is useful at a REPL but
    dangerous in cipher configuration, where a wrong period or offset can look
    like a valid experiment.  We accept normal integers, NumPy integer scalars,
    and simple integer strings; everything else fails loudly.
    """
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer, not bool")
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text and (text.isdigit() or (text[0] in "+-" and text[1:].isdigit())):
            return int(text)
    raise ValueError(f"{name} must be an integer")


def config_bool(value: Any, name: str, *, default: bool = True) -> bool:
    """Return a boolean config value without Python truthiness surprises."""
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "yes", "1", "on"}:
            return True
        if text in {"false", "no", "0", "off"}:
            return False
    raise ValueError(f"{name} must be true or false")


def positive_int(value: Any, name: str, *, minimum: int = 1) -> int:
    """Validate a small positive integer config field."""
    out = config_int(value, name)
    if out < int(minimum):
        raise ValueError(f"{name} must be >= {int(minimum)}")
    return out


def optional_config_int(value: Any, name: str) -> int | None:
    """Return an optional integer config field.

    ``None`` means "use the natural default later".  Empty strings are rejected
    instead of being treated as zero, because an empty bound in a saved config is
    almost always a mistake.
    """
    if value is None:
        return None
    return config_int(value, name)


def validate_alphabet_size(value: Any, name: str = "alphabet_size") -> int:
    """Validate an alphabet size for scheduled-stream arithmetic.

    V1 is intended for the RDP/Liber Primus alphabet, normally mod 29.  We only
    require at least two symbols here.  Array dtype policy belongs to the core
    cipher/key pipeline, not to this small contract helper.
    """
    return positive_int(value, name, minimum=2)


def integer_symbol_list(values: Sequence[Any], name: str) -> list[int]:
    """Return a list of integer symbols and reject lossy coercions."""
    return [config_int(x, f"{name}[{i}]") for i, x in enumerate(values)]


def validate_symbol_range(values: Sequence[Any], *, alphabet_size: int, name: str) -> list[int]:
    """Return symbol values after checking they are already in the alphabet.

    Fixed streams are user-supplied key material, not arithmetic results.
    Rejecting out-of-range values avoids a hidden modulo operation in config.
    Generated prime streams are still reduced mod N at runtime because their
    definition is mathematical rather than a literal symbol list.
    """
    A = validate_alphabet_size(alphabet_size)
    out = integer_symbol_list(values, name)
    bad = [x for x in out if x < 0 or x >= A]
    if bad:
        raise ValueError(f"{name} contains values outside 0..{A - 1}: {bad}")
    return out


def schedule_requires_two_streams(schedule: str) -> bool:
    """True when a schedule is meaningless without stream B."""
    return normalise_schedule(schedule) in _SCHEDULES_REQUIRING_TWO_STREAMS


def active_state_from_label(label: Any) -> int:
    """Convert a readable mask segment label to an active-state integer."""
    text = str(label).strip().upper().replace(" ", "")
    values = {
        "NONE": _ACTIVE_NONE,
        "OFF": _ACTIVE_NONE,
        "0": _ACTIVE_NONE,
        "A": _ACTIVE_A,
        "1": _ACTIVE_A,
        "B": _ACTIVE_B,
        "2": _ACTIVE_B,
        "AB": _ACTIVE_AB,
        "A+B": _ACTIVE_AB,
        "B+A": _ACTIVE_AB,
        "3": _ACTIVE_AB,
    }
    if text not in values:
        raise ValueError("segment label must be 'A', 'B', 'AB', or 'none'")
    return values[text]


def validate_mask(mask: Sequence[Any], *, length: int | None = None) -> list[int]:
    """Return a plain int mask and reject invalid active-state values.

    The cipher runtime calls this before compiling a mask schedule.  Tests and
    tutorials call it too, so mask mistakes are caught before integration.
    """
    if mask is None:
        raise ValueError("mask schedule requires mask")
    out = [config_int(x, f"mask[{i}]") for i, x in enumerate(mask)]
    if length is not None:
        L = config_int(length, "length")
        if len(out) != L:
            raise ValueError(f"mask length {len(out)} does not match text length {L}")
    bad = sorted(set(out) - _VALID_ACTIVE_STATES)
    if bad:
        raise ValueError(f"mask contains invalid active-state values: {bad}")
    return out


def stream_dicts(streams: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return plain stream dicts and enforce the V1 one/two-stream boundary."""
    if streams is None:
        raise ValueError("scheduled_stream_lookup requires streams")
    if isinstance(streams, (str, bytes)) or not isinstance(streams, AbcSequence):
        raise ValueError("scheduled_stream_lookup streams must be a sequence of dict-like specs")
    out: list[dict[str, Any]] = []
    for idx, stream in enumerate(streams):
        if not isinstance(stream, AbcMapping):
            raise TypeError(f"stream specs must be dict-like; streams[{idx}] is {type(stream).__name__}")
        out.append(dict(stream))
    if not (1 <= len(out) <= 2):
        raise ValueError("scheduled_stream_lookup V1 supports one or two streams")
    return out


def default_streams_for_alias(
    alias: str,
    *,
    period_a: int | None = None,
    period_b: int | None = None,
    period: int | None = None,
    prime_offset: int = 0,
) -> list[dict[str, Any]]:
    """Build canonical stream specs for friendly aliases that need no literal sequence."""
    name = normalise_name(alias, "scheduled_stream_lookup")
    if name in {"two_period_vigenere", "two_period_arithmetic"}:
        if period_a is None or period_b is None:
            raise ValueError(f"{name} requires period_a and period_b")
        p_a = positive_int(period_a, "period_a")
        p_b = positive_int(period_b, "period_b")
        return [
            {"name": "A", "kind": "periodic", "period": p_a},
            {"name": "B", "kind": "periodic", "period": p_b},
        ]
    if name == "periodic_plus_primes":
        if period is None:
            raise ValueError("periodic_plus_primes requires period")
        p = positive_int(period, "period")
        return [
            {"name": "A", "kind": "periodic", "period": p},
            {"name": "B", "kind": "primes", "offset": config_int(prime_offset, "prime_offset")},
        ]
    raise ValueError("scheduled_stream_lookup requires explicit streams")


def validate_streams_v1(
    streams: Sequence[Mapping[str, Any]],
    *,
    alphabet_size: int | None = None,
) -> list[dict[str, Any]]:
    """Validate and canonicalise V1 stream specs.

    This is the single production contract for stream specs.  The cipher runtime
    may still convert fixed values into NumPy arrays, but it should not re-decide
    stream kind, period, direction, anchor, advance, or key length.
    """
    out = stream_dicts(streams)
    seen_names: set[str] = set()
    for idx, raw in enumerate(out):
        default_name = "A" if idx == 0 else "B"
        name = str(raw.get("name", default_name)).strip() or default_name
        name_key = name.lower()
        if name_key in seen_names:
            raise ValueError(f"duplicate stream name {name!r}")
        seen_names.add(name_key)
        raw["name"] = name

        kind = normalise_stream_kind(raw.get("kind"))
        raw["kind"] = kind
        raw["direction"] = normalise_stream_direction(raw.get("direction"))
        raw["anchor"] = normalise_stream_anchor(raw.get("anchor"))
        raw["advance"] = normalise_stream_advance(raw.get("advance"))
        raw["offset"] = config_int(raw.get("offset", 0), "offset")
        raw["repeat"] = config_bool(raw.get("repeat", True), "repeat", default=True)

        if kind == "periodic":
            raw["period"] = positive_int(raw.get("period", 0), "period")
        elif kind == "primes":
            # Generated stream; offset is already canonicalised above.
            pass
        elif kind == "fixed":
            values = raw.get("values")
            if values is None:
                raise ValueError("fixed streams require values")
            if isinstance(values, (str, bytes)):
                raise ValueError("fixed stream values must be a sequence of integer symbols, not text")
            if isinstance(values, np.ndarray):
                value_list = values.reshape(-1).tolist()
            elif isinstance(values, AbcSequence):
                value_list = list(values)
            else:
                raise ValueError("fixed stream values must be a sequence of integer symbols")
            if len(value_list) == 0:
                raise ValueError("fixed streams require at least one value")
            if alphabet_size is None:
                raw["values"] = integer_symbol_list(value_list, "fixed values")
            else:
                raw["values"] = validate_symbol_range(value_list, alphabet_size=alphabet_size, name="fixed values")
        else:
            raise ValueError(f"unknown stream kind {kind!r}")
    return out


def solved_key_length_for_streams(streams: Sequence[Mapping[str, Any]]) -> int:
    """Return the RDP unknown-key length for V1 scheduled streams."""
    total = 0
    for stream in validate_streams_v1(streams):
        if stream["kind"] == "periodic":
            total += int(stream["period"])
    return int(total)


def validate_schedule_for_streams(schedule: Any, streams: Sequence[Mapping[str, Any]]) -> str:
    """Validate a schedule against the available streams and return its name."""
    schedule_name = normalise_schedule(schedule)
    stream_list = validate_streams_v1(streams)
    if len(stream_list) < 2 and schedule_requires_two_streams(schedule_name):
        raise ValueError(f"{schedule_name} schedule requires two streams")
    return schedule_name


def validate_schedule_window(length: int, *, start: Any, end: Any, label: str) -> tuple[int, int]:
    """Validate an active window and return ``(start, end)`` as ints."""
    L = config_int(length, "length")
    if L < 0:
        raise ValueError("text length must be >= 0")
    lo = config_int(start, f"{label}_start")
    hi = L if end is None else config_int(end, f"{label}_end")
    if lo < 0 or hi < lo or hi > L:
        raise ValueError(f"bad {label} schedule window [{lo}, {hi}) for text length {L}")
    return lo, hi


def mask_from_segments(
    length: int,
    segments: Sequence[tuple[str, int, int | None]],
    *,
    allow_overwrite: bool = False,
) -> list[int]:
    """Build a readable V1 mask for simple segmented tutorial/test cases.

    ``segments`` is deliberately simple: ``("A", 0, 120)`` means stream A is
    active on ``[0, 120)``.  Use label ``"AB"`` for overlaid positions instead
    of relying on overlapping segments.  By default overlaps raise an error so
    examples stay explicit and reviewable.
    """
    L = config_int(length, "length")
    if L < 0:
        raise ValueError("length must be >= 0")
    if isinstance(segments, (str, bytes)) or not isinstance(segments, AbcSequence):
        raise ValueError("segments must be a sequence of (label, start, end) triples")
    overwrite = config_bool(allow_overwrite, "allow_overwrite", default=False)
    mask = [_ACTIVE_NONE] * L
    filled = [False] * L
    for item_index, segment in enumerate(segments):
        if not isinstance(segment, AbcSequence) or isinstance(segment, (str, bytes)) or len(segment) != 3:
            raise ValueError(f"segments[{item_index}] must be a (label, start, end) triple")
        label, start, end = segment
        state = active_state_from_label(label)
        lo, hi = validate_schedule_window(L, start=start, end=end, label=str(label))
        if not overwrite and any(filled[i] for i in range(lo, hi)):
            raise ValueError("mask segments overlap; use an explicit 'AB' segment or allow_overwrite=True")
        for i in range(lo, hi):
            mask[i] = state
            filled[i] = True
    return validate_mask(mask, length=L)


# ---------------------------------------------------------------------------
# Private lookup-table helper.
# ---------------------------------------------------------------------------
def _coerce_symbol(value: Any, *, alphabet_size: int, context: str) -> int:
    """Return one literal symbol without Python's lossy ``int(...)`` shortcuts."""
    if isinstance(value, bool):
        raise ValueError(f"{context} must be an integer symbol, not bool")
    if isinstance(value, Integral):
        out = int(value)
    elif isinstance(value, str):
        text = value.strip()
        if text and (text.isdigit() or (text[0] in "+-" and text[1:].isdigit())):
            out = int(text)
        else:
            raise ValueError(f"{context} must be an integer symbol")
    else:
        raise ValueError(f"{context} must be an integer symbol")
    if out < 0 or out >= int(alphabet_size):
        raise ValueError(f"{context} outside alphabet 0..{int(alphabet_size) - 1}: {out}")
    return out


def _value_list(value: Any, *, alphabet_size: int, context: str) -> list[int]:
    """Normalise a table/function result to literal ciphertext symbols.

    Lookup tables are explicit cipher definitions.  They should not silently
    truncate floats, accept booleans, or reduce out-of-range symbols modulo N.
    """
    if value is None:
        return []
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return [_coerce_symbol(value.item(), alphabet_size=alphabet_size, context=context)]
        return [
            _coerce_symbol(x, alphabet_size=alphabet_size, context=f"{context}[{i}]")
            for i, x in enumerate(value.reshape(-1).tolist())
        ]
    if isinstance(value, (list, tuple)):
        return [_coerce_symbol(x, alphabet_size=alphabet_size, context=f"{context}[{i}]") for i, x in enumerate(value)]
    return [_coerce_symbol(value, alphabet_size=alphabet_size, context=context)]


@dataclass(frozen=True)
class LookupTables:
    """
    Tiny lookup-table engine for maps of the form:

        ciphertext = table[plaintext, state]

    The inverse can be one-to-one or degenerate.  For degeneracy-aware solving,
    dec_all/dec_len keep all plaintext candidates for each (state, ciphertext).

    Arrays are stored as normal integer arrays.  This keeps the helper aligned
    with the rest of RDP's key/material handling and avoids a hidden local
    storage-width contract in this scheduled-stream feature.
    """

    alphabet_size: int
    state_size: int
    enc: ArrayInt          # shape (A, S): pt,state -> ct
    dec_first: ArrayInt    # shape (S, A): state,ct -> first pt
    dec_all: ArrayInt      # shape (S, A, A): state,ct,n -> pt
    dec_len: np.ndarray    # shape (S, A): number of candidates

    @classmethod
    def from_function(
        cls,
        *,
        alphabet_size: int,
        state_size: int,
        function: Callable[[int, int], int | Iterable[int] | None],
    ) -> "LookupTables":
        """Build lookup tables from a simple function(pt, state)."""
        A = int(alphabet_size)
        S = int(state_size)
        if A <= 1:
            raise ValueError("alphabet_size must be >= 2")
        if S <= 0:
            raise ValueError("state_size must be >= 1")

        enc = np.zeros((A, S), dtype=int)
        dec_len = np.zeros((S, A), dtype=int)
        dec_all = np.zeros((S, A, A), dtype=int)

        for state in range(S):
            seen = np.zeros((A, A), dtype=bool)  # ct, pt
            for pt in range(A):
                vals = _value_list(function(pt, state), alphabet_size=A, context=f"lookup[{pt},{state}]")
                if not vals:
                    enc[pt, state] = 0
                    continue
                enc[pt, state] = vals[0]
                for val in vals:
                    ct = int(val)
                    if seen[ct, pt]:
                        continue
                    idx = int(dec_len[state, ct])
                    if idx < A:
                        dec_all[state, ct, idx] = pt
                        dec_len[state, ct] = idx + 1
                    seen[ct, pt] = True

        dec_first = np.zeros((S, A), dtype=int)
        for state in range(S):
            for ct in range(A):
                if dec_len[state, ct] > 0:
                    dec_first[state, ct] = dec_all[state, ct, 0]

        return cls(A, S, enc, dec_first, dec_all, dec_len)

    @classmethod
    def from_table(
        cls,
        *,
        alphabet_size: int,
        state_size: int,
        table: Any,
    ) -> "LookupTables":
        """Build lookup tables from table[pt, state]. Entries may be int/list/None."""
        A = int(alphabet_size)
        S = int(state_size)
        T = np.asarray(table, dtype=object)
        if T.shape != (A, S):
            raise ValueError(f"lookup table must have shape ({A}, {S}); got {T.shape}")
        return cls.from_function(alphabet_size=A, state_size=S, function=lambda pt, state: T[pt, state])

    def encrypt_first(self, plaintext: ArrayInt, states: np.ndarray) -> ArrayInt:
        """Vectorised encryption using the first ciphertext listed for a mapping."""
        pt = np.asarray(plaintext, dtype=int)
        st = np.asarray(states, dtype=int)
        return self.enc[pt, st].astype(int, copy=False)

    def decrypt_first_symbol(self, ciphertext: ArrayInt, states: np.ndarray) -> ArrayInt:
        """Vectorised deterministic first-inverse decryption."""
        ct = np.asarray(ciphertext, dtype=int)
        st = np.asarray(states, dtype=int)
        return self.dec_first[st, ct].astype(int, copy=False)

    def candidates_for_states(
        self,
        *,
        ciphertext: ArrayInt,
        states: np.ndarray,
        limit: Optional[int] = None,
    ) -> Tuple[ArrayInt, np.ndarray, np.ndarray]:
        """
        Candidate plaintexts for each (state, ciphertext) pair.

        Parameters
        ----------
        ciphertext:
            Shape (Lq,) integer symbol array.
        states:
            Shape (B, Lq) integer state ids.
        limit:
            Maximum candidates retained per position.  Clamped to alphabet size.
        """
        LIMIT = 4 if limit is None else int(limit)
        if LIMIT < 0:
            raise ValueError("limit must be >= 0")
        LIMIT = min(LIMIT, int(self.alphabet_size))

        ct = np.asarray(ciphertext, dtype=int).reshape(-1)
        st = np.asarray(states, dtype=int)
        if st.ndim == 1:
            st = st[None, :]
        if st.shape[1] != ct.size:
            raise ValueError("states must have the same position count as ciphertext")

        B, Lq = int(st.shape[0]), int(st.shape[1])
        cands = np.zeros((B, Lq, LIMIT), dtype=int)
        lens = np.zeros((B, Lq), dtype=int)

        for b in range(B):
            for j in range(Lq):
                state = int(st[b, j])
                ct_sym = int(ct[j])
                n = int(self.dec_len[state, ct_sym])
                if n <= 0:
                    continue
                keep = min(n, LIMIT)
                lens[b, j] = keep
                if keep > 0:
                    cands[b, j, :keep] = self.dec_all[state, ct_sym, :keep]
                    if keep < LIMIT:
                        cands[b, j, keep:] = cands[b, j, keep - 1]

        invalid = lens == 0
        return cands, lens, invalid



@dataclass(frozen=True)
class _StreamRuntime:
    name: str
    kind: str
    period: Optional[int]
    key_start: int
    key_len: int
    fixed_values: Optional[np.ndarray]
    direction: str
    anchor: str
    offset: int
    repeat: bool
    advance: str


@dataclass(frozen=True)
class _CompiledSchedule:
    active: np.ndarray  # integer active-state values: 0 none, 1 A, 2 B, 3 AB
    a_idx: np.ndarray   # int64 stream-local index, -1 inactive
    b_idx: np.ndarray   # int64 stream-local index, -1 inactive


def _get_field(cfg: Any, spec: Any, name: str, default: Any = None) -> Any:
    """Read cfg.attr first, then spec.extra[name], then spec.attr, then default."""
    val = getattr(cfg, name, None)
    if val is not None:
        return val
    extra = getattr(spec, "extra", None) or {}
    if name in extra and extra[name] is not None:
        return extra[name]
    val = getattr(spec, name, None)
    if val is not None:
        return val
    return default


def _first_primes(n: int) -> np.ndarray:
    """Return the first n prime numbers as int64.  Small and deterministic."""
    n = int(n)
    if n <= 0:
        return np.empty(0, dtype=np.int64)
    out: list[int] = []
    candidate = 2
    while len(out) < n:
        is_prime = True
        limit = int(candidate ** 0.5)
        for p in out:
            if p > limit:
                break
            if candidate % p == 0:
                is_prime = False
                break
        if is_prime:
            out.append(candidate)
        candidate += 1
    return np.asarray(out, dtype=np.int64)


@register_cipher("scheduled_stream_lookup")
class ScheduledStreamLookupCipher(CipherPipelineMixin, KeyedCipherBase):
    """
    Scheduled two-stream lookup cipher.

    A small scheduler chooses stream values at each compact core position.  A
    lookup table then maps plaintext + active stream state to ciphertext.  This
    keeps the two concerns separate:

        schedule: where stream A/B apply
        lookup:   what active values do to a rune
    """

    keyops_family: KeyOpsFamily = KeyOpsFamily.VECTOR
    A: int = 29

    def __init__(self, cfg) -> None:
        spec = getattr(cfg, "spec", cfg)
        text_dir = ensure_direction(getattr(cfg, "text_transposition", Direction.LTR))
        key_dir = ensure_direction(getattr(cfg, "key_transposition", Direction.LTR))
        super().__init__(
            text_transposition=text_dir.value,
            key_transposition=key_dir.value,
            initial_text_permutation_indices=getattr(cfg, "initial_text_permutation_indices", None),
        )
        self.cfg = cfg
        self.text_direction = text_dir
        self.key_direction = key_dir
        self.device: Device = ensure_device(getattr(cfg, "device", Device.CPU))

        alias_raw = _get_field(cfg, spec, "name", "scheduled_stream_lookup")
        self.alias = normalise_name(alias_raw, "scheduled_stream_lookup")
        self.A = validate_alphabet_size(_get_field(cfg, spec, "alphabet_size", getattr(spec, "N", 29)))
        self.N = self.A

        self.operation, self.degeneracy = validate_operation_degeneracy(
            _get_field(cfg, spec, "operation", "add"),
            _get_field(cfg, spec, "degeneracy", getattr(spec, "degeneracy", "forbid")),
        )
        self.schedule_name = normalise_schedule(_get_field(cfg, spec, "schedule", "overlay"))
        self.alternating_start = normalise_alternating_start(_get_field(cfg, spec, "alternating_start", "A"))
        self.per_pos_limit = positive_int(
            _get_field(cfg, spec, "per_pos_limit", getattr(spec, "per_pos_limit", self.A)) or self.A,
            "per_pos_limit",
        )
        self.resolver_limit = positive_int(
            _get_field(cfg, spec, "resolver_limit", getattr(spec, "resolver_limit", 8193)) or 8193,
            "resolver_limit",
        )

        streams_cfg = _get_field(cfg, spec, "streams", None)
        if streams_cfg is None:
            streams_cfg = default_streams_for_alias(
                self.alias,
                period_a=_get_field(cfg, spec, "period_a", None),
                period_b=_get_field(cfg, spec, "period_b", None),
                period=_get_field(cfg, spec, "period", None),
                prime_offset=config_int(_get_field(cfg, spec, "prime_offset", 0), "prime_offset"),
            )
        self._stream_specs = validate_streams_v1(streams_cfg, alphabet_size=self.A)
        self.schedule_name = validate_schedule_for_streams(self.schedule_name, self._stream_specs)

        self.streams = self._parse_streams(self._stream_specs)
        key_len = int(sum(s.key_len for s in self.streams))
        cfg_key_len = config_int(getattr(cfg, "key_length", 0), "key_length")
        if cfg_key_len not in (0, key_len):
            raise ValueError(f"scheduled_stream_lookup expected key_length {key_len}, got {cfg_key_len}")
        self.key_length = key_len
        self.keyops_hints = {"mod": int(self.A)}

        self._lookup_cfg = _get_field(cfg, spec, "lookup", None)
        self._lookups = self._build_lookup_tables()

        # Stream/schedule knobs.  Stored plainly for easy inspection/telemetry.
        self.a_start = config_int(_get_field(cfg, spec, "a_start", 0), "a_start")
        self.b_start = config_int(_get_field(cfg, spec, "b_start", 0), "b_start")
        self.a_end = optional_config_int(_get_field(cfg, spec, "a_end", None), "a_end")
        self.b_end = optional_config_int(_get_field(cfg, spec, "b_end", None), "b_end")
        self.mask = _get_field(cfg, spec, "mask", None)

    def _parse_streams(self, specs: Sequence[dict[str, Any]]) -> Tuple[_StreamRuntime, ...]:
        """Convert already validated stream specs into runtime stream records."""
        streams: list[_StreamRuntime] = []
        key_start = 0
        for idx, raw in enumerate(specs):
            name = str(raw.get("name", "A" if idx == 0 else "B"))
            kind = str(raw["kind"])
            direction = str(raw["direction"])
            anchor = str(raw["anchor"])
            advance = str(raw["advance"])
            offset = int(raw["offset"])
            repeat = bool(raw["repeat"])
            period: Optional[int] = None
            key_len = 0
            fixed_values: Optional[np.ndarray] = None

            if kind == "periodic":
                period = int(raw["period"])
                key_len = period
            elif kind == "primes":
                period = None
            elif kind == "fixed":
                values = raw.get("values", None)
                if values is None:
                    raise ValueError("fixed streams require values")
                fixed_values = np.asarray(values, dtype=np.int64).reshape(-1).astype(int, copy=False)
                if fixed_values.size == 0:
                    raise ValueError("fixed streams require at least one value")
                period = int(fixed_values.size)
            else:
                raise ValueError(f"unknown stream kind {kind!r}")

            streams.append(
                _StreamRuntime(
                    name=name,
                    kind=kind,
                    period=period,
                    key_start=key_start,
                    key_len=key_len,
                    fixed_values=fixed_values,
                    direction=direction,
                    anchor=anchor,
                    offset=offset,
                    repeat=repeat,
                    advance=advance,
                )
            )
            key_start += key_len
        return tuple(streams)

    # ------------------------------------------------------------------
    # Lookup tables
    # ------------------------------------------------------------------
    def _build_lookup_tables(self) -> dict[int, LookupTables]:
        A = int(self.A)
        if self.operation == "lookup":
            return self._build_custom_lookup_tables()
        # normalise_operation() already validated the operation name in __init__.
        return {
            _ACTIVE_NONE: LookupTables.from_function(
                alphabet_size=A,
                state_size=1,
                function=lambda pt, state: self._eval_operation(pt, None, None, _ACTIVE_NONE),
            ),
            _ACTIVE_A: LookupTables.from_function(
                alphabet_size=A,
                state_size=A,
                function=lambda pt, state: self._eval_operation(pt, state, None, _ACTIVE_A),
            ),
            _ACTIVE_B: LookupTables.from_function(
                alphabet_size=A,
                state_size=A,
                function=lambda pt, state: self._eval_operation(pt, None, state, _ACTIVE_B),
            ),
            _ACTIVE_AB: LookupTables.from_function(
                alphabet_size=A,
                state_size=A * A,
                function=lambda pt, state: self._eval_operation(pt, state // A, state % A, _ACTIVE_AB),
            ),
        }

    def _build_custom_lookup_tables(self) -> dict[int, LookupTables]:
        if self._lookup_cfg is None or not isinstance(self._lookup_cfg, Mapping):
            raise ValueError("operation='lookup' requires lookup={...} tables")
        A = int(self.A)
        tables: dict[int, LookupTables] = {}
        mapping = {
            _ACTIVE_NONE: ("none", 1),
            _ACTIVE_A: ("a", A),
            _ACTIVE_B: ("b", A),
            _ACTIVE_AB: ("ab", A * A),
        }
        for active, (name, state_size) in mapping.items():
            raw = self._lookup_cfg.get(name)
            if raw is None:
                if active == _ACTIVE_NONE:
                    tables[active] = LookupTables.from_function(
                        alphabet_size=A, state_size=1, function=lambda pt, state: pt
                    )
                    continue
                raise ValueError(f"lookup table for active state {name!r} is required")
            arr = np.asarray(raw, dtype=object)
            if active == _ACTIVE_AB and arr.shape == (A, A, A):
                arr = arr.reshape(A, A * A)
            tables[active] = LookupTables.from_table(alphabet_size=A, state_size=state_size, table=arr)
        return tables

    def _eval_operation(self, pt: int, a: Optional[int], b: Optional[int], active: int) -> int:
        A = int(self.A)
        p = int(pt)
        av = 0 if a is None else int(a)
        bv = 0 if b is None else int(b)
        if active == _ACTIVE_NONE:
            return p % A
        if self.operation == "add":
            return (p + av + bv) % A
        if self.operation == "add_sub":
            return (p + av - bv) % A
        if self.operation == "sub_add":
            return (p - av + bv) % A
        if self.operation == "beaufort_sum":
            return (av + bv - p) % A
        if self.operation == "xor_mod":
            x = p
            if active & _ACTIVE_A:
                x ^= av
            if active & _ACTIVE_B:
                x ^= bv
            return x % A
        raise ValueError(f"unknown operation {self.operation!r}")

    # ------------------------------------------------------------------
    # Schedule and stream values
    # ------------------------------------------------------------------
    def _window_mask(self, pos: np.ndarray, *, start: int, end: Any, length: int, label: str) -> np.ndarray:
        """Return a boolean active-window mask and reject impossible bounds."""
        lo, hi = validate_schedule_window(length, start=start, end=end, label=label)
        return (pos >= lo) & (pos < hi)

    def _compile_schedule(self, L: int) -> _CompiledSchedule:
        L = int(L)
        active = np.zeros(L, dtype=int)
        pos = np.arange(L, dtype=np.int64)

        if self.schedule_name == "overlay":
            active[:] = _ACTIVE_AB if len(self.streams) >= 2 else _ACTIVE_A
        elif self.schedule_name == "alternating":
            if len(self.streams) < 2:
                raise ValueError("alternating schedule requires two streams")
            even = (pos % 2) == 0
            if self.alternating_start == "A":
                active[even] = _ACTIVE_A
                active[~even] = _ACTIVE_B
            else:
                active[even] = _ACTIVE_B
                active[~even] = _ACTIVE_A
        elif self.schedule_name == "staggered_overlay":
            if len(self.streams) < 2:
                raise ValueError("staggered_overlay schedule requires two streams")
            a_on = self._window_mask(pos, start=self.a_start, end=None, length=L, label="A")
            b_on = self._window_mask(pos, start=self.b_start, end=None, length=L, label="B")
            active = (a_on.astype(int) * _ACTIVE_A) | (b_on.astype(int) * _ACTIVE_B)
        elif self.schedule_name == "ragged_overlap":
            if len(self.streams) < 2:
                raise ValueError("ragged_overlap schedule requires two streams")
            a_on = self._window_mask(pos, start=self.a_start, end=self.a_end, length=L, label="A")
            b_on = self._window_mask(pos, start=self.b_start, end=self.b_end, length=L, label="B")
            active = (a_on.astype(int) * _ACTIVE_A) | (b_on.astype(int) * _ACTIVE_B)
        elif self.schedule_name == "mask":
            active = np.asarray(validate_mask(self.mask, length=L), dtype=int).reshape(-1)
        else:
            raise ValueError(f"unknown schedule {self.schedule_name!r}")

        if len(self.streams) < 2 and np.any((active & _ACTIVE_B) != 0):
            raise ValueError("schedule activates stream B, but only one stream is configured")

        a_idx = self._indices_for_stream(self.streams[0], L)
        b_idx = self._indices_for_stream(self.streams[1], L) if len(self.streams) > 1 else np.full(L, -1, dtype=np.int64)
        a_idx = np.where((active & _ACTIVE_A) != 0, a_idx, -1).astype(np.int64, copy=False)
        b_idx = np.where((active & _ACTIVE_B) != 0, b_idx, -1).astype(np.int64, copy=False)
        return _CompiledSchedule(active=active.astype(int, copy=False), a_idx=a_idx, b_idx=b_idx)

    def _indices_for_stream(self, stream: _StreamRuntime, L: int) -> np.ndarray:
        pos = np.arange(int(L), dtype=np.int64)
        if stream.direction == "forward":
            raw = pos if stream.anchor == "start" else pos - (int(L) - 1)
        else:
            raw = -pos if stream.anchor == "start" else (int(L) - 1) - pos
        raw = raw + int(stream.offset)

        if stream.kind == "periodic":
            assert stream.period is not None
            return np.mod(raw, int(stream.period)).astype(np.int64, copy=False)
        if stream.kind == "fixed" and stream.repeat:
            assert stream.period is not None
            return np.mod(raw, int(stream.period)).astype(np.int64, copy=False)
        if np.any(raw < 0):
            raise ValueError(
                f"stream {stream.name!r} produces negative generated/fixed indices; "
                "adjust anchor/direction/offset"
            )
        if stream.kind == "fixed":
            assert stream.period is not None
            if np.any(raw >= int(stream.period)):
                raise ValueError(f"fixed stream {stream.name!r} index exceeds values and repeat=False")
        return raw.astype(np.int64, copy=False)

    def _stream_values(self, stream: _StreamRuntime, idx: np.ndarray, keys: np.ndarray) -> np.ndarray:
        """Return values shaped (B, Lq) for one stream over selected positions."""
        B = int(keys.shape[0])
        idx = np.asarray(idx, dtype=np.int64).reshape(-1)
        if stream.kind == "periodic":
            cols = int(stream.key_start) + idx
            return keys[:, cols].astype(np.int64, copy=False)
        if stream.kind == "fixed":
            assert stream.fixed_values is not None
            vals = stream.fixed_values[idx].astype(np.int64, copy=False)
            return np.broadcast_to(vals[None, :], (B, vals.size))
        if stream.kind == "primes":
            max_idx = int(idx.max()) if idx.size else -1
            vals = (_first_primes(max_idx + 1)[idx] % self.A).astype(np.int64, copy=False)
            return np.broadcast_to(vals[None, :], (B, vals.size))
        raise ValueError(f"unknown stream kind {stream.kind!r}")

    def _states_for_active(
        self,
        keys: np.ndarray,
        sched: _CompiledSchedule,
        positions: np.ndarray,
        active: int,
    ) -> np.ndarray:
        pos = np.asarray(positions, dtype=np.int64).reshape(-1)
        if active == _ACTIVE_NONE:
            return np.zeros((int(keys.shape[0]), int(pos.size)), dtype=np.int64)
        if active == _ACTIVE_A:
            return self._stream_values(self.streams[0], sched.a_idx[pos], keys)
        if active == _ACTIVE_B:
            return self._stream_values(self.streams[1], sched.b_idx[pos], keys)
        if active == _ACTIVE_AB:
            a = self._stream_values(self.streams[0], sched.a_idx[pos], keys)
            b = self._stream_values(self.streams[1], sched.b_idx[pos], keys)
            return a * int(self.A) + b
        raise ValueError(f"invalid active state {active}")

    def _prepare_keys(self, keys_tr: ArrayInt) -> np.ndarray:
        keys = np.asarray(keys_tr, dtype=np.int64)
        if keys.ndim == 1:
            keys = keys[None, :]
        if keys.shape[1] != int(self.key_length):
            raise ValueError(f"Expected key length {self.key_length}, got {keys.shape[1]}")
        if keys.size:
            keys = keys % int(self.A)
        return keys

    # ------------------------------------------------------------------
    # Core kernels used by CipherPipelineMixin
    # ------------------------------------------------------------------
    def _core_encrypt_batch(self, pt_tr: ArrayInt, keys_tr: ArrayInt) -> ArrayInt:
        pt = np.asarray(pt_tr, dtype=int).reshape(-1)
        keys = self._prepare_keys(keys_tr)
        B, L = int(keys.shape[0]), int(pt.size)
        sched = self._compile_schedule(L)
        out = np.zeros((B, L), dtype=int)
        all_pos = np.arange(L, dtype=np.int64)
        for active in (_ACTIVE_NONE, _ACTIVE_A, _ACTIVE_B, _ACTIVE_AB):
            mask = sched.active == active
            if not np.any(mask):
                continue
            pos = all_pos[mask]
            states = self._states_for_active(keys, sched, pos, active)
            out[:, pos] = self._lookups[active].encrypt_first(pt[pos][None, :], states)
        return out

    def _core_decrypt_batch(self, ct_tr: ArrayInt, keys_tr: ArrayInt) -> ArrayInt:
        ct = np.asarray(ct_tr, dtype=int).reshape(-1)
        keys = self._prepare_keys(keys_tr)
        B, L = int(keys.shape[0]), int(ct.size)
        sched = self._compile_schedule(L)
        out = np.zeros((B, L), dtype=int)
        all_pos = np.arange(L, dtype=np.int64)
        for active in (_ACTIVE_NONE, _ACTIVE_A, _ACTIVE_B, _ACTIVE_AB):
            mask = sched.active == active
            if not np.any(mask):
                continue
            pos = all_pos[mask]
            states = self._states_for_active(keys, sched, pos, active)
            out[:, pos] = self._lookups[active].decrypt_first_symbol(ct[pos][None, :], states)
        return out

    def candidates_for(
        self,
        ct_tr: ArrayInt,
        keys_tr: ArrayInt,
        *,
        positions: Optional[np.ndarray] = None,
        limit: Optional[int] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        ct = np.asarray(ct_tr, dtype=int).reshape(-1)
        keys = self._prepare_keys(keys_tr)
        B, L = int(keys.shape[0]), int(ct.size)
        pos = np.arange(L, dtype=np.int64) if positions is None else np.asarray(positions, dtype=np.int64).reshape(-1)
        if np.any(pos < 0) or np.any(pos >= L):
            raise ValueError("positions contains out-of-range values")
        LIMIT = self.per_pos_limit if limit is None else config_int(limit, "limit")
        if LIMIT < 0:
            raise ValueError("limit must be >= 0")
        LIMIT = min(LIMIT, int(self.A))

        sched = self._compile_schedule(L)
        cands = np.zeros((B, int(pos.size), LIMIT), dtype=int)
        lens = np.zeros((B, int(pos.size)), dtype=int)

        for active in (_ACTIVE_NONE, _ACTIVE_A, _ACTIVE_B, _ACTIVE_AB):
            local = np.flatnonzero(sched.active[pos] == active)
            if local.size == 0:
                continue
            actual_pos = pos[local]
            states = self._states_for_active(keys, sched, actual_pos, active)
            sub_cands, sub_lens, _sub_invalid = self._lookups[active].candidates_for_states(
                ciphertext=ct[actual_pos],
                states=states,
                limit=LIMIT,
            )
            cands[:, local, :] = sub_cands
            lens[:, local] = sub_lens

        invalid = lens == 0
        return cands, lens, invalid

