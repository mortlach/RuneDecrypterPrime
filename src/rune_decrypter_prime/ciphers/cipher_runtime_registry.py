"""Exact registry for internal runtime cipher constructors."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from rune_decrypter_prime.core.component_contracts import (
    CipherRegistrationError,
    ComponentKind,
    UnknownComponentError,
)

CipherRuntimeConstructor = Callable[[Any], Any]

_REGISTRY: dict[str, CipherRuntimeConstructor] = {}


def register_cipher(
    identity: str,
) -> Callable[[CipherRuntimeConstructor], CipherRuntimeConstructor]:
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
