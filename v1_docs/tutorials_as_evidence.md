# Runnable material as evidence

Status: retained V1 reference

RDP’s runnable files have two jobs: make a concrete workflow inspectable and
provide repeatable evidence that the workflow still behaves as claimed. They
are not hidden production scoring rules.

## Owners

| Concern | Owner |
| --- | --- |
| Ordered first route | `tutorials/v1/getting_started/` |
| Human catalogue, assets, runtime and truth disclosure | `tutorials/v1/README.md` |
| Run-group membership and subprocess policy | `tutorials/v1/run_tutorials.py` |
| Scientific result condition | The runnable script’s own assertion or exit status |
| Regression contract | Focused tests under `tests/tutorials/` and `tests/contracts/` |

There is no machine-readable tutorial manifest in V1. This removes a second
taxonomy that could disagree with the scripts and human catalogue.

## Evidence rule

A useful run records which script ran, its asset profile, its configuration and
seed, stop status, result policy, truth/oracle use, and the location of complete
output. Exact and partial recovery must remain distinct.

A score ranks candidates under a configured model. A script passes only when
its own semantic condition is met; the runner does not infer success by parsing
friendly prose.

## Update rule

When runnable material is added or changed, update together:

- the script and its semantic assertion;
- the human catalogue;
- an explicit runner exception set only if group membership changes;
- focused tests for the real behaviour;
- active documentation links.

Do not add a parallel manifest or exact total-count lock. New examples should
be possible without reconstructing an unrelated metadata system.
