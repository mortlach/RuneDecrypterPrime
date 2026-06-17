# V1 release acceptance gates

This document is the V1 closure checklist. It is intentionally contract-focused and belongs under `docs/release_contracts/v1/` to avoid root-folder release clutter.

## Scope gate

V1 closure must not add new release features. A closing branch may harden labels, contracts, tests, workflow evidence, documentation, and review-pack generation, but must not add:

```text
new solvers
new ciphers
new scorer lanes
new assets
new ranking behaviour
new scoring behaviour
broad compatibility shims
monkey patches
root-folder release notes
```

## Contract-label gate

Stable V1 labels must be enum-owned or constant-owned in the owning module.

This includes stable modes, policies, report detail keys, artifact classifications, stop categories, execution-route labels, solver parameter keys, oracle/truth-data labels, and scorer telemetry source labels that are used to derive public report sections.

Raw strings are acceptable only for:

```text
free text
human notes
exception messages
user paths
solver names
arbitrary telemetry payload values
public/config boundary input before immediate validation
```

## Public-output gate

Enum hardening must not change public output strings.

Required checks:

```text
ScoringConfig.asdict() emits stable string values
solver reports emit stable JSON strings
scorer reports emit stable JSON strings
artifact manifests emit stable JSON strings
workflow/tutorial logs remain UTF-8 safe
```

## Report-only gate

Report-only diagnostics may appear in reports, but they must not affect:

```text
score
raw_score
ranking order
tie-breaks
candidate selection
solver stopping
```

Any new report-only or diagnostic surface needs a focused test showing the scoring/ranking values are unchanged.

## Run/block/report gate

Requested production capabilities must not silently disappear.

A requested production capability must do one of:

```text
run
block with an explicit reason
report an explicit fallback/degradation
```

Best-effort diagnostics may fail without blocking only when the failure is made visible in JSON-safe diagnostics or is genuinely outside the release contract.

## Required local gates before closure

Run the focused contract tests first:

```text
tests/api/test_artifact_agreement.py
tests/api/test_run_artifact_manifest.py
tests/api/test_run_artifact_manifest_classification_contract.py
tests/api/test_solver_report_enum_contract.py
tests/api/test_solver_report_truth_repro_contract.py
tests/api/test_stop_reason_contract.py
tests/contracts/test_d6_ci_branch_contract.py
tests/contracts/test_d6_docs_contract.py
tests/contracts/test_v1_contract_label_guardrails.py
tests/contracts/test_v1_full_proof_workflow_contract.py
tests/core/test_scoring_config_label_contract.py
tests/scoring/test_scorer_report_builder_diagnostics.py
tests/scoring/test_scorer_report_label_contract.py
tests/scoring/test_scorer_report_builder.py
```

Then run full pytest:

```text
pytest -q -ra -p no:cacheprovider tests
```

## Tutorial gate

The V1 release tutorial runner must pass from the final V1 branch head:

```text
python -X utf8 tutorials/v1/run_all.py
```

The full-proof workflow must also run this tutorial gate.

## CI gate

The full-proof workflow must remain manually runnable through `workflow_dispatch` and must include the active V1 closure branch in push coverage.

For D7 this means:

```text
prelease/v1.0.0_d7
```

A final release note must record either green full-proof CI evidence or clearly labelled equivalent local proof.

## Review-pack gate

The final review pack must be regenerated from the final branch head after all D7 commits.

The final review pack should include:

```text
source files
tests
docs/release_contracts/v1/
workflow files
asset manifest
install/smoke tooling
```

It should not include:

```text
large generated outputs
runtime logs
pytest cache
__pycache__
local planning folders
temporary zip bundles
private local config
```

The review pack is evidence, not source authority. The GitHub branch remains the source of truth.

## Final D7 closeout gate

D7 may close only when all of the following are true:

```text
full pytest passes or failures are explicitly evidenced and accepted
full-proof CI passes or equivalent local proof is documented
V1 release tutorials pass
review pack is regenerated from final D7 head
stable labels are enum-owned or constant-owned
public JSON/config strings are unchanged
diagnostics remain report-only
oracle/truth-data use remains explicit
artifact export surface remains declared
no new V1 feature scope is added
remaining intentionally raw fields are named explicitly
```
