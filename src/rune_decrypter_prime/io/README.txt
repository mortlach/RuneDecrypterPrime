rune_decrypter_prime/io
=======================

Logging, telemetry emission, and file I/O glue.

Highlights
----------
- `logging_adapter.py`: module-level logger consistent with the project’s
  formatting.
- `run_logger.py`: emits structured telemetry JSONL to the active run directory.
- `rng.py`, `telemetry_sink.py` (if present): small helpers used by core/solvers.

Design notes
------------
- Everything here should be side-effect free until `LoggingConfig.init_logging`
  prepares the output directories.
- Keep dependencies minimal; higher layers pass in objects to log so we can
  reuse the same adapters in CLI tools and tests.
