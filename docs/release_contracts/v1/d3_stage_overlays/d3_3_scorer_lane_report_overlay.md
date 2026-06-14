# D3.3 scorer-lane report builder overlay

Scope: scoring-layer report construction only.

Changed files:

- `src/rune_decrypter_prime/scoring/scorer_lane_report.py`
- `tests/scoring/test_scorer_lane_report.py`

Behaviour locked by this overlay:

- `ScoringConfig` is the only accepted config input.
- `build_scorer_lane_report(...)` returns a `ScorerCapabilityReport`, not an ad hoc dict.
- lane order follows `ScorerLaneName`.
- `lm_char_wli` is always required, active, production, and block-policy.
- non-requested optional lanes are inactive and non-blocking.
- requested production lanes are active when their observed runtime object is present.
- requested production lanes are blocked when their runtime object is missing or an issue is supplied.
- requested word-ngram report-only lane stays `EffectiveState.REPORT_ONLY` whether the diagnostic runtime is available or unavailable.
- report-only lanes remain non-blocking.
- JSON serialisation uses `ScorerCapabilityReport.to_json_dict()`.

Out of scope for this overlay:

- wiring this report into `RuneScorer`.
- converting existing NumPy warning-skip paths to requested-lane blocking.
- solver report propagation.
- report-only no-rank proof.
- stale-pattern sweep.
- Torch parity.
- ScheduledStreamLookup changes.

Next overlay:

D3.4 should wire this builder into the NumPy `RuneScorer`, capture capability issues from backend construction, expose `scorer.capability_report()`, and raise `RequestedLaneUnavailableError` for blocked requested production lanes.
