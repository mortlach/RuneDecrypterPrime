# D3 NumPy strict requested lanes

D3 hardens NumPy scorer optional production lanes.

Requested production lanes:

- `hamming`
- `span_hamming_raw`
- `span_hamming_calibrated`

A requested production lane must be active or blocked. It must not warn and silently disappear.

The public module path remains:

- `rune_decrypter_prime.scoring.rune_scorer.RuneScorer`

The large NumPy implementation is kept in:

- `rune_decrypter_prime.scoring.rune_scorer_impl`

The public wrapper enforces the strict V1 requested-lane contract and exposes `capability_report()`.

Report-only lanes remain report-only and must not affect score or rank.
