# D3.7 targeted V1 contract sweep overlay

Scope: guard the D3 V1 core/scoring/report contract paths against known stale patterns and silent drift.

Changed file:

- `tests/meta/test_d3_contract_sweep.py`

Locked behaviour:

- removed `src/rune_decrypter_prime/core/config.py` shim stays absent.
- D3 contract/report paths do not use hidden config helper names.
- D3 contract/report paths do not introduce report-only score/bonus tokens.

This was not random refactoring; it was a required no-drift sweep over the V1 core/scoring/report paths. Hits were either fixed, isolated, or documented as intentional compatibility boundaries.
