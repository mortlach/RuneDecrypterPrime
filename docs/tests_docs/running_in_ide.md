# Running Tests In An IDE Or CLI

## IDE

- Use your editor's built-in pytest runner.
- Point the run configuration at the same Python used for `python install.py`.
- Leave environment variables empty unless a test explicitly documents one.
- Results still land under `output/tests/<timestamp>__tests__pytest__<git>/`; open `logs/app.jsonl` from your IDE run panel if you want to inspect telemetry.

## CLI

```text
pytest -m tier_a
pytest tests/tutorials/test_hybrid_stage2_regression.py -vv
```

The same telemetry and artifact paths are produced as the IDE run because
`tests/conftest.py` initialises `LoggingConfig` for you.
