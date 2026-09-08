"""Execution settings needed to build a scorer without a cipher."""

from __future__ import annotations

from dataclasses import dataclass

from rdp.core.config.cipher import CipherConfig
from rdp.core.types import Device, Direction


@dataclass(frozen=True, slots=True)
class ScorerContext:
    encoding_dir: Direction
    device: Device

    def __post_init__(self) -> None:
        if not isinstance(self.encoding_dir, Direction):
            raise TypeError("encoding_dir must be Direction")
        if not isinstance(self.device, Device):
            raise TypeError("device must be Device")


def require_scorer_context(
    config: CipherConfig | ScorerContext,
) -> CipherConfig | ScorerContext:
    """Keep cipher-backed callers while admitting standalone scoring."""
    if not isinstance(config, (CipherConfig, ScorerContext)):
        raise TypeError(
            "cfg_cipher must be CipherConfig or ScorerContext, "
            f"got {type(config).__name__}"
        )
    return config


__all__ = ["ScorerContext", "require_scorer_context"]
