"""
Back-compat shim: re-export the logging config helpers from their new home.

Tests and legacy modules still import ``rune_decrypter_prime.core.logging_config``
directly, so keep this module as a thin alias to the canonical implementation
under ``rune_decrypter_prime.core.config.logging_config``.
"""

from rune_decrypter_prime.core.config.logging_config import (  # noqa: F401
    LoggingConfig,
    current_paths,
    get_run_dir,
    init_logging,
)

__all__ = ["LoggingConfig", "init_logging", "get_run_dir", "current_paths"]
