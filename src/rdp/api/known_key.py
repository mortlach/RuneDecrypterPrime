"""Pure known-key operations over the shared cipher materializer.

This module is moved to the canonical ``rdp.api`` package during AN3.6. It
contains no solver, scorer, runtime-object facade, or generic transform route.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from rdp.api.specs import CipherSpec, KeySpec
from rune_decrypter_prime.core.component_contracts import (
    CapabilityIssue,
    CapabilityStatus,
    NonInvertibleCipherError,
)
from rune_decrypter_prime.core.config.cipher import (
    materialize_cipher_config,
    validate_concrete_key,
)
from rune_decrypter_prime.core.engine.builders import build_cipher
from rune_decrypter_prime.core.types import (
    ComputeDevice,
    CipherKind,
    ConcreteKey,
    FinalCipherKind,
    RuneIndices,
    TextDirection,
    normalize_concrete_key,
    normalize_rune_indices,
)


def encrypt(
    plaintext: RuneIndices,
    *,
    cipher: CipherSpec,
    key: ConcreteKey,
) -> RuneIndices:
    """Encrypt immutable rune indices with one validated semantic key."""
    return _known_key_operation("encrypt", plaintext, cipher=cipher, key=key)


def decrypt(
    ciphertext: RuneIndices,
    *,
    cipher: CipherSpec,
    key: ConcreteKey,
) -> RuneIndices:
    """Decrypt immutable rune indices with one validated semantic key."""
    return _known_key_operation("decrypt", ciphertext, cipher=cipher, key=key)


def _known_key_operation(
    operation: str,
    text: Sequence[int],
    *,
    cipher: CipherSpec,
    key: ConcreteKey,
) -> RuneIndices:
    if not isinstance(cipher, CipherSpec):
        raise TypeError("cipher must be CipherSpec")
    field_name = "plaintext" if operation == "encrypt" else "ciphertext"
    indices = normalize_rune_indices(text, field_name=field_name)
    concrete_key = normalize_concrete_key(key)
    key_space = _key_space_for_cipher(cipher, key_length=len(concrete_key))
    concrete_key = validate_concrete_key(cipher, key_space, concrete_key)
    cfg = materialize_cipher_config(
        cipher=cipher,
        key_space=key_space,
        ciphertext=indices,
        word_lengths=None,
        text_direction=TextDirection.RIGHT_TO_LEFT,
        compute_device=ComputeDevice.CPU,
    )
    runtime = build_cipher(cfg)
    method = getattr(runtime, operation, None)
    if not callable(method):
        raise _non_invertible_error(cipher, operation)
    key_array = np.asarray(concrete_key, dtype=np.int16)
    try:
        if operation == "encrypt":
            output = method(plaintext=np.asarray(indices, dtype=np.uint8), key=key_array)
        else:
            output = method(ciphertext=np.asarray(indices, dtype=np.uint8), key=key_array)
    except NotImplementedError as exc:
        raise _non_invertible_error(cipher, operation) from exc
    values = np.asarray(output)
    if values.ndim == 2:
        if values.shape[0] != 1:
            raise RuntimeError(f"known-key {operation} returned an unexpected batch")
        values = values[0]
    if values.ndim != 1:
        raise RuntimeError(f"known-key {operation} returned shape {values.shape}")
    result = tuple(int(item) for item in values.tolist())
    return normalize_rune_indices(result, field_name="result")


def _key_space_for_cipher(cipher: CipherSpec, *, key_length: int) -> KeySpec:
    values = cipher.parameters
    kind = cipher.kind
    if kind in {CipherKind.USER_MAP2, CipherKind.LOOKUP}:
        return KeySpec.repeating(length=key_length)
    if kind in {FinalCipherKind.VIGENERE, FinalCipherKind.AUTOKEY}:
        return KeySpec.repeating(length=key_length)
    if kind in {
        FinalCipherKind.PERIODIC_WITH_FIXED_STREAM,
        FinalCipherKind.PERIODIC_WITH_PRIME_STREAM,
    }:
        return KeySpec.repeating(length=int(values["period"]))
    if kind is FinalCipherKind.COLUMNAR:
        return KeySpec.permutation(length=int(values["columns"]))
    if kind is FinalCipherKind.RAIL_FENCE:
        return KeySpec.scalar(
            minimum=int(values["minimum_rails"]),
            maximum=int(values["maximum_rails"]),
        )
    if kind is FinalCipherKind.SUBSTITUTION:
        return KeySpec.permutation(length=int(values["alphabet_size"]))
    if kind is FinalCipherKind.PERIODIC_SUBSTITUTION:
        return KeySpec.periodic_substitution(
            period=int(values["period"]),
            alphabet_size=int(values["alphabet_size"]),
        )
    if kind is FinalCipherKind.PERIODIC_COLUMNAR:
        return KeySpec.periodic_columnar(
            period=int(values["period"]),
            columns=int(values["columns"]),
            alphabet_size=int(values["alphabet_size"]),
        )
    if kind in {FinalCipherKind.TWO_PERIOD_VIGENERE, FinalCipherKind.TWO_PERIOD_STREAMS}:
        return KeySpec.repeating(
            length=int(values["first_period"]) + int(values["second_period"])
        )
    raise ValueError(f"unsupported known-key cipher: {kind.value}")


def _non_invertible_error(cipher: CipherSpec, operation: str) -> NonInvertibleCipherError:
    from rdp.api.stop_reason_contract import (
        CanonicalStopReason,
        ExecutionStatus,
        RunStatus,
        StopCategory,
    )

    issue = CapabilityIssue(
        code="cipher_operation_unavailable",
        message=f"{cipher.kind.value} does not support {operation}",
        status=CapabilityStatus.UNSUPPORTED,
        source=cipher.kind.value,
    )
    status = RunStatus(
        execution_status=ExecutionStatus.BLOCKED_BEFORE_RUN,
        stop_category=StopCategory.BLOCKED_BEFORE_RUN,
        stop_reason=CanonicalStopReason.CONFIG_INVALID,
        stop_detail=issue.message,
    )
    return NonInvertibleCipherError(issue.message, status=status, issues=(issue,))


__all__ = ["decrypt", "encrypt"]
