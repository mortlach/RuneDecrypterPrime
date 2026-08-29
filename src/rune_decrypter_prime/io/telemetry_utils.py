# ============================================================
# rune_decrypter_prime/io/telemetry_utils.py
# Back-compat shim for legacy imports (v0/v1 release branch).
# ============================================================
from __future__ import annotations

from warnings import warn

from rune_decrypter_prime.telemetry.pipeline import (
    make_pipeline_block as _make_pipeline_block,
)

__all__ = ["make_pipeline_block"]


def make_pipeline_block(*args, **kwargs):
    """
    Deprecated shim: forward to rune_decrypter_prime.telemetry.pipeline.make_pipeline_block.
    Tests and external callers should import from the telemetry module directly.
    """
    warn(
        "Importing make_pipeline_block from rune_decrypter_prime.io.telemetry_utils is deprecated; "
        "use rune_decrypter_prime.telemetry.pipeline.make_pipeline_block instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _make_pipeline_block(*args, **kwargs)
