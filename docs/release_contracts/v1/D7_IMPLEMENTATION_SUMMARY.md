# D7 implementation summary

D7 closes the V1 release-contract gap by turning the D0-D6 hardening work into explicit, repo-local evidence and tests.

## Design split

D7 deliberately keeps the API layer forgiving and the core layer strict.

API-facing code may accept aliases, friendly names, strings, and compatibility surfaces where those are documented and normalised. Core RDP code must use typed configs, stable enum domains, explicit capability states, explicit stop/oracle/truth reports, and deterministic failures for unsupported requested behaviour.

## Core contract hardening completed

- Enum-domain ownership is ledgered and tested.
- Raw string labels are rejected at core component-contract boundaries.
- Scoring and cipher config strings are normalised into core enums.
- `CipherConfig.keyops_family` is normalised to `KeyOpsFamily`.
- `UnifiedRuneScorer` construction is covered as a strict typed-config boundary.
- Explicit backend requests do not silently fall back to NumPy.
- Requested scorer lanes block when unavailable instead of warning and disappearing.
- Report-only lanes remain report-only and do not acquire production rank effect.
- Scorer lane report sections are stable public labels and JSON-safe.

## Solver/report hardening completed

- Unknown stop reasons classify as errors instead of silent budget stops.
- Oracle/truth usage is separated from execution-route and parameter-key domains.
- Caller-supplied solver-report details cannot overwrite generated oracle/truth contract fields.

## ScheduledStreamLookup V1 lock completed

- The canonical engine remains `scheduled_stream_lookup`.
- Friendly aliases remain API wrappers only, not core cipher registry names.
- Fixed streams are literal integer symbols, not text and not modulo-wrapped.
- Strict config validation covers stream kind, direction, anchor, advance, schedule, operation, and lossy integer coercion.
- Schedule-mode tests cover overlay, alternating, staggered overlay, ragged overlap, mask, direction, and anchor combinations.
- Degenerate operations require explicit `degeneracy='allow'` and expose candidate lists instead of pretending there is a unique plaintext.

## Asset and artifact hardening completed

- Public artifact agreement keeps export candidates small, reviewable, and repo-relative.
- LM root/index tests cover structured path/index handling.
- ECDF status tests cover relative asset ids, metadata, meta hash, interpolation dtype, missing assets, and malformed ECDF rejection.
- D7 does not add a fake asset-registry layer; the V1 asset status contract is the existing LM path helpers plus `ECDFCache` validation/status methods.

## Tutorial/report output rationalisation started

- `utils.tutorial_report` provides a compact `rdp_tutorial_run_report.v1` payload and deterministic console renderer.
- `utils.tutorial_benchmark` provides typed tutorial benchmark policies and `rdp_tutorial_benchmark_summary.v1` summaries for readability/target/work/time reporting.
- `utils.tutorial_reference` provides an attachable reference helper so tutorial/session code can add reference data early or later without making the run surface brittle.
- Tutorial truth thresholds are explicitly labelled by `TutorialTruthPolicy`; they are allowed for tutorials and benchmarks but are not ciphertext-only solver claims.
- ScheduledStreamLookup real tutorials now request `return_solver_report=True` and print the unified tutorial report.
- Seeded pipeline smoke remains minimal and requests a solver report only when a report is explicitly printed.
- This is a first unified output layer; broader tutorial clean-up should continue after D7 validation rather than expanding V1 scope late.

## Release-contract evidence completed

- D7 cleanup/deprecation policy and machine-readable ledger are present.
- D7 acceptance-test promotion status records every original acceptance-row outcome.
- D7 closure checklist records the exact local/CI gates required before final closure.
- Contract tests ensure implemented D7 acceptance paths exist and non-V1 rows stay explicitly experimental.

## Still deliberately not done in D7

- Full save/restore solving remains roadmap/experimental.
- New no-WLI n-gram Hamming remains experimental/report-only with no V1 production rank effect.
- Legacy internal optional-backend warning setup remains behind the V1 wrapper and is tracked as future cleanup in the cleanup ledger; requested V1 production lanes are blocked by tests.

## Required final validation

D7 is not closed until the latest commit is validated with:

```bash
python -m pytest -q -ra -p no:cacheprovider tests
```

and the tutorial/release gate used by the project CI is green after the final commit.
