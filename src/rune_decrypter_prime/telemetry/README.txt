rune_decrypter_prime/telemetry
==============================

Structured logging and run metadata helpers.

Key modules
-----------
- `events.py`: emits canonical `run_start`, `solver_progress`, `solver_end`,
  etc., into the active telemetry sink.
- `pipeline.py`: builds “pipeline blocks” and tracks start/end timestamps for
  Stage-1/Stage-2 transitions.
- `schema.py`: helper functions for normalising device/impl strings.
- `bag.py`: lightweight mutable telemetry store attached to every
  `DecryptionProblem`.

Guidelines
----------
- All telemetry writes should go through these helpers so the JSONL format
  remains stable.
- Avoid putting heavy business logic here; telemetry should be best-effort and
  never throw exceptions back into solver/scorer code.

Extending telemetry
-------------------
1. **New event types:** define them in `events.py`, document the payload, and
   add schema tests under `tests/telemetry/`.
2. **Pipeline data:** if a new stage needs metadata, extend `pipeline.make_pipeline_block`
   so RunAPI/Engine automatically include it.
3. **Redaction/privacy:** respect `LoggingConfig.redact_identity` and future
   privacy toggles whenever you emit hostnames, usernames, or file-system paths.
