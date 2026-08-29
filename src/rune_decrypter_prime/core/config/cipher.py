# ============================================================
# rune_decrypter_prime/core/config/cipher.py
# ============================================================
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence

if TYPE_CHECKING:
    from rune_decrypter_prime.api.specs import CipherSpec, KeySpec

from rune_decrypter_prime.core.config.interruptor import InterruptorConfig
from rune_decrypter_prime.core.types import (
    Device,
    Direction,
    ensure_device,
    ensure_direction,
    ensure_keyops_family,
    KeyOpsFamily,
)

# ---------------- CipherConfig ------------------------------------------------
@dataclass
class CipherConfig:
    """Cipher-specific configuration (ciphertext, WLI, keys, device, etc.)."""
    ciphertext: Sequence[int]
    wli_data: Sequence[Sequence[int]]
    key_length: Optional[int]
    keyops_family: Optional[KeyOpsFamily | str] = None
    keyops_hints: Optional[Dict[str, Any]] = None
    # Optional cipher-family specification object for typed plugin contracts.
    # This is not a general config escape hatch: runtime code may use it only
    # when a cipher plugin defines and documents a concrete spec object.
    spec: Optional[Any] = None
    key_space: Optional[Any] = None
    alphabet_size: Optional[int] = None
    period: Optional[int] = None
    columns: Optional[int] = None
    order: Optional[str] = None
    plaintext_english26: Optional[str] = None
    plaintext: Optional[Sequence[int]] = None
    initial_text_permutation_indices: Optional[Sequence[int]] = None
    device: Optional[Device] = Device.CPU
    encoding_dir: Optional[Direction] = Direction.LTR
    interruptors: Optional[List[int]] = None
    interruptors_cfg: Optional[InterruptorConfig | Dict[str, Any]] = None
    initial_keys: Optional[List[Sequence[int]]] = None
    test_key: Optional[Sequence[int]] = None
    interruptors_exact: Optional[List[int]] = None
    interruptors_pool: Optional[List[int]] = None
    interruptors_max: Optional[int] = None
    transposition_search_modes: Optional[List[str]] = None
    name: str = "vigenere"
    def __post_init__(self) -> None:
        if self.device is not None:
            self.device = ensure_device(self.device)
        if self.encoding_dir is not None:
            self.encoding_dir = ensure_direction(self.encoding_dir)
        if self.keyops_family is not None:
            self.keyops_family = ensure_keyops_family(self.keyops_family)

        if self.wli_data is not None:
            try:
                import numpy as _np  # local import to avoid core-level import debt
                arr = self.wli_data
                # Allow empty list/array to mean "no WLI"
                if isinstance(arr, _np.ndarray):
                    if arr.size == 0:
                        self.wli_data = []
                        arr = None
                    else:
                        if arr.ndim != 2 or arr.shape[1] != 2:
                            raise ValueError("wli_data ndarray must have shape (N,2)")
                        pairs = [[int(a), int(b)] for a, b in arr.tolist()]
                        self._validate_wli_pairs(pairs)
                        self.wli_data = pairs
                        arr = None
                if arr is not None:
                    pairs = list(arr)
                    if len(pairs) == 0:
                        self.wli_data = []
                    else:
                        out: list[list[int]] = []
                        for i, pair in enumerate(pairs):
                            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                                raise ValueError("wli_data items must be (pos_in_word, word_len) pairs")
                            out.append([int(pair[0]), int(pair[1])])
                        self._validate_wli_pairs(out)
                        self.wli_data = out
            except Exception as exc:
                raise ValueError("wli_data must be a sequence of two-integer tuples as documented") from exc

        self._normalize_interruptors_cfg()

    def _validate_wli_pairs(self, pairs: list[list[int]]) -> None:
        # Empty list means "no WLI"; caller must handle WLI requirement.
        if not pairs:
            return
        ct_len = len(self.ciphertext) if self.ciphertext is not None else None
        if ct_len is not None and len(pairs) != int(ct_len):
            raise ValueError("wli_data length must match ciphertext length")
        expected_pos = 0
        current_len = None
        for i, (pos, ln) in enumerate(pairs):
            if pos < 0 or ln <= 0:
                raise ValueError("wli_data entries must be non-negative; word_len must be > 0")
            if pos >= ln:
                raise ValueError("wli_data pos_in_word must be < word_len")
            if pos > 63 or ln > 63:
                raise ValueError("wli_data entries must be <= 63 to match LMPrime WLI encoding")
            if expected_pos == 0:
                current_len = ln
            if ln != current_len:
                raise ValueError("wli_data word_len must remain constant within a word")
            if pos != expected_pos:
                raise ValueError("wli_data pos_in_word sequence must be contiguous within each word")
            expected_pos += 1
            if expected_pos == current_len:
                expected_pos = 0
                current_len = None
        if expected_pos != 0:
            raise ValueError("wli_data word_len exceeds available positions")

    def _normalize_interruptors_cfg(self) -> None:
        cfg_raw = getattr(self, "interruptors_cfg", None)
        has_legacy = any(
            x is not None for x in (
                self.interruptors_exact,
                self.interruptors,
                self.interruptors_pool,
                self.interruptors_max,
            )
        )

        if cfg_raw is not None:
            if has_legacy:
                raise ValueError("interruptors_cfg cannot be combined with legacy interruptor fields")
            if isinstance(cfg_raw, dict):
                cfg = InterruptorConfig.from_dict(cfg_raw)
            elif isinstance(cfg_raw, InterruptorConfig):
                cfg = cfg_raw
            else:
                raise TypeError("interruptors_cfg must be InterruptorConfig or dict")
            self.interruptors_cfg = cfg
        else:
            cfg = None
            if self.interruptors_exact is not None:
                cfg = InterruptorConfig.exact(self.interruptors_exact)
            elif self.interruptors is not None:
                cfg = InterruptorConfig.exact(self.interruptors)
            elif self.interruptors_pool is not None or self.interruptors_max is not None:
                pool = list(self.interruptors_pool or [])
                if not pool:
                    raise ValueError("interruptors_pool is required when interruptors_max is set")
                count = len(pool) if self.interruptors_max is None else int(self.interruptors_max)
                cfg = InterruptorConfig.search(
                    pool,
                    minimum_count=count,
                    maximum_count=count,
                )
            self.interruptors_cfg = cfg


def _binding_error(cipher: "CipherSpec", key_space: "KeySpec", message: str):
    from rune_decrypter_prime.core.component_contracts import CipherKeyMismatchError

    raise CipherKeyMismatchError(message, cipher=cipher, key_space=key_space)


def expected_concrete_key_length(cipher: "CipherSpec", key_space: "KeySpec") -> int:
    """Validate one accepted cipher/key-space pair and return its flat length."""
    from rune_decrypter_prime.api.specs import CipherSpec, KeySpec
    from rune_decrypter_prime.core.types import FinalCipherKind, FinalKeyKind

    if not isinstance(cipher, CipherSpec):
        raise TypeError("cipher must be CipherSpec")
    if not isinstance(key_space, KeySpec):
        raise TypeError("key_space must be KeySpec")

    cipher_values = cipher.parameters
    key_values = key_space.parameters
    kind = cipher.kind
    key_kind = key_space.kind

    if kind in {FinalCipherKind.VIGENERE, FinalCipherKind.AUTOKEY}:
        if key_kind is not FinalKeyKind.REPEATING:
            _binding_error(cipher, key_space, f"{kind.value} requires a repeating key space")
        return int(key_values["length"])

    if kind is FinalCipherKind.COLUMNAR:
        if key_kind is not FinalKeyKind.PERMUTATION:
            _binding_error(cipher, key_space, "columnar requires a permutation key space")
        columns = int(cipher_values["columns"])
        if int(key_values["length"]) != columns:
            _binding_error(cipher, key_space, "columnar key length must equal cipher columns")
        return columns

    if kind is FinalCipherKind.RAIL_FENCE:
        if key_kind is not FinalKeyKind.SCALAR:
            _binding_error(cipher, key_space, "rail_fence requires a scalar key space")
        expected = (
            int(cipher_values["minimum_rails"]),
            int(cipher_values["maximum_rails"]),
        )
        supplied = (int(key_values["minimum"]), int(key_values["maximum"]))
        if supplied != expected:
            _binding_error(cipher, key_space, "rail_fence key bounds must match cipher rail bounds")
        return 1

    if kind is FinalCipherKind.SUBSTITUTION:
        if key_kind is not FinalKeyKind.PERMUTATION:
            _binding_error(cipher, key_space, "substitution requires a permutation key space")
        alphabet_size = int(cipher_values["alphabet_size"])
        if int(key_values["length"]) != alphabet_size:
            _binding_error(cipher, key_space, "substitution key length must equal alphabet size")
        return alphabet_size

    if kind is FinalCipherKind.PERIODIC_SUBSTITUTION:
        if key_kind is not FinalKeyKind.PERIODIC_SUBSTITUTION:
            _binding_error(cipher, key_space, "periodic_substitution requires its structured key space")
        for dimension in ("period", "alphabet_size"):
            if int(key_values[dimension]) != int(cipher_values[dimension]):
                _binding_error(cipher, key_space, f"periodic_substitution {dimension} values conflict")
        return int(cipher_values["period"]) * int(cipher_values["alphabet_size"])

    if kind is FinalCipherKind.PERIODIC_COLUMNAR:
        if key_kind is not FinalKeyKind.PERIODIC_COLUMNAR:
            _binding_error(cipher, key_space, "periodic_columnar requires its structured key space")
        for dimension in ("period", "columns", "alphabet_size"):
            if int(key_values[dimension]) != int(cipher_values[dimension]):
                _binding_error(cipher, key_space, f"periodic_columnar {dimension} values conflict")
        return (
            int(cipher_values["period"]) * int(cipher_values["alphabet_size"])
            + int(cipher_values["columns"])
        )

    if key_kind is not FinalKeyKind.REPEATING:
        _binding_error(cipher, key_space, f"{kind.value} requires a repeating key space")
    if kind in {FinalCipherKind.TWO_PERIOD_VIGENERE, FinalCipherKind.TWO_PERIOD_STREAMS}:
        expected_length = int(cipher_values["first_period"]) + int(cipher_values["second_period"])
    elif kind in {
        FinalCipherKind.PERIODIC_WITH_FIXED_STREAM,
        FinalCipherKind.PERIODIC_WITH_PRIME_STREAM,
    }:
        expected_length = int(cipher_values["period"])
    else:
        _binding_error(cipher, key_space, f"unsupported cipher kind {kind.value!r}")
    if int(key_values["length"]) != expected_length:
        _binding_error(
            cipher,
            key_space,
            f"{kind.value} requires derived key length {expected_length}",
        )
    return expected_length


def validate_concrete_key(
    cipher: "CipherSpec",
    key_space: "KeySpec",
    key: tuple[int, ...],
) -> tuple[int, ...]:
    """Apply the shared strict V1 key length, range, and segment validator."""
    from rune_decrypter_prime.core.component_contracts import InvalidConcreteKeyError
    from rune_decrypter_prime.core.types import FinalCipherKind, normalize_concrete_key

    concrete_key = normalize_concrete_key(key)
    expected_length = expected_concrete_key_length(cipher, key_space)
    if len(concrete_key) != expected_length:
        raise InvalidConcreteKeyError(
            f"concrete key length must be {expected_length}",
            expected_domain=f"tuple[int, ...] of length {expected_length}",
        )

    values = cipher.parameters
    alphabet_size = int(values["alphabet_size"])
    kind = cipher.kind
    if kind is FinalCipherKind.RAIL_FENCE:
        minimum = int(values["minimum_rails"])
        maximum = int(values["maximum_rails"])
        if not minimum <= concrete_key[0] <= maximum:
            raise InvalidConcreteKeyError(
                "rail count is outside the configured inclusive bounds",
                index=0,
                value=concrete_key[0],
                expected_domain=f"[{minimum}, {maximum}]",
            )
        return concrete_key

    permutation_segments: list[tuple[int, int]] = []
    if kind is FinalCipherKind.COLUMNAR:
        permutation_segments.append((0, int(values["columns"])))
    elif kind is FinalCipherKind.SUBSTITUTION:
        permutation_segments.append((0, alphabet_size))
    elif kind is FinalCipherKind.PERIODIC_SUBSTITUTION:
        for start in range(0, len(concrete_key), alphabet_size):
            permutation_segments.append((start, alphabet_size))
    elif kind is FinalCipherKind.PERIODIC_COLUMNAR:
        periodic_length = int(values["period"]) * alphabet_size
        for start in range(0, periodic_length, alphabet_size):
            permutation_segments.append((start, alphabet_size))
        permutation_segments.append((periodic_length, int(values["columns"])))

    segment_indices: set[int] = set()
    for start, length in permutation_segments:
        expected = tuple(range(length))
        segment = concrete_key[start : start + length]
        if tuple(sorted(segment)) != expected:
            raise InvalidConcreteKeyError(
                "concrete key permutation segment is invalid",
                index=start,
                expected_domain=f"permutation of [0, {length - 1}]",
            )
        segment_indices.update(range(start, start + length))
    for index, value in enumerate(concrete_key):
        if index in segment_indices:
            continue
        if value < 0 or value >= alphabet_size:
            raise InvalidConcreteKeyError(
                "concrete key symbol is outside the cipher alphabet",
                index=index,
                value=value,
                expected_domain=f"[0, {alphabet_size - 1}]",
            )
    return concrete_key


def materialize_cipher_config(
    *,
    cipher: "CipherSpec",
    key_space: "KeySpec",
    ciphertext: Sequence[int],
    word_lengths: Sequence[Sequence[int]] | None,
    text_direction: object,
    compute_device: object,
    initial_keys: Sequence[Sequence[int]] | None = None,
    text_permutation: Sequence[int] | None = None,
    interruptors: InterruptorConfig | None = None,
) -> CipherConfig:
    """Build the sole internal runtime cipher configuration from typed specs."""
    from rune_decrypter_prime.core.types import (
        ComputeDevice,
        FinalCipherKind,
        PeriodicColumnarOrder,
        ScheduledStreamOperation,
        TextDirection,
    )

    if not isinstance(text_direction, TextDirection):
        raise TypeError("text_direction must be TextDirection")
    if not isinstance(compute_device, ComputeDevice):
        raise TypeError("compute_device must be ComputeDevice")
    key_length = expected_concrete_key_length(cipher, key_space)
    validated_initial_keys = None
    if initial_keys is not None:
        validated_initial_keys = [
            validate_concrete_key(cipher, key_space, tuple(key))
            for key in initial_keys
        ]
    values = cipher.parameters
    kind = cipher.kind
    runtime_identity = kind.value
    config_values: dict[str, object] = {}

    if kind is FinalCipherKind.RAIL_FENCE:
        config_values.update(
            min_rails=int(values["minimum_rails"]),
            max_rails=int(values["maximum_rails"]),
        )
    elif kind in {FinalCipherKind.PERIODIC_SUBSTITUTION, FinalCipherKind.PERIODIC_COLUMNAR}:
        config_values.update(
            period=int(values["period"]),
            alphabet_size=int(values["alphabet_size"]),
        )
        if kind is FinalCipherKind.PERIODIC_COLUMNAR:
            config_values["columns"] = int(values["columns"])
            config_values["order"] = {
                PeriodicColumnarOrder.SUBSTITUTION_THEN_COLUMNAR.value: "sub_then_col",
                PeriodicColumnarOrder.COLUMNAR_THEN_SUBSTITUTION.value: "col_then_sub",
            }[str(values["order"])]
    elif kind in {
        FinalCipherKind.TWO_PERIOD_VIGENERE,
        FinalCipherKind.PERIODIC_WITH_FIXED_STREAM,
        FinalCipherKind.PERIODIC_WITH_PRIME_STREAM,
        FinalCipherKind.TWO_PERIOD_STREAMS,
    }:
        from rune_decrypter_prime.ciphers.scheduled_stream_lookup_cipher import (
            solved_key_length_for_streams,
            validate_mask,
            validate_schedule_for_streams,
            validate_streams_v1,
        )

        runtime_identity = "scheduled_stream_lookup"
        if kind in {FinalCipherKind.TWO_PERIOD_VIGENERE, FinalCipherKind.TWO_PERIOD_STREAMS}:
            streams = [
                {"name": "A", "kind": "periodic", "period": int(values["first_period"])},
                {"name": "B", "kind": "periodic", "period": int(values["second_period"])},
            ]
        elif kind is FinalCipherKind.PERIODIC_WITH_FIXED_STREAM:
            streams = [
                {"name": "A", "kind": "periodic", "period": int(values["period"])},
                {"name": "B", "kind": "fixed", "values": list(values["fixed_stream"])},
            ]
        else:
            streams = [
                {"name": "A", "kind": "periodic", "period": int(values["period"])},
                {"name": "B", "kind": "primes", "offset": int(values["prime_offset"])},
            ]
        operation = "add"
        if kind is FinalCipherKind.TWO_PERIOD_STREAMS:
            operation = {
                ScheduledStreamOperation.ADD.value: "add",
                ScheduledStreamOperation.ADD_SUBTRACT.value: "add_sub",
                ScheduledStreamOperation.SUBTRACT_ADD.value: "sub_add",
                ScheduledStreamOperation.BEAUFORT_SUM.value: "beaufort_sum",
            }[str(values["operation"])]
        streams = validate_streams_v1(streams, alphabet_size=int(values["alphabet_size"]))
        if solved_key_length_for_streams(streams) != key_length:
            raise RuntimeError("scheduled runtime key length disagrees with the public binding")
        schedule = validate_schedule_for_streams(values.get("schedule", "overlay"), streams)
        mask = values.get("mask")
        if schedule == "mask":
            mask = tuple(validate_mask(mask, length=len(ciphertext)))
        config_values.update(
            streams=streams,
            schedule=schedule,
            operation=operation,
            mask=mask,
        )

    cfg = CipherConfig(
        ciphertext=tuple(int(value) for value in ciphertext),
        wli_data=tuple(word_lengths or ()),
        key_length=key_length,
        keyops_family=(
            KeyOpsFamily.PERMUTATION
            if kind in {FinalCipherKind.COLUMNAR, FinalCipherKind.SUBSTITUTION}
            else KeyOpsFamily.MATRIX
            if kind in {FinalCipherKind.PERIODIC_SUBSTITUTION, FinalCipherKind.PERIODIC_COLUMNAR}
            else KeyOpsFamily.VECTOR
        ),
        keyops_hints=(
            {
                "mod": int(values["maximum_rails"]) - int(values["minimum_rails"]) + 1,
                "minimum": int(values["minimum_rails"]),
            }
            if kind is FinalCipherKind.RAIL_FENCE
            else {"mod": int(values["alphabet_size"])}
        ),
        spec=cipher,
        key_space=key_space,
        alphabet_size=int(values["alphabet_size"]),
        initial_text_permutation_indices=text_permutation,
        device=Device.CPU if compute_device is ComputeDevice.CPU else Device.CUDA,
        encoding_dir=Direction.LTR if text_direction is TextDirection.LEFT_TO_RIGHT else Direction.RTL,
        interruptors_cfg=interruptors,
        initial_keys=validated_initial_keys,
        name=runtime_identity,
    )
    for name, value in config_values.items():
        setattr(cfg, name, value)
    return cfg
