# Tests Folder

Automated tests for API, ciphers, scoring, solvers, telemetry, tools, and tutorials.

## Run all tests

`python -m pytest tests -q`

## Common issue

Some community tests require `jsonschema`. If collection fails with
`ModuleNotFoundError: jsonschema`, install it in your environment:

`python -m pip install jsonschema`

## Useful subsets

- Core smoke: `python -m pytest tests/smoke -q`
- Tutorials: `python -m pytest tests/tutorials -q`
- Benchmarks/community tooling: `python -m pytest tests/community -q`
