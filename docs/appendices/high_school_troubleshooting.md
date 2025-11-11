# High School Troubleshooting & Quick Tests

This appendix helps Hands-on users recover from common issues without deep CLI knowledge.

## Environment Checklist
1. **Virtual environment active** - the shell prompt should show `(.venv)` before running tutorials.
2. **Dependencies installed** - run `python -m pip list | findstr rune` to confirm `rune-decrypter-prime` is editable-installed.
3. **Python 3.11** - `python --version` should report `3.11.x`.

## Frequent Issues
| Symptom | Fix |
| --- | --- |
| `ModuleNotFoundError: rune_decrypter_prime` | Activate `.venv` and ensure the repo root (`src/`) is on `PYTHONPATH` (PyCharm: mark `src/` as a Sources Root). |
| `torch` missing | Re-run `pip install -e .[dev]` or set `RDP_TORCH=0` before reinstalling if the lab machines cannot use Torch. |
| Tutorial prints no progress | Set `print_progress=True` and keep `progress_pct=1` in `SolverSpec`. |
| Files written outside the repo | Start shells in the repo root and verify `pwd`/`Get-Location` before running commands. |

## Simplified Test Target
For quick Hands-on validation (~2 minutes on lab hardware):
```powershell
$env:PYTHONPATH = 'src'
pytest tests/telemetry/test_schema_contract.py tests/tutorials/test_mono_substitution.py -m tier_a -q
```
This runs the telemetry contract plus the GA/SA tutorial regression enforcing the >=0.55 mono score requirement.

## When To Escalate
- Deterministic scores diverge between machines.
- Telemetry JSON is missing required fields (`telemetry.run`, `solver_progress`).
- `output/` contains personal data or absolute paths - delete the folder and rerun the tests/tutorials.

Escalate with the failing command, full traceback, and the `.venv` Python version.

