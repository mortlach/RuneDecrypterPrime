# D7 tutorial output framework

D7 starts a unified tutorial/session output layer. It is intentionally outside strict runtime modules.

## Layers

- `utils.tutorial_report`: compact `rdp_tutorial_run_report.v1` payload and deterministic renderer.
- `utils.tutorial_benchmark`: typed policy and `rdp_tutorial_benchmark_summary.v1` payload for readable/target/work/time reporting.
- `utils.tutorial_reference`: attachable reference helper for known plaintext/key tutorial data.
- `utils.tutorial_session_report`: bridge from solution plus optional report/reference/policy into one tutorial/session report.

## Boundary

The tutorial/session layer is forgiving. It may accept friendly labels and missing reference pieces while a session is being assembled.

Strict runtime modules must not import tutorial/session helpers. The boundary is tested by `tests/contracts/test_tutorial_helpers_boundary.py`.

## Current D7 scope

D7 establishes the framework and applies the first ScheduledStreamLookup report-output rationalisation. It does not finish all tutorial tuning.

## Follow-on tutorial pass

After D7 validation, run local tutorial packs and tune:

- fast versus long tutorial classification,
- readable and target match thresholds,
- score/eval/token/time budgets,
- unified JSON summaries,
- removal of obsolete bespoke printing.
