# Quickstart

Audience: Hands-on / Expert
Time: 5 minutes
Outcome: Run a deterministic tutorial and find its outputs
Prereqs: Python 3.11+, repo set up (venv, deps installed)

Two common entry points share the same deterministic contracts.

## Track 1 - Hands-on snippet
```python
from rune_decrypter_prime.api import run, KeySpec, SolverSpec, by_name
from rune_decrypter_prime.core.types import Direction

SEED = 1337
cipher = by_name.cipher("vigenere", key_len=6)
key = KeySpec.repeat(len=6)
solver = SolverSpec.ga(pop_size=64, generations=40, seed=SEED, progress_pct=1, print_progress=True)

solution = run(
    text="??????",
    cipher=cipher,
    key=key,
    solver=solver,
    scorer_params=dict(encoding_dir=Direction.LTR),
    telemetry_on=True,
)
print(solution.plaintext_rune[:120])
```
Outputs appear in `output/tutorials/<timestamp>__tutorials__v1__<git>/`.

Troubleshooting: see `docs/appendices/high_school_troubleshooting.md` for a checklist and the two-test Tier-A command.

## Track 2 - Advanced test slice
```powershell
# Activate your environment
.\.venv\Scripts\activate

# Run a focused tutorial test and view output
python -m pytest tests/tutorials/test_mono_substitution.py -q
```
Pytest writes to `output/tests/...` (see `tests/conftest.py`).

Keep `seed`, `progress_pct`, and `print_progress` explicit so telemetry traces stay reproducible across both tracks.

## Related tests
- `tests/tutorials/test_mono_substitution.py`
- `tests/tutorials/test_hybrid_stage2_regression.py`
- `tests/smoke/test_determinism_canary.py`

