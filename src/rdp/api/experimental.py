"""Typed experimental two-input and lookup cipher definitions."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from enum import StrEnum

from rdp.api.specs import CipherSpec
from rdp.ciphers.generic_map_cipher import (
    function_id,
    register_function,
    validate_function,
    validate_lookup_table,
)
from rdp.core.types import RuntimeCipherKind


class DegeneracyPolicy(StrEnum):
    ALLOW = "allow"
    FORBID = "forbid"


class ResolverMode(StrEnum):
    EXPAND_BEAM = "expand_beam"
    FIRST = "first"


def define_cipher_map(
    function: Callable[[int, int], int],
    /,
    *,
    alphabet_size: int = 29,
    degeneracy: DegeneracyPolicy = DegeneracyPolicy.FORBID,
    resolver: ResolverMode = ResolverMode.FIRST,
    per_position_limit: int = 29,
    resolver_limit: int = 8_193,
    name: str | None = None,
) -> CipherSpec:
    """Define one typed two-input experimental cipher map."""
    validate_function(function)
    values = _validated_options(
        alphabet_size=alphabet_size,
        degeneracy=degeneracy,
        resolver=resolver,
        per_position_limit=per_position_limit,
        resolver_limit=resolver_limit,
        name=name,
    )
    definition_id = function_id(function)
    values.update(definition_kind="function", definition_id=definition_id)
    spec = CipherSpec._create(RuntimeCipherKind.USER_MAP2, values)  # type: ignore[arg-type]
    registered_id = register_function(function)
    if registered_id != definition_id:  # pragma: no cover - defensive invariant
        raise RuntimeError("experimental map callable identity changed during registration")
    return spec


def define_cipher_lookup(
    table: Sequence[Sequence[int]],
    /,
    *,
    alphabet_size: int = 29,
    degeneracy: DegeneracyPolicy = DegeneracyPolicy.FORBID,
    resolver: ResolverMode = ResolverMode.FIRST,
    per_position_limit: int = 29,
    resolver_limit: int = 8_193,
    name: str | None = None,
) -> CipherSpec:
    """Define one typed experimental lookup cipher."""
    values = _validated_options(
        alphabet_size=alphabet_size,
        degeneracy=degeneracy,
        resolver=resolver,
        per_position_limit=per_position_limit,
        resolver_limit=resolver_limit,
        name=name,
    )
    rows = validate_lookup_table(table, alphabet_size=alphabet_size)
    values.update(definition_kind="lookup", table=rows)
    return CipherSpec._create(RuntimeCipherKind.LOOKUP, values)  # type: ignore[arg-type]


def _validated_options(
    *,
    alphabet_size: int,
    degeneracy: DegeneracyPolicy,
    resolver: ResolverMode,
    per_position_limit: int,
    resolver_limit: int,
    name: str | None,
) -> dict[str, object]:
    for field_name, value, minimum in (
        ("alphabet_size", alphabet_size, 2),
        ("per_position_limit", per_position_limit, 1),
        ("resolver_limit", resolver_limit, 1),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{field_name} must be an integer")
        if value < minimum:
            raise ValueError(f"{field_name} must be >= {minimum}")
    if not isinstance(degeneracy, DegeneracyPolicy):
        raise TypeError("degeneracy must be DegeneracyPolicy")
    if not isinstance(resolver, ResolverMode):
        raise TypeError("resolver must be ResolverMode")
    if name is not None and (not isinstance(name, str) or not name):
        raise ValueError("name must be a non-empty string or None")
    return {
        "alphabet_size": alphabet_size,
        "degeneracy": degeneracy,
        "resolver": resolver,
        "per_position_limit": per_position_limit,
        "resolver_limit": resolver_limit,
        "name": name,
    }


__all__ = [
    "DegeneracyPolicy",
    "ResolverMode",
    "define_cipher_lookup",
    "define_cipher_map",
]
