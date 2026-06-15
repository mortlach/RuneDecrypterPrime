# D7 tutorial benchmark match-ratio addendum

For tutorials and benchmarks with known plaintext/reference data, `match_ratio` is mandatory.

A run declaring `TutorialTruthPolicy.KNOWN_PLAINTEXT_REFERENCE` or `TutorialTruthPolicy.KNOWN_KEY_AND_PLAINTEXT` must provide enough plaintext/reference data to compute:

- `match_ratio`
- `readable_reached`
- `target_reached`

This is intentional. Match ratio is part of the tutorial/benchmark oracle instrumentation and should always be available when truth data is known.

A run declaring `TutorialTruthPolicy.NONE` must not report a match ratio.

This keeps tutorial benchmarking useful for readability/compute-efficiency tuning without confusing tutorial truth with ciphertext-only solving.
