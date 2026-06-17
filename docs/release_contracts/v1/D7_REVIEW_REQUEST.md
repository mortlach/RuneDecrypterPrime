# D7 review request

Branch under review: `prelease/v1.0.0_d7`

Review target: current head of `prelease/v1.0.0_d7`.

Validation status: rerun focused and full validation after any commit made in response to this review request.

GitHub status-check status: no combined status checks were attached when this note was last checked through the connector.

## Review purpose

D7 is intended to close V1 contract ambiguity, not to expand V1 feature scope.

The main review question is:

> Does D7 now make V1 strict, explicit, testable, and reviewable without silently promoting experimental work or breaking documented API/tutorial compatibility?

## Design rule to review against

D7 follows this boundary:

- API/tutorial/session surfaces may be forgiving when inputs are normalised and reported canonically.
- Core/runtime code must be strict, typed, explicit, and deterministic.
- Report-only/experimental signals must not affect V1 production ranking.
- Requested production capabilities must block when unavailable rather than silently warning or disappearing.

## Major D7 areas completed

### Core contract hardening

- Enum-domain ownership and usage clarified.
- Oracle/truth usage separated from execution-route and parameter-key domains.
- Unknown solver stop reasons classify as errors rather than silent budget stops.
- Caller-supplied solver-report details cannot overwrite generated oracle/truth contract fields.
- Raw core labels and typed config boundaries are covered by contract tests.

### Scorer lane and report hardening

- Requested production scorer lanes block when unavailable.
- Report-only lanes remain report-only and cannot become ranking inputs accidentally.
- Scorer lane report sections are stable and JSON-safe.
- Tutorial reports preserve structured scorer-lane payloads instead of silently dropping non-list payloads.
- Legacy optional-backend warning behaviour remains behind the V1 wrapper and is tracked for future cleanup.

### ScheduledStreamLookup V1 lock

- Canonical core engine remains `scheduled_stream_lookup`.
- Friendly aliases remain API wrappers only.
- Fixed streams are literal integer symbols, not text and not modulo-wrapped.
- Strict validation covers stream kind, direction, anchor, advance, schedule, operation, and lossy integer coercion.
- Schedule-mode tests cover overlay, alternating, staggered overlay, ragged overlap, mask, direction, and anchor combinations.
- Degenerate operations require explicit degeneracy allowance and expose candidate lists rather than pretending a unique plaintext exists.

### Asset and artifact contracts

- LM root/index tests cover structured asset path/index handling.
- ECDF tests cover relative asset ids, metadata, meta hash, dtype, missing assets, and malformed ECDF rejection.
- No fake V1 asset-registry layer was added.

### Tutorial/session/report framework

D7 now starts a unified tutorial/session output framework:

- `utils.tutorial_report`
- `utils.tutorial_benchmark`
- `utils.tutorial_reference`
- `utils.tutorial_session_report`

This framework is intentionally outside strict runtime modules. It is forgiving at the tutorial/session boundary, normalises canonical strings to enums, and emits stable canonical report strings.

Important review point: this is the framework foundation only. D7 does not claim every long tutorial has been tuned or migrated.

## New review files and contracts

Review these files together:

- `docs/release_contracts/v1/D7_IMPLEMENTATION_SUMMARY.md`
- `docs/release_contracts/v1/D7_CLOSURE_CHECKLIST.md`
- `docs/release_contracts/v1/D7_TUTORIAL_BENCHMARK_POLICY.md`
- `docs/release_contracts/v1/D7_TUTORIAL_BENCHMARK_MATCH_RATIO_ADDENDUM.md`
- `docs/release_contracts/v1/D7_TUTORIAL_OUTPUT_FRAMEWORK.md`
- `docs/release_contracts/v1/d7_acceptance_test_promotion_status.csv`
- `docs/release_contracts/v1/v1_cleanup_deprecation_ledger.json`

Key tests added or strengthened include:

- `tests/contracts/test_d7_acceptance_promotion_status.py`
- `tests/contracts/test_d7_review_request_contract.py`
- `tests/contracts/test_tutorial_helpers_boundary.py`
- `tests/contracts/test_tutorial_output_framework_contract.py`
- `tests/contracts/test_tutorial_enum_normalization_contract.py`
- `tests/contracts/test_tutorial_report_shape_contract.py`
- `tests/utils/test_tutorial_benchmark.py`
- `tests/utils/test_tutorial_benchmark_enum_normalization.py`
- `tests/utils/test_tutorial_reference.py`
- `tests/utils/test_tutorial_session_report.py`
- `tests/utils/test_tutorial_session_report_enum_normalization.py`
- `tests/utils/test_tutorial_report_scorer_lanes_payload.py`

## Review-response fixes applied

The following review blockers were addressed after the initial review request:

1. Removed the one-off root patch script `apply_solver_stop_reason_domain.py`.
2. Updated `utils/tutorial_report.py` to preserve structured `scorer_lanes` mapping payloads and wrap legacy list payloads as `{"lanes": [...]}`.
3. Removed the stale hard-coded latest-reviewed commit from this review request; the review target is now the current branch head.

## Deliberately not done in D7

These are not D7 failures:

- Full save/restore solving remains roadmap/experimental.
- New no-WLI n-gram Hamming remains experimental/report-only.
- Full tutorial-pack tuning remains a follow-on tutorial rationalisation pass.
- Long-solve readable/target threshold tuning requires local tutorial-pack evidence.
- Legacy internal optional-backend warning setup remains tracked for future cleanup behind the V1 wrapper.

## Requested reviewer checks

Please review hard for:

1. Any silent fallback still reachable from a requested V1 production path.
2. Any report-only or experimental signal that can affect ranking.
3. Any tutorial/session helper imported into strict runtime modules.
4. Any raw string domain that should be normalised to an enum at the relevant boundary.
5. Any compatibility break at API/tutorial surfaces that should instead be deprecate-only.
6. Any D7 evidence file that overclaims compared with actual tests.
7. Any local-only or machine-specific path leaking into release-contract evidence.

## Recommended validation commands

Focused D7/tutorial framework validation:

```bash
python -m pytest -q \
  tests/utils/test_tutorial_benchmark.py \
  tests/utils/test_tutorial_benchmark_enum_normalization.py \
  tests/utils/test_tutorial_reference.py \
  tests/utils/test_tutorial_session_report.py \
  tests/utils/test_tutorial_session_report_enum_normalization.py \
  tests/utils/test_tutorial_report_scorer_lanes_payload.py \
  tests/contracts/test_tutorial_enum_normalization_contract.py \
  tests/contracts/test_tutorial_helpers_boundary.py \
  tests/contracts/test_tutorial_output_framework_contract.py \
  tests/contracts/test_tutorial_report_shape_contract.py \
  tests/contracts/test_d7_review_request_contract.py \
  tests/contracts/test_d7_acceptance_promotion_status.py
```

Full D7 gate:

```bash
python -m pytest -q -ra -p no:cacheprovider tests
```

D7 should not be treated as closed until the latest branch head has equivalent full validation evidence.
