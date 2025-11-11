# Running Tests (PyCharm & CLI)

## PyCharm
- Right-click on a test file or folder (e.g., `tests/tutorials`) and choose **Run "Pytest in ..."**.
- Select the project virtualenv (`.venv/Scripts/python.exe`) as the interpreter for that Run/Debug configuration.
- Leave environment variables empty unless a test explicitly documents one.
- Outputs land in `output/tests/<timestamp>__tests__pytest__<git>/`; open `logs/app.jsonl` from the Run tool window.

## CLI
```powershell
.\.venv\Scripts\activate
pytest -m tier_a
pytest tests/tutorials/test_hybrid_stage2_regression.py -vv
```
- Use `PYTEST_ADDOPTS=-q` to keep CI quiet.
- The same telemetry and artifacts paths are produced as the IDE run because `tests/conftest.py` initialises `LoggingConfig` for you.

