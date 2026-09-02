"""Typed experimental two-input and lookup cipher definitions."""

from __future__ import annotations

import hashlib
import inspect
from collections.abc import Callable, Sequence
from enum import StrEnum

from rdp.api.specs import CipherSpec
from rdp.core.types import RuntimeCipherKind


class DegeneracyPolicy(StrEnum):
    ALLOW = "allow"
    FORBID = "forbid"


class ResolverMode(StrEnum):
    EXPAND_BEAM = "expand_beam"
    FIRST = "first"


_FUNCTIONS: dict[str, Callable[[int, int], int]] = {}


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
    _validate_function(function)
    values = _validated_options(
        alphabet_size=alphabet_size,
        degeneracy=degeneracy,
        resolver=resolver,
        per_position_limit=per_position_limit,
        resolver_limit=resolver_limit,
        name=name,
    )
    definition_id = _function_id(function)
    values.update(definition_kind="function", definition_id=definition_id)
    spec = CipherSpec._create(RuntimeCipherKind.USER_MAP2, values)  # type: ignore[arg-type]
    _FUNCTIONS[definition_id] = function
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
    rows = _validate_table(table, alphabet_size=alphabet_size)
    values.update(definition_kind="lookup", table=rows)
    return CipherSpec._create(RuntimeCipherKind.LOOKUP, values)  # type: ignore[arg-type]


def function_for(spec: CipherSpec) -> Callable[[int, int], int]:
    """Return the callable owned by an experimental map specification."""
    if not isinstance(spec, CipherSpec) or spec.kind is not RuntimeCipherKind.USER_MAP2:
        raise TypeError("spec must be an experimental two-input CipherSpec")
    definition_id = str(spec.parameters["definition_id"])
    try:
        return _FUNCTIONS[definition_id]
    except KeyError as exc:
        raise RuntimeError(
            "experimental map callable is not registered in this process; "
            "define the map before materializing it"
        ) from exc


def _validate_function(function: object) -> None:
    if not callable(function):
        raise TypeError("function must be callable")
    if not hasattr(function, "__code__"):
        raise TypeError("function must be a Python function with stable code identity")
    parameters = tuple(inspect.signature(function).parameters.values())
    if len(parameters) != 2 or any(
        parameter.kind
        not in {parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD}
        for parameter in parameters
    ):
        raise TypeError("function must accept exactly two positional inputs")


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


def _validate_table(
    table: Sequence[Sequence[int]],
    *,
    alphabet_size: int,
) -> tuple[tuple[int, ...], ...]:
    if isinstance(table, (str, bytes)) or not isinstance(table, Sequence):
        raise TypeError("table must be a sequence of rows")
    rows: list[tuple[int, ...]] = []
    for row_index, row in enumerate(table):
        if isinstance(row, (str, bytes)) or not isinstance(row, Sequence):
            raise TypeError(f"table[{row_index}] must be a sequence")
        values: list[int] = []
        for column_index, value in enumerate(row):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"table[{row_index}][{column_index}] must be an integer")
            if not 0 <= value < alphabet_size:
                raise ValueError(
                    f"table[{row_index}][{column_index}] must be in [0, {alphabet_size - 1}]"
                )
            values.append(value)
        if not values:
            raise ValueError(f"table[{row_index}] must not be empty")
        rows.append(tuple(values))
    if len(rows) != alphabet_size:
        raise ValueError(f"table must contain exactly {alphabet_size} rows")
    if len({len(row) for row in rows}) != 1:
        raise ValueError("table rows must have equal length")
    return tuple(rows)


def _function_id(function: Callable[[int, int], int]) -> str:
    code = function.__code__
    closure = tuple(repr(cell.cell_contents) for cell in (function.__closure__ or ()))
    payload = repr(
        (
            function.__module__,
            function.__qualname__,
            code.co_code,
            code.co_consts,
            closure,
        )
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


__all__ = [
    "DegeneracyPolicy",
    "ResolverMode",
    "define_cipher_lookup",
    "define_cipher_map",
]
