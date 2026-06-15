# D7 final summary

D7 is a V1 closure and hardening branch. It is not a feature branch.

Branch under closure:

```text
prelease/v1.0.0_d7
```

D7 starts from the D6 release-contract baseline and keeps GitHub as source of truth. Review packs are evidence generated from branch heads; they are not the implementation authority.

## Scope

D7 deliberately does not add:

```text
new solvers
new ciphers
new scorer lanes
new assets
new scoring behaviour
new ranking behaviour
broad compatibility shims
monkey patches
```

The branch only hardens stable contract labels, branch workflow coverage, acceptance gates, and release evidence rules.

## Implemented hardening

### Component and capability contract labels

D7 converts the stable component/capability contract label domains from plain `Enum` to Python 3.11 `StrEnum`.

Owned labels:

```text
ComponentKind
V1Status
RankEffect
RequestState
EffectiveState
CapabilityStatus
FallbackPolicy
ScorerLaneName
```

The public JSON strings are unchanged because reports still emit `.value`. Raw strings are still rejected when constructing typed contract objects such as `LaneStatus`.

### Core scoring config labels

D7 enum-owns the finite scoring config modes and policies that had still been represented as raw strings inside `ScoringConfig`.

Owned labels:

```text
HammingDirectionMode
SpanHammingMode
SpanHammingBucketPolicy
SpanHammingCombineMode
SpanHammingGateFailPolicy
SpanHammingLmProfileSource
```

Public/config boundary strings are still accepted, but they are normalised immediately in `ScoringConfig.__post_init__`. Internal config state stores enum values. `ScoringConfig.asdict()` preserves the same public strings as before.

D7 also exports domain-local normalisers:

```text
ensure_hamming_direction_mode
ensure_span_hamming_mode
ensure_span_hamming_bucket_policy
ensure_span_hamming_combine_mode
ensure_span_hamming_gate_fail_policy
ensure_span_hamming_lm_profile_source
```

These are used by runtime/capability bridge code so each path does not invent its own string validation.

This is a contract-hardening change, not a scoring change.

### Requested scorer lane detection

`ScoringConfig.requested_scorer_lanes()` now reads enum-backed span-hamming mode state instead of re-normalising with ad hoc string comparisons.

This keeps the capability-report path aligned with the same labels used by config validation.

### Runtime capability report bridges

D7 hardens the scorer-construction capability bridge in `core/engine/builders.py`, plus the NumPy wrapper and unified scorer capability-report fallback paths.

These bridges may need to inspect private runtime scorer state when a scorer backend does not provide a native `capability_report()`. They now normalise `_span_hamming_mode` through `SpanHammingMode` before deciding whether a raw span backend is active. This prevents enum-backed runtime mode state from silently dropping a requested `span_hamming_raw` lane in fallback capability-report paths.

This is intentionally narrow. It does not change scoring, ranking, scorer construction, or the public report schema.

### Scorer telemetry source labels

D7 enum-owns the scorer telemetry source prefixes and keys that derive stable public scorer-report detail sections.

Owned labels:

```text
ScorerTelemetryPrefix
ScorerTelemetryKey
```

These cover:

```text
span_hamming_
word_ngram_judge_
span_lm_
hamming_dictionary_policy
span_hamming_dictionary_policy
span_hamming_assets_dictionary_policy
span_hamming_dictionary_policy_match
span_hamming_dictionary_policy_note
```

The public report detail sections remain unchanged:

```text
hamming_dictionary
span_hamming
span_lm
word_ngrams
```

Report-only telemetry continues to be visible without affecting `score`, `raw_score`, ordering, tie-breaks, candidate selection, or solver stopping.

### Solver report semantic label split

D7 confirmed the D6 solver-report split is already present on the branch:

```text
ExecutionRoute.KNOWN_KEY_FASTPATH = "known_key_fastpath"
SolverParamKey.TEST_KEY = "test_key"
OracleUse.TEST_KEY = "test_key"
```

`OracleUse` is no longer reused as the execution-route owner or the normalised-parameter-key owner in `solver_report.py`.

### Workflow coverage

The full-proof workflow remains manually runnable and now includes D7 push coverage:

```text
workflow_dispatch
prelease/v1.0.0_d7
```

The workflow still runs the installer smoke, full pytest, and V1 release tutorial runner on Windows and Ubuntu with Python 3.11.

### Acceptance gates

D7 adds `docs/release_contracts/v1/V1_RELEASE_ACCEPTANCE_GATES.md`.

That document records the final V1 closure gates for:

```text
scope
stable label ownership
public output preservation
report-only no-rank-effect
run/block/report visibility
focused tests
full pytest
V1 tutorials
full-proof CI
review-pack regeneration
```

## Tests added or extended

D7 adds or extends focused tests for the new hardening surface:

```text
tests/contracts/test_component_contracts.py
tests/core/test_scoring_config_label_contract.py
tests/core/test_scorer_capability_builder_contract.py
tests/scoring/test_scorer_report_label_contract.py
tests/contracts/test_v1_contract_label_guardrails.py
tests/contracts/test_v1_full_proof_workflow_contract.py
tests/contracts/test_v1_release_acceptance_gates_doc.py
```

These tests assert that:

```text
component/capability labels are StrEnum-owned
D7-owned scoring config labels are enum-owned
exported scoring-mode normalisers preserve enum domains
invalid D7-owned config strings are rejected
public asdict strings are unchanged
requested scorer lanes use enum-backed span mode
fallback capability reports preserve enum-backed runtime span mode
scorer telemetry source labels are enum-owned
public scorer-report sections remain unchanged
report-only details do not mutate score/raw_score/metrics
full-proof workflow covers prelease/v1.0.0_d7
acceptance-gate docs record the closure rules
```

## Known local overlay not yet pushed

A runtime enum-state overlay exists for the large NumPy and Torch scorer backend files. It is intentionally handled as a separate local overlay because the GitHub connector has blocked writes to the large scorer backend paths.

The branch now hardens the config surface and all fallback capability-report bridges, but the large backend files still contain private runtime fields that are normalised to raw strings internally. The correct final hardening direction is to update those backend private fields to enum members and update tests that directly mutate those private fields to use enum members too.

Required local test-only substitutions are:

```text
"raw_bonus" -> SpanHammingMode.RAW_BONUS
"min" -> SpanHammingCombineMode.MIN
"weighted_sum" -> SpanHammingCombineMode.WEIGHTED_SUM
"score_floor" -> SpanHammingGateFailPolicy.SCORE_FLOOR
"char_only" -> SpanHammingGateFailPolicy.CHAR_ONLY
```

This is not a D7 scope reduction. It is a tooling limitation around large backend-path updates. The branch should not close until that overlay is either applied locally and pushed, or the equivalent backend/test update is made through a normal Git checkout.

## Closure status

D7 has completed these closure hardening blocks:

```text
component/capability contract StrEnum ownership
core scoring config label ownership
exported scoring-mode normalisers
requested scorer lane enum-backed detection
fallback capability-report runtime span-mode normalisation
scorer telemetry label ownership
solver-report semantic split verification
workflow D7 branch coverage
V1 acceptance-gate document
focused guardrail tests
```

D7 is not final until:

```text
large backend runtime enum-state overlay is applied or explicitly superseded by equivalent code
focused D7 tests pass
full pytest passes
V1 tutorial gate passes
full-proof CI is green or equivalent local proof is documented
final review pack is regenerated from final D7 head
```
