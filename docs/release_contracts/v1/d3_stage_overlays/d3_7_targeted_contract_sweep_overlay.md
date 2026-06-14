# D3.7 targeted contract sweep overlay

Scope: guard the D3 scorer-lane contract paths against known stale patterns.

Changed file:

- `tests/meta/test_d3_contract_sweep.py`

Locked behaviour:

- removed `src/rune_decrypter_prime/core/config.py` shim stays absent.
- D3 contract/report paths do not use hidden config helper names.
- D3 contract/report paths do not introduce report-only score/bonus tokens.

This is a targeted guardrail, not a whole-repository cleanup campaign.
