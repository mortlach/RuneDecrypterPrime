# Two-period development fixture

Pack 09 is the final retained WP6 scientific/development fixture for the V1
source release. Run it only through `cipher_development/run_experiment.py`.
Its exact recursive Python dependency closure is recorded in
`docs/release_contracts/v1/two_period_fixture_manifest.json`.

The normal public route starts with `from rdp import api` and uses
`api.SolverSpec.two_period_cribs(...)` through `api.run(...)`. Historical staged,
multiscale and ranking runners were removed;
their history remains available through Git.

Pack 09 is a long scientific campaign and must not run in normal CI. The
production package and wheel must never import or include `cipher_development`;
the curated fixture is a separate source-release concern. Every run requires an
explicit absolute output root outside the repository. Smoke mode is the default
and performs only the deterministic Pack 09 contract preflight.
