# D3.4 NumPy builder wiring overlay

Scope: first NumPy runtime-path wiring slice.

Changed files:

- `src/rune_decrypter_prime/core/engine/builders.py`
- `tests/core/test_scoring_requested_lane_detection.py`

Behaviour locked by this overlay:

- `build_scorer(...)` still requires canonical `CipherConfig` and `ScoringConfig`.
- NumPy scorers constructed through `build_scorer(...)` receive a `ScorerCapabilityReport` built by `build_scorer_lane_report(...)`.
- The report is attached to the scorer as `_capability_report`.
- If the scorer has no public `capability_report()` method, `build_scorer(...)` attaches one.
- Requested production lanes that are missing after NumPy scorer construction now raise `RequestedLaneUnavailableError` through `raise_if_requested_lane_blocked(...)`.
- Requested report-only lanes remain visible and non-blocking.
- Focused tests use a fake NumPy scorer, so this stage tests contract wiring without depending on scorer assets.

Known limitation / next work:

- Direct `RuneScorer(c_cfg, s_cfg)` construction still needs native wiring inside `rune_scorer.py`.
- Existing NumPy constructor warning-skip paths still need to capture explicit `CapabilityIssue` objects instead of relying only on missing observed runtime objects.
- Calibrated span constructor failures still need consistent requested-lane wrapping if raised before the builder report is attached.

Out of scope for this overlay:

- scoring arithmetic changes.
- report-only no-rank proof.
- solver report propagation.
- stale-pattern sweep.
- Torch parity.
- ScheduledStreamLookup changes.
