"""Exact registry for internal runtime cipher constructors."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from rdp.core.component_contracts import (
    CipherRegistrationError,
    ComponentKind,
    UnknownComponentError,
)
from rdp.ciphers.autokey_cipher import AutokeyCipher
from rdp.ciphers.columnar_transposition_cipher import ColumnarTranspositionCipher
from rdp.ciphers.generic_map_cipher import GenericMapCipher
from rdp.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rdp.ciphers.periodic_substitution_cipher import PeriodicSubstitutionCipher
from rdp.ciphers.railfence_cipher import RailFenceCipher
from rdp.ciphers.scheduled_stream_lookup_cipher import ScheduledStreamLookupCipher
from rdp.ciphers.substitution_cipher import SubstitutionCipher
from rdp.ciphers.vigenere_cipher import RuneVigenereCipher

CipherRuntimeConstructor = Callable[[Any], Any]

_REGISTRY: dict[str, CipherRuntimeConstructor] = {
    "autokey": AutokeyCipher,
    "columnar": ColumnarTranspositionCipher,
    "generic_map": GenericMapCipher,
    "periodic_columnar": PeriodicColumnarCipher,
    "periodic_substitution": PeriodicSubstitutionCipher,
    "rail_fence": RailFenceCipher,
    "scheduled_stream_lookup": ScheduledStreamLookupCipher,
    "substitution": SubstitutionCipher,
    "vigenere": RuneVigenereCipher,
}


def register_cipher(identity: str) -> Callable[[CipherRuntimeConstructor], CipherRuntimeConstructor]:
    if not isinstance(identity, str) or not identity:
        raise CipherRegistrationError(
            "cipher runtime identity must be a non-empty string",
            identity=str(identity),
            owner=__name__,
        )
    if identity != identity.strip().lower() or "-" in identity or " " in identity:
        raise CipherRegistrationError(
            "cipher runtime identity must be canonical snake_case",
            identity=identity,
            owner=__name__,
        )

    def register(constructor: CipherRuntimeConstructor) -> CipherRuntimeConstructor:
        if identity in _REGISTRY:
            raise CipherRegistrationError(
                f"cipher runtime {identity!r} is already registered",
                identity=identity,
                owner=f"{constructor.__module__}.{constructor.__qualname__}",
            )
        _REGISTRY[identity] = constructor
        return constructor

    return register


def has(identity: str) -> bool:
    return identity in _REGISTRY


def get(identity: str) -> CipherRuntimeConstructor:
    try:
        return _REGISTRY[identity]
    except KeyError as exc:
        raise UnknownComponentError(
            f"unknown cipher runtime {identity!r}",
            component_kind=ComponentKind.CIPHER,
            token=identity,
        ) from exc


def available() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


__all__ = ["CipherRuntimeConstructor", "available", "get", "has", "register_cipher"]
