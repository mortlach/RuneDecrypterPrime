# Two-period development fixture

`pack09.py` is the final retained WP6 scientific/development fixture for the V1
source release. Its exact recursive Python dependency closure is recorded in
`docs/release_contracts/v1/two_period_fixture_manifest.json`.

The normal public route is `SolverSpec.two_period_cribs(...)` through
`api.run(...)`. Earlier experiment files remain repository evidence and are not
recommended public API examples.

Pack 09 is a long scientific campaign and must not run in normal CI. The
production package and wheel must never import or include `cipher_development`;
the curated fixture is a separate source-release concern.
