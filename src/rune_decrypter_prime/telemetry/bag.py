# rune_decrypter_prime/telemetry/bag.py
from __future__ import annotations
from typing import Any

class TelemetryBag(dict):
    """A dict that also supports attribute access for ergonomic writes/reads."""
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("__") or name in self.__class__.__dict__:
            return super().__setattr__(name, value)
        self[name] = value

    def __delattr__(self, name: str) -> None:
        try:
            del self[name]
        except KeyError as e:
            raise AttributeError(name) from e
