# V1 scorer lane contract

The V1 scorer lane report is the stable contract for optional scorer capability.

Canonical surface:

- `ScorerCapabilityReport`
- `LaneStatus`
- `ScorerLaneName`
- `RankEffect`
- `RequestState`
- `EffectiveState`
- `FallbackPolicy`

Required lane:

- `lm_char_wli` is required, production, active, and block-policy.

Optional production lanes:

- `hamming`
- `span_hamming_raw`
- `span_hamming_calibrated`

If an optional production lane is requested, it must be active or blocked. It must not silently disappear.

Report-only diagnostic lanes:

- `word_ngram_judge_report_only`
- `ngram_hamming_experimental_report_only`

Report-only lanes must be visible in the report and must not affect ranking, raw score, ordering, or tie-breaks.

JSON output must come from `ScorerCapabilityReport.to_json_dict()`.
