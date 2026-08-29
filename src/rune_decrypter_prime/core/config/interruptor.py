"""Immutable interruptor request configuration."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from numbers import Integral
from typing import Any, ClassVar

from rune_decrypter_prime.core.component_contracts import UnsupportedConfigurationError
from rune_decrypter_prime.core.types import (
    FinalInterruptorSearchStrategy as InterruptorSearchStrategy,
    FrozenParameterItems,
    InterruptorMode,
    JsonObject,
    JsonValue,
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


def _positions(values: Sequence[int], field_name: str) -> tuple[int, ...]:
    if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, Sequence):
        raise TypeError(f"{field_name} must be an ordered sequence")
    copied = tuple(
        _strict_int(value, f"{field_name}[{index}]", minimum=0)
        for index, value in enumerate(values)
    )
    if not copied:
        raise ValueError(f"{field_name} must not be empty")
    if len(set(copied)) != len(copied):
        raise ValueError(f"{field_name} must not contain duplicates")
    return tuple(sorted(copied))


@dataclass(frozen=True, slots=True, init=False, repr=False)
class InterruptorConfig:
    mode: InterruptorMode
    _parameter_items: FrozenParameterItems = field(repr=False)

    _REPLAY_PREFIX: ClassVar[str] = "interruptor-config"

    @classmethod
    def _create(
        cls,
        mode: InterruptorMode,
        parameters: Mapping[str, object],
    ) -> InterruptorConfig:
        instance = object.__new__(cls)
        object.__setattr__(instance, "mode", mode)
        object.__setattr__(instance, "_parameter_items", freeze_parameter_items(parameters))
        return instance

    @classmethod
    def disabled(cls) -> InterruptorConfig:
        return cls._create(InterruptorMode.DISABLED, {})

    @classmethod
    def exact(cls, positions: Sequence[int], /) -> InterruptorConfig:
        return cls._create(InterruptorMode.EXACT, {"positions": _positions(positions, "positions")})

    @classmethod
    def search(
        cls,
        candidate_positions: Sequence[int],
        /,
        *,
        minimum_count: int = 0,
        maximum_count: int | None = None,
        strategy: InterruptorSearchStrategy = InterruptorSearchStrategy.AUTO,
        maximum_combinations: int = 5000,
    ) -> InterruptorConfig:
        positions = _positions(candidate_positions, "candidate_positions")
        low = _strict_int(minimum_count, "minimum_count", minimum=0)
        high = len(positions) if maximum_count is None else _strict_int(
            maximum_count, "maximum_count", minimum=0
        )
        if low > high:
            raise ValueError("minimum_count must not exceed maximum_count")
        if high > len(positions):
            raise ValueError("maximum_count must not exceed candidate position count")
        if not isinstance(strategy, InterruptorSearchStrategy):
            raise TypeError("strategy must be InterruptorSearchStrategy")
        return cls._create(InterruptorMode.SEARCH, {
            "candidate_positions": positions,
            "minimum_count": low,
            "maximum_count": high,
            "strategy": strategy,
            "maximum_combinations": _strict_int(
                maximum_combinations, "maximum_combinations", minimum=1
            ),
        })

    @classmethod
    def from_dict(cls, values: JsonObject, /) -> InterruptorConfig:
        if not isinstance(values, Mapping):
            raise TypeError("values must be a mapping")
        unknown = sorted(set(values) - {"mode", "parameters"})
        if unknown:
            raise UnsupportedConfigurationError(
                f"unsupported interruptor fields: {', '.join(unknown)}",
                field_paths=tuple(unknown),
            )
        mode = values.get("mode")
        parameters = values.get("parameters", {})
        if not isinstance(mode, str):
            raise TypeError("mode must be a serialized InterruptorMode value")
        if not isinstance(parameters, Mapping):
            raise TypeError("parameters must be a mapping")
        try:
            parsed_mode = InterruptorMode(mode)
        except ValueError as exc:
            raise UnsupportedConfigurationError(
                f"unsupported interruptor mode {mode!r}", field_paths=("mode",)
            ) from exc
        payload = dict(parameters)
        try:
            if parsed_mode is InterruptorMode.DISABLED:
                if payload:
                    raise TypeError("disabled mode accepts no parameters")
                return cls.disabled()
            if parsed_mode is InterruptorMode.EXACT:
                positions = payload.pop("positions")
                if payload:
                    raise TypeError(f"unsupported exact parameters: {sorted(payload)}")
                return cls.exact(positions)
            if "strategy" in payload:
                payload["strategy"] = InterruptorSearchStrategy(payload["strategy"])
            positions = payload.pop("candidate_positions")
            return cls.search(positions, **payload)
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, UnsupportedConfigurationError):
                raise
            raise UnsupportedConfigurationError(
                f"invalid interruptor parameters: {exc}", field_paths=("parameters",)
            ) from exc

    @property
    def parameters(self) -> Mapping[str, JsonValue]:
        return readonly_parameters(self._parameter_items)  # type: ignore[return-value]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "mode": self.mode.value,
            "parameters": thaw_parameter_items(self._parameter_items, json_compatible=True),
        }  # type: ignore[return-value]

    @property
    def replay_key(self) -> str:
        return replay_key(self._REPLAY_PREFIX, self.to_dict())

    def __copy__(self) -> InterruptorConfig:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> InterruptorConfig:
        return self

    def __repr__(self) -> str:
        return (
            f"InterruptorConfig(mode={self.mode!r}, "
            f"parameters={dict(self.parameters)!r})"
        )

    # Existing internal projections are removed after the AN3.6 caller cutover.
    @property
    def exact_positions(self) -> tuple[int, ...] | None:
        value = self.parameters.get("positions")
        return None if value is None else tuple(value)  # type: ignore[arg-type]

    @property
    def pool(self) -> tuple[int, ...] | None:
        value = self.parameters.get("candidate_positions")
        return None if value is None else tuple(value)  # type: ignore[arg-type]

    @property
    def min_count(self) -> int:
        return int(self.parameters.get("minimum_count", 0))

    @property
    def max_count(self) -> int | None:
        value = self.parameters.get("maximum_count")
        return None if value is None else int(value)

    @property
    def search_strategy(self) -> str:
        return str(self.parameters.get("strategy", InterruptorSearchStrategy.AUTO.value))

    @property
    def bruteforce_max(self) -> int:
        return int(self.parameters.get("maximum_combinations", 5000))

    def asdict(self) -> dict[str, Any]:
        return self.to_dict()


__all__ = ["InterruptorConfig"]
