# Running Tests (IDE & CLI)

## IDE
- Use your editor’s built-in pytest runner (right-click a test file/folder such as `tests/tutorials` and choose the pytest run/debug option).
- Point the run configuration at the project virtual environment (`.venv/bin/python` on macOS/Linux or `.venv\Scripts\python.exe` on Windows).
- Leave environment variables empty unless a test explicitly documents one.
- Results still land under `output/tests/<timestamp>__tests__pytest__<git>/`; open `logs/app.jsonl` from your IDE’s run panel if you want to inspect telemetry.

## CLI
```powershell
.\.venv\Scripts\activate
pytest -m tier_a
pytest tests/tutorials/test_hybrid_stage2_regression.py -vv
```
- Use `PYTEST_ADDOPTS=-q` to keep CI quiet.
- The same telemetry and artifacts paths are produced as the IDE run because `tests/conftest.py` initialises `LoggingConfig` for you.

