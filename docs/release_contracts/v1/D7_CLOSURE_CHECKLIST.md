# D7 closure checklist

D7 is the final V1 contract-closure branch. It is not a feature branch.

The branch is considered closed only when the release-contract evidence, focused contract tests, compact smoke tests, tutorial gate, and full pytest/CI evidence are green after the final commit.

## Scope rule

- Public/API boundaries may stay forgiving: aliases, friendly strings, and compatibility wrappers are allowed when they normalise to canonical internals.
- Core RDP boundaries must stay strict: typed configs, stable enum domains, explicit scorer capability states, no silent requested-lane fallback, no hidden modulo wrapping of literal config, no truth/oracle drift, and no experimental rank effect in V1.

## Release-contract evidence

Required release-contract files:

- `final_source_to_wp_decision_target_test_chain.csv`
- `final_missing_or_new_acceptance_tests.csv`
- `v1_scope_lock.json`
- `D7_CLEANUP_DEPRECATION_POLICY.md`
- `v1_cleanup_deprecation_ledger.json`
- `d7_acceptance_test_promotion_status.csv`

The D7 promotion status must have no silent pending rows. Rows are either:

- `implemented`, with a real test file in this repo, or
- `not_v1_production`, with an explicit experimental path and explanation.

## Acceptance themes closed by D7

- Source traceability and source-decision completeness.
- V1 scope lock and no silent spec drift.
- API compatibility aliases retained/deprecated deliberately.
- Raw strings accepted only at API/config boundaries, then normalised to core enums.
- Requested production scorer lanes block instead of warning and disappearing.
- Report-only lanes remain report-only and have no production rank effect.
- ScheduledStreamLookup strict config, schedule modes, degeneracy policy, wrapper aliases, and literal fixed-symbol semantics.
- Artifact agreement and public artifact path portability.
- Oracle/truth separation in solver reports.
- Stop-reason schema hardening.
- LM root/index and ECDF asset-status validation through concrete V1 helpers.

## Required local/CI commands

Focused D7 closure gate:

```bash
python -m pytest -q tests/contracts tests/core tests/api tests/ciphers tests/scoring/language_model
```

Compact V1 smoke:

```bash
python -m pytest -q -p no:cacheprovider tests/contracts tests/api/test_scheduled_stream_lookup_wrappers.py tests/ciphers/test_scheduled_stream_lookup_cipher.py tests/tutorials/test_scheduled_stream_lookup_pipeline_smoke.py
```

Full test gate:

```bash
python -m pytest -q -ra -p no:cacheprovider tests
```

Tutorial/release gate should be run with the existing project tutorial runner used by CI/release evidence.

## Closure criteria

- No full-pytest failures.
- No collection/import mismatch failures.
- No unregistered pytest marker warnings.
- No acceptance-status rows marked pending.
- No V1 production promotion for experimental/report-only work.
- No deletion of release-contract traceability evidence.
- No final branch changes after green CI unless CI is rerun.
