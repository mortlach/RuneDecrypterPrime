# rdp/io/logging_adapter.py
from __future__ import annotations

def module_logger(name: str):
    """
    Unified entrypoint for module-level loggers.
    - Prefer project's run_logger (if available).
    - Otherwise, fall back to the stdlib logger with no basicConfig.
    """
    # Try existing run_logger first
    try:
        # Common shapes this covers:
        #  1) run_logger.get_logger(__name__) -> stdlib Logger-like
        #  2) run_logger.RunLogger(__name__)  -> object with .debug/.info/...
        import rdp.io.run_logger as run_logger  # type: ignore
        # Shape A: get_logger API
        if hasattr(run_logger, "get_logger"):
            return run_logger.get_logger(name)  # type: ignore[attr-defined]
        # Shape B: class-based
        if hasattr(run_logger, "RunLogger"):
            return run_logger.RunLogger(name)   # type: ignore[attr-defined]
    except Exception:
        pass

    # Fallback: stdlib logger, no global config here (apps/tests configure handlers).
    import logging
    return logging.getLogger(name)
