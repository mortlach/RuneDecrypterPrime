# `io/logging_adapter.py`

> Purpose: thin compatibility shim that returns a module-level logger, preferring the project's `RunLogger` when available. Keeps legacy modules (ported from stdlib logging) working without pulling in heavy logging configuration.

## `module_logger(name)`
- Tries `rune_decrypter_prime.io.run_logger.get_logger(name)` first.
- Falls back to instantiating `RunLogger(name)` if a class is exposed.
- If the run logger is unavailable (e.g., during early imports), returns `logging.getLogger(name)` without mutating global configuration.

Used by legacy modules that still expect a `logging.Logger`-like object but should play nicely with the new run logging pipeline.

