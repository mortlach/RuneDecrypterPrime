# rune_decrypter_prime/telemetry/schema.py
from __future__ import annotations
from rune_decrypter_prime.core.types import (
    Device,
    ScorerImpl,
    ensure_device,
    ensure_scorer_impl,
)


def to_canonical_device_str(dev: Device | str) -> str:
    """Canonical device string for telemetry."""
    d = ensure_device(dev)
    return d.value  # "cpu" | "cuda"


def to_canonical_impl_str(impl: ScorerImpl | str) -> str:
    """Canonical scorer impl string for telemetry."""
    s = ensure_scorer_impl(impl)
    return s.value  # "numpy" | "torch" | "unified" | "auto"
