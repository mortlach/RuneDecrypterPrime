# Tests

Tests protect the public request, scientific behaviour, package boundaries and retained
release contracts. Start with the component affected by your change. `conftest.py`
supplies shared fixtures; `harness.py` supports controlled execution. Many solver and
asset tests are expensive. Read the selected test before running it and use the
documented asset markers.

Useful entry points: [test_artifact_policy.py](test_artifact_policy.py), [test_logging_paths.py](test_logging_paths.py), [test_run_logger_paths.py](test_run_logger_paths.py).

See [test selection and tiers](../docs/tests_docs/tiering.md) for the wider testing context.
