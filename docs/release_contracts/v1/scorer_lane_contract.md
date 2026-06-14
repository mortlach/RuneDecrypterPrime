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

Public scorer / backend visibility:

- Every public scorer implementation exposed by `build_scorer()` must provide `capability_report()`.
- Public scorer constructors that are part of the V1 runtime surface must require typed `CipherConfig` and `ScoringConfig` objects.
- Façade scorers, including `UnifiedRuneScorer`, must expose the backend-derived report.
- When a builder attaches a capability report to a façade, the backend must expose the same report object.
- Backend-specific `CapabilityIssue` entries must survive into the public report; they must not be flattened into a generic unavailable state.

Failure reporting:

- Requested production lanes block through `RequestedLaneUnavailableError` when unavailable.
- Solver reports must preserve `details["scorer_lanes"]` when available.
- Capability-report or JSON serialisation failure must produce a JSON-safe diagnostic payload rather than silently omitting the scorer-lane section.

JSON output must come from `ScorerCapabilityReport.to_json_dict()`.
