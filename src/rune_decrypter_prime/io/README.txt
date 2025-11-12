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

Extending I/O
-------------
1. **New log sinks:** wrap them in `run_logger.py` and respect the same schema
   keys (`telemetry.run`, solver spans, `solution.meta["work"]`). Never write
   outside the run directory that `LoggingConfig` returns.
2. **Randomness helpers:** keep RNG utilities in `io/rng.py` so solvers and
   ciphers share the same deterministic source-of-truth.
3. **Redaction:** honour `LoggingConfig.redact_identity` whenever you emit user
   identifiers or hostnames. Add tests in `tests/telemetry` if you extend that feature.
