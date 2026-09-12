# Two-period development fixture

"Pack 09" is the internal name for the final retained P13/P31 overlapping
two-period development fixture from the V1 work.

The name is historical rather than a contribution format. This particular
experiment became complicated enough that, once it was working, I wanted to
freeze the exact Python dependency closure as well as the input/recipe. That way
a later code or line-ending change could not quietly turn the retained result
into a different experiment.

Run it only through `cipher_development/run_experiment.py`. Its exact recursive
Python dependency closure is recorded in
`docs/release_contracts/v1/two_period_fixture_manifest.json`.

The normal public route starts with `from rdp import api` and uses
`api.SolverSpec.two_period_cribs(...)` through `api.run(...)`. Historical staged,
multiscale and ranking runners were removed; their history remains available
through Git.

Pack 09 is a long specialist campaign and must not run in normal CI. The
production package and wheel must never import or include `cipher_development`;
the curated fixture is a separate source-release concern. Every run requires an
explicit absolute output root outside the repository. Smoke mode is the default
and performs only the deterministic Pack 09 contract preflight.

The pinned manifest is useful here because this is a retained development
fixture whose result we want to notice if it drifts. Ordinary solving attempts
do not need to copy this machinery.
