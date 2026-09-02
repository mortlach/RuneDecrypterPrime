"""Canonical RuneDecrypterPrime V1 public API."""

from __future__ import annotations

from rdp.api import advanced, display, experimental, liber_primus
from rdp.api.errors import (
    AssetUnavailableError,
    CapabilityUnavailableError,
    ConfigurationError,
    ExecutionError,
    NonInvertibleCipherError,
    RdpError,
)
from rdp.api.known_key import decrypt, encrypt
from rdp.api.run import run
from rdp.api.run_result import RunResult
from rdp.api.run_spec import (
    ProblemInput,
    RawTextInput,
    RuneIndexInput,
    RunSpec,
    SourceReferenceInput,
)
from rdp.api.specs import CipherSpec, KeySpec, SolverSpec
from rdp.api.stop_reason_contract import RunStatus
from rdp.core.config.interruptor import InterruptorConfig
from rdp.core.config.logging_config import LoggingConfig
from rdp.core.config.scoring import ScoringConfig
from rdp.core.types import (
    ComputeDevice,
    ConcreteKey,
    InitialKeys,
    RuneIndices,
    TextDirection,
    WordLengthPolicy,
)

__all__ = [
    "run",
    "encrypt",
    "decrypt",
    "RunSpec",
    "RunResult",
    "CipherSpec",
    "KeySpec",
    "SolverSpec",
    "ScoringConfig",
    "LoggingConfig",
    "InterruptorConfig",
    "RawTextInput",
    "RuneIndexInput",
    "SourceReferenceInput",
    "ProblemInput",
    "ConcreteKey",
    "RuneIndices",
    "InitialKeys",
    "TextDirection",
    "ComputeDevice",
    "WordLengthPolicy",
    "RunStatus",
    "RdpError",
    "ConfigurationError",
    "CapabilityUnavailableError",
    "AssetUnavailableError",
    "NonInvertibleCipherError",
    "ExecutionError",
    "advanced",
    "display",
    "liber_primus",
    "experimental",
]
