# Quickstart

Audience: Hands-on / Expert  
Time: 5 minutes  
Outcome: Run the deterministic tutorials and know where the outputs live.  
Prereqs: Followed the steps in `docs/setup/installation.md`.

---

## 1. Hands-on path (Start_Here tutorial)
1. Activate your virtualenv.
2. Run the intro tutorial:

```bash
python tutorials/v1/Start_Here.py
```
3. Expected console output:

```text
[Wrapper Beam] score=0.69
  Plaintext: ᛏᚻᛖᚱᛖ ᚹᚪᛋ ᚪ ᛏᚪᛒᛚᛖ ᛋᛖᛏ …
  Key: [3, 1, 4, 1]

[General Map Beam] score=0.03
  Plaintext: …
  Key: [13, 0, 24, 28]
```
4. Inspect telemetry/logs under
   `output/tutorials/<timestamp>__tutorials__start_here__nogit/`.
5. Compare `telemetry.run` blocks if you need to confirm two runs are identical.

Troubleshooting: see `docs/guides/troubleshooting.md` for simple
checks (venv active, outputs under `output/`, Tier-A tests).

---

## 2. Advanced path (CLI + tests)
Use the CLI for automation and regression tests:
```bash
# Always activate venv first
source .venv/bin/activate          # or .\.venv\Scripts\activate on Windows

# Run a tutorial regression
python -m pytest tests/tutorials/test_mono_substitution.py -q

# Run Tier-A smoke
pytest -m tier_a
```
Pytest writes to `output/tests/<timestamp>__tests__pytest__.../`. Each test gets
its own subfolder under `artifacts/tests/<nodeid>/`.

Keep `seed`, `progress_pct`, and `print_progress` explicit in solver configs so
telemetry stays reproducible.

---

## 3. RunAPI snippet (build your own run)
```python
from rune_decrypter_prime.api import run, KeySpec, SolverSpec, by_name
from rune_decrypter_prime.core.types import Direction

cipher = by_name.cipher("vigenere", key_len=6)
key = KeySpec.repeat(len=6)
solver = SolverSpec.ga(pop_size=64, generations=40, seed=1337, progress_pct=1)

sol = run(
    text="ᛏᚻᛖᚱᛖ ᚹᚪᛋ ᚪ ᛏᚪᛒᛚᛖ ᛋᛖᛏ",
    cipher=cipher,
    key=key,
    solver=solver,
    scorer_params=dict(encoding_dir=Direction.LTR),
    telemetry_on=True,
)
print(sol.plaintext_rune[:80], sol.key)
```
Use this pattern for custom ciphers or to embed Rune Decrypter Prime inside your
own scripts. Outputs still go under `output/<kind>/<run_id>/...`.

---

## Related tests
- `tests/tutorials/test_mono_substitution.py`
- `tests/tutorials/test_hybrid_stage2_regression.py`
- `tests/smoke/test_determinism_canary.py`
