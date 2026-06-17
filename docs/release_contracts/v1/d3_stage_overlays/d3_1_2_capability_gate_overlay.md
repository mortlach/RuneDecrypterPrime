# D3.1 / D3.2 capability-gate overlay

Scope: contract inventory and capability-gate semantics only.

Changed files:

- `src/rune_decrypter_prime/core/capability_gates.py`
- `tests/core/test_capability_gates.py`
- `tests/contracts/test_component_contracts.py`

Behaviour locked by this overlay:

- `FallbackPolicy.REPORT_ONLY` failure maps to `EffectiveState.REPORT_ONLY`.
- `FallbackPolicy.REPORT_ONLY` failure does not block `raise_if_blocked()`.
- `FallbackPolicy.EXPLICIT_REPORTED_FALLBACK` failure maps to `EffectiveState.FALLBACK_REPORTED` and does not block.
- `FallbackPolicy.BLOCK` failure maps to `EffectiveState.BLOCKED` and raises `RequestedLaneUnavailableError`.
- `FallbackPolicy.DISABLED` remains explicit:
  - not requested means inactive and non-blocking;
  - requested means blocked, so a requested lane cannot disappear silently.
- scorer lane names, request states, effective states, rank effects, and fallback policies have stable JSON string values.
- raw enum strings remain rejected by core contract dataclasses.

Out of scope for this overlay:

- NumPy `RuneScorer` wiring.
- solver report propagation.
- report-only no-rank proof.
- stale-pattern sweep.
- Torch parity.
- ScheduledStreamLookup changes.

Next overlay:

D3.3 should add the scorer-lane report builder using these fixed capability semantics.
