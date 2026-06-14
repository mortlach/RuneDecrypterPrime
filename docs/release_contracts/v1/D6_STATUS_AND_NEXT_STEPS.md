# D6 status and next steps

D6 is currently a narrow hardening branch from final D5 head `8b549f934748aa15b7cad3b88403c1ba81bf4f18`.

## Completed so far

D6 has covered these contract areas:

- verified `prelease/v1.0.0_d6` starts from the final D5 head;
- restored full-proof workflow coverage for the active D6 branch;
- restored the V1 release tutorial gate in full-proof CI;
- prevented caller-provided solver-report details from masking generated `report_contract`, `oracle_use`, `truth_data_policy`, and `reproducibility` sections;
- made scorer-report telemetry and `last_stats()` failures explicit through `report_builder_diagnostics` instead of silently dropping them;
- reserved `report_builder_diagnostics` so caller-provided `extra_details` cannot mask generated report-builder diagnostics;
- removed the duplicate manifest-local `Classification = str` alias so manifest classification type information comes from the artifact agreement authority;
- added focused contract tests for each changed behaviour.

## Design alignment

These changes stay inside V1 hardening scope. They do not add solvers, ciphers, scorer lanes, assets, ranking behaviour, broad compatibility layers, or new runtime feature paths.

The common rule is unchanged:

> Requested production capability must run, block, or report explicit fallback. Report-only capability must be visible but must never affect ranking.

## Remaining D6 candidates

Before closing D6, only small contract/hygiene checks should remain:

1. Wait for GitHub CI/full-proof output and fix any real failures.
2. Audit artifact agreement path classification for wording drift between docs and source.
3. Do a final grep-style review for broad exception handlers that can hide report/capability metadata.
4. Write final D6 summary and D7 handoff.

Avoid further broad refactors unless CI or review exposes a concrete contract mismatch.
