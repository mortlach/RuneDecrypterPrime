"""Immutable public cipher, key-space, and solver specifications."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from numbers import Integral, Real
from typing import Any, ClassVar

from rune_decrypter_prime.core.component_contracts import UnsupportedConfigurationError
from rune_decrypter_prime.core.types import (
    BeamExpansionMode,
    FinalCipherKind as CipherKind,
    FinalKeyKind as KeyKind,
    FrozenParameterItems,
    JsonObject,
    JsonValue,
    KaedingBlockSchedule,
    KaedingSlipPolicy,
    PeriodicColumnarOrder,
    ScheduledStreamOperation,
    ScheduledStreamSchedule,
    SolverKind,
    freeze_parameter_items,
    readonly_parameters,
    replay_key,
    thaw_parameter_items,
)


def _strict_int(value: object, field_name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{field_name} must be an integer")
    result = int(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    return result


def _optional_int(value: object, field_name: str, *, minimum: int | None = None) -> int | None:
    return None if value is None else _strict_int(value, field_name, minimum=minimum)


def _finite_float(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a finite float")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be finite")
    return 0.0 if result == 0.0 else result


def _optional_float(value: object, field_name: str) -> float | None:
    return None if value is None else _finite_float(value, field_name)


def _strict_bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{field_name} must be a bool")
    return value


def _strict_enum(value: object, enum_type: type[Enum], field_name: str) -> Enum:
    if not isinstance(value, enum_type):
        raise TypeError(f"{field_name} must be {enum_type.__name__}")
    return value


def _parse_enum(value: object, enum_type: type[Enum], field_name: str) -> Enum:
    if isinstance(value, enum_type):
        return value
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a serialized {enum_type.__name__} value")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise UnsupportedConfigurationError(
            f"unsupported {field_name} {value!r}", field_paths=(field_name,)
        ) from exc


def _strict_sequence(value: object, field_name: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise TypeError(f"{field_name} must be an ordered sequence")
    return value


def _strict_int_tuple(
    value: object,
    field_name: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
    non_empty: bool = False,
) -> tuple[int, ...]:
    values = tuple(
        _strict_int(item, f"{field_name}[{index}]", minimum=minimum)
        for index, item in enumerate(_strict_sequence(value, field_name))
    )
    if non_empty and not values:
        raise ValueError(f"{field_name} must not be empty")
    if maximum is not None:
        for index, item in enumerate(values):
            if item > maximum:
                raise ValueError(f"{field_name}[{index}] must be <= {maximum}")
    return values


def _mapping_or_empty(value: JsonObject | None, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping or None")
    if any(not isinstance(key, str) for key in value):
        raise TypeError(f"{field_name} keys must be strings")
    return dict(value)


class _ImmutableSpec:
    _REPLAY_PREFIX: ClassVar[str]
    _PAIR_SEQUENCE_KEYS: ClassVar[frozenset[str]] = frozenset()

    @property
    def parameters(self) -> Mapping[str, JsonValue]:
        return readonly_parameters(
            self._parameter_items, pair_sequence_keys=self._PAIR_SEQUENCE_KEYS
        )  # type: ignore[return-value]

    def _json_parameters(self) -> dict[str, JsonValue]:
        return thaw_parameter_items(
            self._parameter_items,
            json_compatible=True,
            pair_sequence_keys=self._PAIR_SEQUENCE_KEYS,
        )  # type: ignore[return-value]

    @property
    def replay_key(self) -> str:
        return replay_key(self._REPLAY_PREFIX, self.to_dict())

    def __copy__(self) -> _ImmutableSpec:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> _ImmutableSpec:
        return self

    def __repr__(self) -> str:
        seed = f", seed={self.seed!r}" if hasattr(self, "seed") else ""
        return (
            f"{type(self).__name__}(kind={self.kind!r}{seed}, "
            f"parameters={dict(self.parameters)!r})"
        )


@dataclass(frozen=True, slots=True, init=False, repr=False)
class CipherSpec(_ImmutableSpec):
    kind: CipherKind
    _parameter_items: FrozenParameterItems = field(repr=False)

    _REPLAY_PREFIX: ClassVar[str] = "cipher-spec"

    @classmethod
    def _create(cls, kind: CipherKind, parameters: Mapping[str, object]) -> CipherSpec:
        instance = object.__new__(cls)
        object.__setattr__(instance, "kind", kind)
        object.__setattr__(instance, "_parameter_items", freeze_parameter_items(parameters))
        return instance

    @staticmethod
    def _alphabet(value: object) -> int:
        return _strict_int(value, "alphabet_size", minimum=2)

    @classmethod
    def vigenere(cls, *, alphabet_size: int = 29) -> CipherSpec:
        return cls._create(CipherKind.VIGENERE, {"alphabet_size": cls._alphabet(alphabet_size)})

    @classmethod
    def autokey(cls, *, alphabet_size: int = 29) -> CipherSpec:
        return cls._create(CipherKind.AUTOKEY, {"alphabet_size": cls._alphabet(alphabet_size)})

    @classmethod
    def columnar(cls, *, columns: int, alphabet_size: int = 29) -> CipherSpec:
        return cls._create(CipherKind.COLUMNAR, {
            "columns": _strict_int(columns, "columns", minimum=1),
            "alphabet_size": cls._alphabet(alphabet_size),
        })

    @classmethod
    def rail_fence(
        cls,
        *,
        minimum_rails: int = 2,
        maximum_rails: int = 8,
        alphabet_size: int = 29,
    ) -> CipherSpec:
        low = _strict_int(minimum_rails, "minimum_rails", minimum=2)
        high = _strict_int(maximum_rails, "maximum_rails", minimum=2)
        if low > high:
            raise ValueError("minimum_rails must not exceed maximum_rails")
        return cls._create(CipherKind.RAIL_FENCE, {
            "minimum_rails": low,
            "maximum_rails": high,
            "alphabet_size": cls._alphabet(alphabet_size),
        })

    @classmethod
    def substitution(cls, *, alphabet_size: int = 29) -> CipherSpec:
        return cls._create(CipherKind.SUBSTITUTION, {"alphabet_size": cls._alphabet(alphabet_size)})

    @classmethod
    def periodic_substitution(cls, *, period: int, alphabet_size: int = 29) -> CipherSpec:
        return cls._create(CipherKind.PERIODIC_SUBSTITUTION, {
            "period": _strict_int(period, "period", minimum=1),
            "alphabet_size": cls._alphabet(alphabet_size),
        })

    @classmethod
    def periodic_columnar(
        cls,
        *,
        period: int,
        columns: int,
        order: PeriodicColumnarOrder = PeriodicColumnarOrder.SUBSTITUTION_THEN_COLUMNAR,
        alphabet_size: int = 29,
    ) -> CipherSpec:
        _strict_enum(order, PeriodicColumnarOrder, "order")
        return cls._create(CipherKind.PERIODIC_COLUMNAR, {
            "period": _strict_int(period, "period", minimum=1),
            "columns": _strict_int(columns, "columns", minimum=1),
            "order": order,
            "alphabet_size": cls._alphabet(alphabet_size),
        })

    @staticmethod
    def _schedule_mask(
        schedule: ScheduledStreamSchedule,
        mask: Sequence[int] | None,
    ) -> tuple[int, ...] | None:
        _strict_enum(schedule, ScheduledStreamSchedule, "schedule")
        if schedule is ScheduledStreamSchedule.MASK:
            if mask is None:
                raise ValueError("mask is required when schedule is MASK")
            return _strict_int_tuple(mask, "mask", maximum=3, non_empty=True)
        if mask is not None:
            raise ValueError("mask is supported only when schedule is MASK")
        return None

    @classmethod
    def two_period_vigenere(
        cls,
        *,
        first_period: int = 13,
        second_period: int = 31,
        schedule: ScheduledStreamSchedule = ScheduledStreamSchedule.OVERLAY,
        mask: Sequence[int] | None = None,
        alphabet_size: int = 29,
    ) -> CipherSpec:
        return cls._create(CipherKind.TWO_PERIOD_VIGENERE, {
            "first_period": _strict_int(first_period, "first_period", minimum=1),
            "second_period": _strict_int(second_period, "second_period", minimum=1),
            "schedule": _strict_enum(schedule, ScheduledStreamSchedule, "schedule"),
            "mask": cls._schedule_mask(schedule, mask),
            "alphabet_size": cls._alphabet(alphabet_size),
        })

    @classmethod
    def periodic_with_fixed_stream(
        cls,
        fixed_stream: Sequence[int],
        /,
        *,
        period: int = 13,
        alphabet_size: int = 29,
    ) -> CipherSpec:
        alphabet = cls._alphabet(alphabet_size)
        stream = _strict_int_tuple(fixed_stream, "fixed_stream", maximum=alphabet - 1, non_empty=True)
        return cls._create(CipherKind.PERIODIC_WITH_FIXED_STREAM, {
            "fixed_stream": stream,
            "period": _strict_int(period, "period", minimum=1),
            "alphabet_size": alphabet,
        })

    @classmethod
    def periodic_with_prime_stream(
        cls,
        *,
        period: int = 13,
        prime_offset: int = 0,
        alphabet_size: int = 29,
    ) -> CipherSpec:
        return cls._create(CipherKind.PERIODIC_WITH_PRIME_STREAM, {
            "period": _strict_int(period, "period", minimum=1),
            "prime_offset": _strict_int(prime_offset, "prime_offset", minimum=0),
            "alphabet_size": cls._alphabet(alphabet_size),
        })

    @classmethod
    def two_period_streams(
        cls,
        *,
        first_period: int = 13,
        second_period: int = 31,
        operation: ScheduledStreamOperation = ScheduledStreamOperation.ADD,
        schedule: ScheduledStreamSchedule = ScheduledStreamSchedule.OVERLAY,
        mask: Sequence[int] | None = None,
        alphabet_size: int = 29,
    ) -> CipherSpec:
        _strict_enum(operation, ScheduledStreamOperation, "operation")
        return cls._create(CipherKind.TWO_PERIOD_STREAMS, {
            "first_period": _strict_int(first_period, "first_period", minimum=1),
            "second_period": _strict_int(second_period, "second_period", minimum=1),
            "operation": operation,
            "schedule": _strict_enum(schedule, ScheduledStreamSchedule, "schedule"),
            "mask": cls._schedule_mask(schedule, mask),
            "alphabet_size": cls._alphabet(alphabet_size),
        })

    @classmethod
    def from_name(
        cls,
        name: str,
        /,
        *,
        parameters: JsonObject | None = None,
    ) -> CipherSpec:
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        values = _mapping_or_empty(parameters, "parameters")
        constructors: dict[str, tuple[object, dict[str, type[Enum]]]] = {
            "vigenere": (cls.vigenere, {}),
            "autokey": (cls.autokey, {}),
            "columnar": (cls.columnar, {}),
            "rail_fence": (cls.rail_fence, {}),
            "substitution": (cls.substitution, {}),
            "periodic_substitution": (cls.periodic_substitution, {}),
            "periodic_columnar": (cls.periodic_columnar, {"order": PeriodicColumnarOrder}),
            "two_period_vigenere": (cls.two_period_vigenere, {"schedule": ScheduledStreamSchedule}),
            "periodic_with_fixed_stream": (cls.periodic_with_fixed_stream, {}),
            "periodic_with_prime_stream": (cls.periodic_with_prime_stream, {}),
            "two_period_streams": (cls.two_period_streams, {
                "operation": ScheduledStreamOperation,
                "schedule": ScheduledStreamSchedule,
            }),
        }
        if name not in constructors:
            raise UnsupportedConfigurationError(f"unsupported cipher name {name!r}", field_paths=("name",))
        constructor, enum_fields = constructors[name]
        for key, enum_type in enum_fields.items():
            if key in values:
                values[key] = _parse_enum(values[key], enum_type, f"parameters.{key}")
        try:
            if name == "periodic_with_fixed_stream":
                stream = values.pop("fixed_stream")
                return cls.periodic_with_fixed_stream(stream, **values)
            return constructor(**values)  # type: ignore[operator]
        except (KeyError, TypeError) as exc:
            raise UnsupportedConfigurationError(
                f"invalid parameters for cipher {name!r}: {exc}", field_paths=("parameters",)
            ) from exc

    def to_dict(self) -> dict[str, JsonValue]:
        return {"kind": self.kind.value, "parameters": self._json_parameters()}

    # Existing internal projections are removed after the AN3.6 caller cutover.
    @property
    def name(self) -> str:
        return self.kind.value

    @property
    def N(self) -> int:
        return int(self.parameters["alphabet_size"])

    @property
    def extra(self) -> dict[str, object]:
        return dict(self.parameters)

    @property
    def wrapper_core(self) -> str:
        return self.kind.value

    @property
    def device(self) -> None:
        return None


@dataclass(frozen=True, slots=True, init=False, repr=False)
class KeySpec(_ImmutableSpec):
    kind: KeyKind
    _parameter_items: FrozenParameterItems = field(repr=False)

    _REPLAY_PREFIX: ClassVar[str] = "key-spec"

    @classmethod
    def _create(cls, kind: KeyKind, parameters: Mapping[str, object]) -> KeySpec:
        instance = object.__new__(cls)
        object.__setattr__(instance, "kind", kind)
        object.__setattr__(instance, "_parameter_items", freeze_parameter_items(parameters))
        return instance

    @classmethod
    def repeating(cls, *, length: int) -> KeySpec:
        return cls._create(KeyKind.REPEATING, {"length": _strict_int(length, "length", minimum=1)})

    @classmethod
    def repeating_range(cls, *, minimum_length: int, maximum_length: int) -> KeySpec:
        low = _strict_int(minimum_length, "minimum_length", minimum=1)
        high = _strict_int(maximum_length, "maximum_length", minimum=1)
        if low > high:
            raise ValueError("minimum_length must not exceed maximum_length")
        return cls._create(KeyKind.REPEATING_RANGE, {"minimum_length": low, "maximum_length": high})

    @classmethod
    def permutation(cls, *, length: int) -> KeySpec:
        return cls._create(KeyKind.PERMUTATION, {"length": _strict_int(length, "length", minimum=1)})

    @classmethod
    def scalar(cls, *, minimum: int, maximum: int) -> KeySpec:
        low = _strict_int(minimum, "minimum")
        high = _strict_int(maximum, "maximum")
        if low > high:
            raise ValueError("minimum must not exceed maximum")
        return cls._create(KeyKind.SCALAR, {"minimum": low, "maximum": high})

    @classmethod
    def periodic_substitution(cls, *, period: int, alphabet_size: int = 29) -> KeySpec:
        return cls._create(KeyKind.PERIODIC_SUBSTITUTION, {
            "period": _strict_int(period, "period", minimum=1),
            "alphabet_size": _strict_int(alphabet_size, "alphabet_size", minimum=2),
        })

    @classmethod
    def periodic_columnar(
        cls,
        *,
        period: int,
        columns: int,
        alphabet_size: int = 29,
    ) -> KeySpec:
        return cls._create(KeyKind.PERIODIC_COLUMNAR, {
            "period": _strict_int(period, "period", minimum=1),
            "columns": _strict_int(columns, "columns", minimum=1),
            "alphabet_size": _strict_int(alphabet_size, "alphabet_size", minimum=2),
        })

    def with_fixed_alignment(self, *, offset: int) -> KeySpec:
        self._require_alignment_capability()
        parameters = dict(self.parameters)
        parameters["alignment"] = ("fixed", _strict_int(offset, "offset"))
        return self._create(self.kind, parameters)

    def with_alignment_search(self, *, minimum_offset: int, maximum_offset: int) -> KeySpec:
        self._require_alignment_capability()
        low = _strict_int(minimum_offset, "minimum_offset")
        high = _strict_int(maximum_offset, "maximum_offset")
        if low > high:
            raise ValueError("minimum_offset must not exceed maximum_offset")
        parameters = dict(self.parameters)
        parameters["alignment"] = {"minimum_offset": low, "maximum_offset": high}
        return self._create(self.kind, parameters)

    def _require_alignment_capability(self) -> None:
        if self.kind not in {KeyKind.REPEATING, KeyKind.REPEATING_RANGE}:
            raise UnsupportedConfigurationError(
                f"{self.kind.value} keys do not support alignment", field_paths=("alignment",)
            )

    @classmethod
    def from_name(
        cls,
        name: str,
        /,
        *,
        parameters: JsonObject | None = None,
    ) -> KeySpec:
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        values = _mapping_or_empty(parameters, "parameters")
        alignment = values.pop("alignment", None)
        constructors = {
            "repeating": cls.repeating,
            "repeating_range": cls.repeating_range,
            "permutation": cls.permutation,
            "scalar": cls.scalar,
            "periodic_substitution": cls.periodic_substitution,
            "periodic_columnar": cls.periodic_columnar,
        }
        constructor = constructors.get(name)
        if constructor is None:
            raise UnsupportedConfigurationError(f"unsupported key name {name!r}", field_paths=("name",))
        try:
            spec = constructor(**values)
        except TypeError as exc:
            raise UnsupportedConfigurationError(
                f"invalid parameters for key {name!r}: {exc}", field_paths=("parameters",)
            ) from exc
        if alignment is None:
            return spec
        if isinstance(alignment, Sequence) and not isinstance(alignment, (str, bytes)):
            items = tuple(alignment)
            if len(items) == 2 and items[0] == "fixed":
                return spec.with_fixed_alignment(offset=items[1])
        if isinstance(alignment, Mapping) and set(alignment) == {"minimum_offset", "maximum_offset"}:
            return spec.with_alignment_search(
                minimum_offset=alignment["minimum_offset"],
                maximum_offset=alignment["maximum_offset"],
            )
        raise UnsupportedConfigurationError("invalid serialized alignment", field_paths=("parameters.alignment",))

    def to_dict(self) -> dict[str, JsonValue]:
        return {"kind": self.kind.value, "parameters": self._json_parameters()}

    @property
    def plan(self) -> str:
        return {
            KeyKind.REPEATING: "repeat",
            KeyKind.REPEATING_RANGE: "repeat_range",
            KeyKind.PERMUTATION: "perm",
            KeyKind.SCALAR: "scalar",
            KeyKind.PERIODIC_SUBSTITUTION: "periodic_structured",
            KeyKind.PERIODIC_COLUMNAR: "periodic_structured",
        }[self.kind]

    @property
    def params(self) -> dict[str, object]:
        aliases = {
            "length": "len",
            "minimum_length": "min",
            "maximum_length": "max",
            "minimum": "min",
            "maximum": "max",
        }
        return {
            aliases.get(key, key): value
            for key, value in self.parameters.items()
            if key != "alignment"
        }

    @property
    def _align_offset(self) -> object:
        return self.parameters.get("alignment")

    def period_hint(self) -> int | None:
        return int(self.parameters["length"]) if self.kind is KeyKind.REPEATING else None

    def to_telemetry(self) -> dict[str, object]:
        return {"plan": self.plan, **self.params}

    @classmethod
    def repeat(cls, *, len: int) -> KeySpec:
        return cls.repeating(length=len)

    @classmethod
    def repeat_range(cls, *, min: int, max: int) -> KeySpec:
        return cls.repeating_range(minimum_length=min, maximum_length=max)

    @classmethod
    def periodic_structured(
        cls,
        *,
        period: int,
        alphabet_size: int = 29,
        columns: int | None = None,
    ) -> KeySpec:
        if columns is None:
            return cls.periodic_substitution(period=period, alphabet_size=alphabet_size)
        return cls.periodic_columnar(period=period, columns=columns, alphabet_size=alphabet_size)

    def align(self, *, offset: int | tuple[str, int, int]) -> KeySpec:
        if isinstance(offset, tuple) and len(offset) == 3 and offset[0] == "search":
            return self.with_alignment_search(minimum_offset=offset[1], maximum_offset=offset[2])
        return self.with_fixed_alignment(offset=offset)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True, init=False, repr=False)
class SolverSpec(_ImmutableSpec):
    kind: SolverKind
    seed: int | None
    _parameter_items: FrozenParameterItems = field(repr=False)

    _REPLAY_PREFIX: ClassVar[str] = "solver-spec"
    _PAIR_SEQUENCE_KEYS: ClassVar[frozenset[str]] = frozenset({"fixed_cribs"})

    @classmethod
    def _create(
        cls,
        kind: SolverKind,
        seed: int | None,
        parameters: Mapping[str, object],
    ) -> SolverSpec:
        instance = object.__new__(cls)
        object.__setattr__(instance, "kind", kind)
        object.__setattr__(instance, "seed", _optional_int(seed, "seed"))
        object.__setattr__(instance, "_parameter_items", freeze_parameter_items(parameters))
        return instance

    @classmethod
    def beam_search(
        cls,
        *,
        width: int,
        rounds: int,
        restarts: int = 1,
        expansion: BeamExpansionMode = BeamExpansionMode.SWEEP,
        maximum_children_per_parent: int | None = None,
        sample_per_parent: int | None = None,
        top_parents_fraction: float = 0.5,
        plateau_rounds: int | None = None,
        plateau_minimum_delta: float = 0.0,
        target_score: float | None = None,
        seed: int | None = None,
    ) -> SolverSpec:
        _strict_enum(expansion, BeamExpansionMode, "expansion")
        fraction = _finite_float(top_parents_fraction, "top_parents_fraction")
        if not 0.0 < fraction <= 1.0:
            raise ValueError("top_parents_fraction must be in (0, 1]")
        return cls._create(SolverKind.BEAM_SEARCH, seed, {
            "width": _strict_int(width, "width", minimum=1),
            "rounds": _strict_int(rounds, "rounds", minimum=0),
            "restarts": _strict_int(restarts, "restarts", minimum=1),
            "expansion": expansion,
            "maximum_children_per_parent": _optional_int(maximum_children_per_parent, "maximum_children_per_parent", minimum=1),
            "sample_per_parent": _optional_int(sample_per_parent, "sample_per_parent", minimum=1),
            "top_parents_fraction": fraction,
            "plateau_rounds": _optional_int(plateau_rounds, "plateau_rounds", minimum=1),
            "plateau_minimum_delta": _finite_float(plateau_minimum_delta, "plateau_minimum_delta"),
            "target_score": _optional_float(target_score, "target_score"),
        })

    @classmethod
    def genetic_algorithm(
        cls,
        *,
        population_size: int,
        generations: int,
        elite_fraction: float = 0.1,
        mutation_probability: float = 0.2,
        crossover_fraction: float = 0.8,
        tournament_size: int = 3,
        plateau_generations: int | None = None,
        plateau_minimum_delta: float = 0.0,
        target_score: float | None = None,
        seed: int | None = None,
    ) -> SolverSpec:
        fractions = {
            "elite_fraction": _finite_float(elite_fraction, "elite_fraction"),
            "mutation_probability": _finite_float(mutation_probability, "mutation_probability"),
            "crossover_fraction": _finite_float(crossover_fraction, "crossover_fraction"),
        }
        if any(not 0.0 <= value <= 1.0 for value in fractions.values()):
            raise ValueError("genetic algorithm fractions must be in [0, 1]")
        return cls._create(SolverKind.GENETIC_ALGORITHM, seed, {
            "population_size": _strict_int(population_size, "population_size", minimum=1),
            "generations": _strict_int(generations, "generations", minimum=1),
            **fractions,
            "tournament_size": _strict_int(tournament_size, "tournament_size", minimum=2),
            "plateau_generations": _optional_int(plateau_generations, "plateau_generations", minimum=1),
            "plateau_minimum_delta": _finite_float(plateau_minimum_delta, "plateau_minimum_delta"),
            "target_score": _optional_float(target_score, "target_score"),
        })

    @classmethod
    def simulated_annealing(
        cls,
        *,
        iterations: int,
        initial_temperature: float | None = None,
        minimum_temperature: float | None = None,
        cooling_rate: float | None = None,
        automatic_cooling: bool = False,
        reseed_interval: int | None = None,
        local_improvement_on_accept: bool = False,
        rescue_drop_absolute: float | None = None,
        rescue_drop_ratio: float | None = None,
        plateau_iterations: int | None = None,
        plateau_minimum_delta: float = 0.0,
        target_score: float | None = None,
        seed: int | None = None,
    ) -> SolverSpec:
        return cls._create(SolverKind.SIMULATED_ANNEALING, seed, {
            "iterations": _strict_int(iterations, "iterations", minimum=1),
            "initial_temperature": _optional_float(initial_temperature, "initial_temperature"),
            "minimum_temperature": _optional_float(minimum_temperature, "minimum_temperature"),
            "cooling_rate": _optional_float(cooling_rate, "cooling_rate"),
            "automatic_cooling": _strict_bool(automatic_cooling, "automatic_cooling"),
            "reseed_interval": _optional_int(reseed_interval, "reseed_interval", minimum=0),
            "local_improvement_on_accept": _strict_bool(local_improvement_on_accept, "local_improvement_on_accept"),
            "rescue_drop_absolute": _optional_float(rescue_drop_absolute, "rescue_drop_absolute"),
            "rescue_drop_ratio": _optional_float(rescue_drop_ratio, "rescue_drop_ratio"),
            "plateau_iterations": _optional_int(plateau_iterations, "plateau_iterations", minimum=1),
            "plateau_minimum_delta": _finite_float(plateau_minimum_delta, "plateau_minimum_delta"),
            "target_score": _optional_float(target_score, "target_score"),
        })

    @classmethod
    def hybrid(
        cls,
        *,
        genetic_algorithm: SolverSpec,
        simulated_annealing: SolverSpec,
        use_beam_search: bool = True,
        beam_width: int | None = None,
        beam_rounds: int | None = None,
        beam_expansion: BeamExpansionMode = BeamExpansionMode.SWEEP,
        sample_per_parent: int | None = None,
        top_parents_fraction: float = 0.5,
        plateau_rounds: int | None = None,
        plateau_minimum_delta: float = 0.0,
        target_score: float | None = None,
        seed: int | None = None,
    ) -> SolverSpec:
        if not isinstance(genetic_algorithm, SolverSpec) or genetic_algorithm.kind is not SolverKind.GENETIC_ALGORITHM:
            raise TypeError("genetic_algorithm must be a genetic-algorithm SolverSpec")
        if not isinstance(simulated_annealing, SolverSpec) or simulated_annealing.kind is not SolverKind.SIMULATED_ANNEALING:
            raise TypeError("simulated_annealing must be a simulated-annealing SolverSpec")
        _strict_enum(beam_expansion, BeamExpansionMode, "beam_expansion")
        fraction = _finite_float(top_parents_fraction, "top_parents_fraction")
        if not 0.0 < fraction <= 1.0:
            raise ValueError("top_parents_fraction must be in (0, 1]")
        return cls._create(SolverKind.HYBRID, seed, {
            "genetic_algorithm": genetic_algorithm.to_dict(),
            "simulated_annealing": simulated_annealing.to_dict(),
            "use_beam_search": _strict_bool(use_beam_search, "use_beam_search"),
            "beam_width": _optional_int(beam_width, "beam_width", minimum=1),
            "beam_rounds": _optional_int(beam_rounds, "beam_rounds", minimum=0),
            "beam_expansion": beam_expansion,
            "sample_per_parent": _optional_int(sample_per_parent, "sample_per_parent", minimum=1),
            "top_parents_fraction": fraction,
            "plateau_rounds": _optional_int(plateau_rounds, "plateau_rounds", minimum=1),
            "plateau_minimum_delta": _finite_float(plateau_minimum_delta, "plateau_minimum_delta"),
            "target_score": _optional_float(target_score, "target_score"),
        })

    @classmethod
    def kaeding(
        cls,
        *,
        steps: int,
        restarts: int,
        inner_batch_size: int,
        block_schedule: KaedingBlockSchedule = KaedingBlockSchedule.ROUND_ROBIN,
        column_batch_size: int = 0,
        column_interval: int = 0,
        slip_blocks: int = 0,
        slip_interval: int = 0,
        slip_policy: KaedingSlipPolicy = KaedingSlipPolicy.FIXED_INTERVAL,
        slip_swaps: int = 0,
        stall_rounds: int = 0,
        stall_slip_limit: int = 0,
        stop_after_stall_slip_limit: bool = False,
        plateau_rounds: int | None = None,
        plateau_minimum_delta: float = 0.0,
        target_score: float | None = None,
        seed: int | None = None,
    ) -> SolverSpec:
        _strict_enum(block_schedule, KaedingBlockSchedule, "block_schedule")
        _strict_enum(slip_policy, KaedingSlipPolicy, "slip_policy")
        return cls._create(SolverKind.KAEDING, seed, {
            "steps": _strict_int(steps, "steps", minimum=1),
            "restarts": _strict_int(restarts, "restarts", minimum=1),
            "inner_batch_size": _strict_int(inner_batch_size, "inner_batch_size", minimum=1),
            "block_schedule": block_schedule,
            "column_batch_size": _strict_int(column_batch_size, "column_batch_size", minimum=0),
            "column_interval": _strict_int(column_interval, "column_interval", minimum=0),
            "slip_blocks": _strict_int(slip_blocks, "slip_blocks", minimum=0),
            "slip_interval": _strict_int(slip_interval, "slip_interval", minimum=0),
            "slip_policy": slip_policy,
            "slip_swaps": _strict_int(slip_swaps, "slip_swaps", minimum=0),
            "stall_rounds": _strict_int(stall_rounds, "stall_rounds", minimum=0),
            "stall_slip_limit": _strict_int(stall_slip_limit, "stall_slip_limit", minimum=0),
            "stop_after_stall_slip_limit": _strict_bool(stop_after_stall_slip_limit, "stop_after_stall_slip_limit"),
            "plateau_rounds": _optional_int(plateau_rounds, "plateau_rounds", minimum=1),
            "plateau_minimum_delta": _finite_float(plateau_minimum_delta, "plateau_minimum_delta"),
            "target_score": _optional_float(target_score, "target_score"),
        })

    @classmethod
    def two_period_cribs(
        cls,
        *,
        fixed_cribs: Sequence[tuple[str, int]] = (),
        candidate_words: Sequence[str] = (),
        candidate_positions: Mapping[str, Sequence[int]] | None = None,
        starts: int = 96,
        seed: int | None = None,
    ) -> SolverSpec:
        copied_cribs: list[tuple[str, int]] = []
        for index, item in enumerate(_strict_sequence(fixed_cribs, "fixed_cribs")):
            if not isinstance(item, Sequence) or isinstance(item, (str, bytes)) or len(item) != 2:
                raise TypeError(f"fixed_cribs[{index}] must be a (word, position) pair")
            word, position = item
            if not isinstance(word, str) or not word:
                raise ValueError(f"fixed_cribs[{index}].word must be non-empty")
            copied_cribs.append((word, _strict_int(position, f"fixed_cribs[{index}].position", minimum=0)))
        words = tuple(candidate_words)
        if any(not isinstance(word, str) or not word for word in words):
            raise ValueError("candidate_words must contain non-empty strings")
        positions: dict[str, tuple[int, ...]] | None = None
        if candidate_positions is not None:
            if not isinstance(candidate_positions, Mapping):
                raise TypeError("candidate_positions must be a mapping or None")
            positions = {}
            for word, items in candidate_positions.items():
                if not isinstance(word, str) or not word:
                    raise ValueError("candidate_positions keys must be non-empty strings")
                positions[word] = _strict_int_tuple(items, f"candidate_positions.{word}", minimum=0)
        return cls._create(SolverKind.TWO_PERIOD_CRIBS, seed, {
            "fixed_cribs": tuple(copied_cribs),
            "candidate_words": words,
            "candidate_positions": positions,
            "starts": _strict_int(starts, "starts", minimum=1),
        })

    @classmethod
    def from_name(
        cls,
        name: str,
        /,
        *,
        parameters: JsonObject | None = None,
    ) -> SolverSpec:
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        values = _mapping_or_empty(parameters, "parameters")
        enum_fields: dict[str, dict[str, type[Enum]]] = {
            "beam_search": {"expansion": BeamExpansionMode},
            "genetic_algorithm": {},
            "simulated_annealing": {},
            "hybrid": {"beam_expansion": BeamExpansionMode},
            "kaeding": {"block_schedule": KaedingBlockSchedule, "slip_policy": KaedingSlipPolicy},
            "two_period_cribs": {},
        }
        constructors = {
            "beam_search": cls.beam_search,
            "genetic_algorithm": cls.genetic_algorithm,
            "simulated_annealing": cls.simulated_annealing,
            "hybrid": cls.hybrid,
            "kaeding": cls.kaeding,
            "two_period_cribs": cls.two_period_cribs,
        }
        constructor = constructors.get(name)
        if constructor is None:
            raise UnsupportedConfigurationError(f"unsupported solver name {name!r}", field_paths=("name",))
        for key, enum_type in enum_fields[name].items():
            if key in values:
                values[key] = _parse_enum(values[key], enum_type, f"parameters.{key}")
        if name == "hybrid":
            for key, nested_name in (
                ("genetic_algorithm", "genetic_algorithm"),
                ("simulated_annealing", "simulated_annealing"),
            ):
                nested = values.get(key)
                if isinstance(nested, Mapping):
                    nested_values = dict(nested)
                    nested_kind = nested_values.pop("kind", nested_name)
                    nested_seed = nested_values.pop("seed", None)
                    nested_parameters = nested_values.pop("parameters", nested_values)
                    parsed = cls.from_name(str(nested_kind), parameters=dict(nested_parameters))
                    if nested_seed is not None:
                        parsed = cls._create(parsed.kind, _strict_int(nested_seed, f"{key}.seed"), parsed.parameters)
                    values[key] = parsed
        seed = values.pop("seed", None)
        try:
            return constructor(seed=seed, **values)
        except TypeError as exc:
            raise UnsupportedConfigurationError(
                f"invalid parameters for solver {name!r}: {exc}", field_paths=("parameters",)
            ) from exc

    def to_dict(self) -> dict[str, JsonValue]:
        return {"kind": self.kind.value, "seed": self.seed, "parameters": self._json_parameters()}

    @property
    def name(self) -> str:
        return {
            SolverKind.BEAM_SEARCH: "beam",
            SolverKind.GENETIC_ALGORITHM: "ga",
            SolverKind.SIMULATED_ANNEALING: "sa",
            SolverKind.HYBRID: "hybrid",
            SolverKind.KAEDING: "kaeding",
            SolverKind.TWO_PERIOD_CRIBS: "two_period_cribs",
        }[self.kind]

    @property
    def params(self) -> dict[str, object]:
        mappings = {
            SolverKind.BEAM_SEARCH: {"width": "beam_width"},
            SolverKind.GENETIC_ALGORITHM: {"population_size": "pop_size"},
            SolverKind.SIMULATED_ANNEALING: {"iterations": "sa_iters"},
            SolverKind.KAEDING: {"inner_batch_size": "inner_batch"},
        }
        aliases = mappings.get(self.kind, {})
        return {aliases.get(key, key): value for key, value in self.parameters.items()}

    @classmethod
    def beam(cls, **parameters: Any) -> SolverSpec:
        from rune_decrypter_prime.api._resolve import resolve_optimizer_aliases

        seed = parameters.pop("seed", None)
        values = resolve_optimizer_aliases("beam", dict(parameters))
        width = values.pop("beam_width")
        rounds = values.pop("rounds", 0)
        expansion = _parse_enum(values.pop("expand_mode", "sweep"), BeamExpansionMode, "expansion")
        return cls.beam_search(width=width, rounds=rounds, expansion=expansion, seed=seed, **values)

    @classmethod
    def ga(cls, **parameters: Any) -> SolverSpec:
        from rune_decrypter_prime.api._resolve import resolve_optimizer_aliases

        seed = parameters.pop("seed", None)
        values = resolve_optimizer_aliases("ga", dict(parameters))
        return cls.genetic_algorithm(
            population_size=values.pop("pop_size"),
            generations=values.pop("generations"),
            seed=seed,
            **values,
        )

    @classmethod
    def sa(cls, **parameters: Any) -> SolverSpec:
        from rune_decrypter_prime.api._resolve import resolve_optimizer_aliases

        seed = parameters.pop("seed", None)
        values = resolve_optimizer_aliases("sa", dict(parameters))
        return cls.simulated_annealing(iterations=values.pop("sa_iters"), seed=seed, **values)


__all__ = ["CipherSpec", "KeySpec", "SolverSpec"]
