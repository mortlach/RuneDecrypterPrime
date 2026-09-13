# rdp/io/logging_adapter.py
from __future__ import annotations

def module_logger(name: str):
    """Return a standard module logger without configuring global handlers."""
    import logging
    return logging.getLogger(name)
