# D6 implementation plan

D6 continues V1 hardening from the final D5 head. It is a cleanup and contract-hardening pass, not a feature pass.

## Verified start state

- Working branch: `prelease/v1.0.0_d6`.
- Baseline branch: `preleasev1.0.0_d5`.
- Verified D6 and D5 are identical at start: `8b549f934748aa15b7cad3b88403c1ba81bf4f18`.
- Verified D6 is ahead of `prelease/v1.0.0_d4` only by the D5 report/artifact contract changes.

GitHub Actions is not treated as the only authority for this stage. Local full pytest/full-proof output remains the immediate release gate unless Actions has been manually fixed or rerun.

## D6 scope

D6 may change only contract, validation, reporting, documentation, tests, and small local runtime hardening needed to remove ambiguity.

D6 must not add:

- solvers;
- ciphers;
- scorer lanes;
- assets;
- broad compatibility layers;
- ranking or scoring behaviour changes.

## Push blocks

### Push 1: verification and real contract tests

- Record the verified D6 baseline.
- Add non-placeholder contract tests for any discovered D6 hardening target.
- Keep docs tied to actual source behaviour.

### Push 2: narrow hardening

- Tighten remaining public/reporting boundaries where D5 still allows contract masking or loose behaviour.
- Prefer explicit `ValueError`/`TypeError` over silent acceptance.
- Keep existing ordinary details payloads working where they do not conflict with generated contract sections.

### Push 3: silent-failure/reporting audit

- Audit broad exception handlers that can make capability/report metadata disappear.
- Convert contract-visible failures into explicit JSON-safe diagnostic payloads where appropriate.
- Leave only genuinely non-contract best-effort logging as best effort.

### Push 4: final tidy and D7 handoff

- Reconcile docs, tests, and implementation.
- Check repo/review-pack hygiene.
- Write D6 summary and D7 handoff.

## D6 first hardening decision

D5 added generated solver-report detail sections:

- `report_contract`;
- `oracle_use`;
- `truth_data_policy`;
- `reproducibility`.

D6 treats those as reserved generated sections. Caller-provided `details` may add ordinary review detail, but must not overwrite or pre-seed those generated sections. This prevents hidden oracle/truth-data masking and keeps solver reports source-backed and reviewable.
