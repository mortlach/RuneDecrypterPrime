# D4 contract closure

D4 is the V1 hardening pass that turns the D3 lessons into explicit, testable contracts. It is not a feature-expansion pass. The goal is that requested capabilities run, block, or report an explicit fallback; they must not disappear behind compatibility helpers, broad exception handlers, façade scorers, optional runtimes, or tutorial-only assumptions.

## D4.0 full-proof gate

The V1 release proof is the GitHub workflow `.github/workflows/rdp_v1_full_proof.yml`. It must remain a manual release gate and must run:

- `python install.py`
- the full pytest suite under `tests`
- `tutorials/v1/run_pretty_print_release.py`
- Windows and Ubuntu on Python 3.11

Pytest must use `-ra` so skipped optional-runtime tests are visible in the log rather than silently hidden.

## D4.1 scorer capability attachment

All public scorer implementations must expose a `ScorerCapabilityReport`. This includes NumPy, Torch, and Unified scorer paths. Façade scorers must not hide backend lane state. When a scorer builder creates a façade around a backend, the public scorer and backend must both expose the same report.

A requested production lane must be either `active` or `blocked`. Report-only lanes must be visible and must not affect ranking.

## D4.2 solver report visibility

Solver reports must preserve `scorer_lanes` in report details. If capability-report construction or JSON serialisation fails, the report must contain a JSON-safe error payload rather than silently omitting the lane section.

## D4.3 stop reason schema

Stop reasons must classify into stable V1 categories:

- `success`
- `budget`
- `blocked_before_run`
- `error`
- `manual`
- `not_started`

Known emitted aliases such as `target_score`, `stop_score`, and `test_key` are success reasons. Dynamic budget families such as `no_improve_*` and `stall_*` are budget reasons.

## D4.4 typed public config boundary

Public builders must require typed config objects at the V1 boundary. Loose `dict` or `SimpleNamespace` objects may still exist in focused compatibility layers and tests, but they must not bypass the public `build_cipher()` / `build_scorer()` typed boundary.

## D4.5 scheduled-stream lookup contract

`scheduled_stream_lookup` is V1 core. Its V1 contract is explicit and narrow:

- one or two streams only
- two-stream schedules must reject one-stream configs
- `xor_mod` and `lookup` require `degeneracy='allow'`
- fixed stream values are literal symbols and must not be modulo-reduced
- fixed stream text values such as `"12"` must be rejected, not split into characters
- backward/end anchoring is a real stream-state mode and must be test-covered

## D4.6 silent-exception policy

Broad `except Exception` blocks are allowed only when one of these is true:

- the code is best-effort UI/logging/telemetry and failure does not affect solving semantics
- the failure is converted into a typed contract error or a JSON-safe diagnostic payload
- the failure is re-raised after attaching a capability report or explicit error payload
- a test proves the fallback is deliberate and non-ranking

They are not allowed to make requested production scorer lanes, requested Torch execution, stop reasons, or scheduled-stream configuration silently disappear.

## D4.7 docs/contracts alignment

The release docs must describe only contracts actually backed by source and tests. No aspirational V1 claims are allowed in the release contract docs.

## D4.8 final proof expectation

Final D4 acceptance requires:

- clean branch diff review
- full-proof workflow pass
- V1 tutorials pass
- no new V1 feature scope opened
- every D4 contract listed above covered by at least one source gate and one test/doc gate
