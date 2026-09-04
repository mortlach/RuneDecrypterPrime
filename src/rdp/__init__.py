"""RuneDecrypterPrime V1 package."""

from __future__ import annotations

from importlib import import_module

__version__ = "1.0.0"

__all__ = ["api"]


def __getattr__(name: str):
    if name == "api":
        module = import_module("rdp.api")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
