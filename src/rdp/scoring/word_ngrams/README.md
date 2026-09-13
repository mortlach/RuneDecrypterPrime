# Word-token sequence models

Build and inspect sequence evidence over rune-word tokens. These modules provide model storage, scoring and diagnostic reports; their presence does not introduce another ordinary V1 run path.

## Where to look

- [in_memory.py](in_memory.py) — Build an in-memory word-token model.
- [sqlite_model.py](sqlite_model.py) — Store and query counts in SQLite.
- [runtime.py](runtime.py) — Extract exact word tokens and construct judge reports.
- [scorer.py](scorer.py) — Token-sequence counts, scores and trust diagnostics.

## Choices and extension

The in-memory and SQLite models suit different data sizes. Word tokenisation depends on the supplied boundaries. Check report trust and coverage before interpreting a sequence score, and keep diagnostic use separate from production ranking.

Continue with the [guide](../../../../docs/guides/scoring.md) or the [package map](../../README.md).
