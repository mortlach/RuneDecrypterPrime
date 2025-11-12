# Troubleshooting & Quick Tests

Audience: Hands-on / Expert  
Time: 3–5 minutes per issue  
Goal: Recover from the most common setup and runtime problems without digging through the entire codebase.

---

## 1. Environment checklist
Run these commands inside your repo root:

| Check | Command | Expected |
| --- | --- | --- |
| Virtualenv active | *(prompt shows)* `(.venv)` | `(.venv)` prefix before every command |
| Package installed | `python -m pip list | findstr rune` | `rune-decrypter-prime` shows `editable` path |
| Python version | `python --version` | `3.11.x` |
| PYTHONPATH (only if needed) | `echo $env:PYTHONPATH` or `echo $PYTHONPATH` | Either empty or pointing at `src/` |

If any check fails, re-run the steps from `docs/setup/installation.md`.

---

## 2. Frequent issues

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: rune_decrypter_prime` | venv not activated or IDE not pointing at `src/` | Activate `.venv` and mark `src/` as the source root (PyCharm/VS Code). |
| `torch` missing or fails to import | Torch CPU wheel skipped (common on lab machines) | Set `RDP_TORCH=0` before `pip install -e .[dev]`, or re-run the install to pull the CPU wheel. |
| Tutorial prints zero progress | Solver config left at defaults | Set `print_progress=True` and keep `progress_pct=1` when teaching/demonstrating. |
| Files end up outside `output/` | Commands run from the wrong directory | `cd` into the repo root and re-run; check `pwd`/`Get-Location`. All scripts should write under `output/<kind>/...`. |
| Start_Here outputs differ between machines | Different seeds/directions/permutations | Compare `output/tutorials/.../logs/app.jsonl` → `telemetry.run`. Seeds and `text_encoding_direction` must match. |

If you see corrupted logs or telemetry fields missing, delete the run folder under `output/` and re-run after fixing the root cause.

---

## 3. Quick validation commands
Use these whenever you set up a new machine or after a large dependency change.

### A. Tutorial smoke (≈1 minute)
```bash
source .venv/bin/activate      # or .\.venv\Scripts\activate
python tutorials/v1/Start_Here.py
```
Check for both console blocks (Wrapper Beam / General Map) and verify logs under `output/tutorials/...`.

### B. Tier-A slice (≈2 minutes)
```bash
pytest tests/tutorials/test_mono_substitution.py -m tier_a -q
```
This enforces the GA/SA mono score threshold (≥0.55) and confirms telemetry writes to `output/tests/...`.

### C. Telemetry contract
```bash
pytest tests/telemetry/test_schema_contract.py -q
```
Useful when editing logging or telemetry modules.

Set `PYTHONPATH=src` if your IDE shell doesn’t mark `src/` as a source root.

---

## 4. When to escalate
Contact maintainers (or open a GitHub issue) if:

- Deterministic runs (same seed/config) produce different scores across machines after rerunning the quick tests above.
- `telemetry.run` or solver progress events are missing from JSONL logs despite `telemetry_on=True`.
- `output/.../META.json` contains personal data and `LoggingConfig.redact_identity=True` didn’t help.

Include the failing command, full traceback, `python --version`, and the relevant `output/<kind>/<run_id>/logs/app.jsonl` snippet.

---

## Related docs
- `docs/setup/installation.md` – one-time setup steps.
- `docs/guides/architecture.md` – explains the pipeline, which helps when comparing telemetry blocks.
- `docs/guides/quickstart.md` – examples of successful runs and their expected output folders.
