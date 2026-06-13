# Tutorial - Monoalphabetic Substitution (GA)

Audience: Hands-on
Time: 5–7 minutes
Outcome: Recover a substitution key using a GA preset
Prereqs: Python 3.11+, quickstart complete

Goal
- Use a genetic algorithm to recover a substitution key and decrypt the text.

Steps
1. Open `tutorials/v1/Tutorial_MonoSubstitution_GA.py`.
2. Leave the fixed seed as provided.
3. Run. Inspect console progress and final output.
4. Open `output/tutorials/.../logs/app.jsonl` to see `telemetry.solver_progress`.

Shape of the code
```python
from rune_decrypter_prime.api import run, KeySpec, SolverSpec, by_name
from rune_decrypter_prime.core.types import Direction

solver = SolverSpec.ga(pop_size=96, generations=60, seed=12345, progress_pct=1)
cipher = by_name.cipher("mono")
key = KeySpec.permutation(len=29)

solution = run(
    text="ᚠᚢᚦ…",  # ciphertext runes or indices
    cipher=cipher,
    key=key,
    solver=solver,
    scorer="rune",
    scorer_params=dict(objective="pct.logp.win10", encoding_dir=Direction.LTR),
    telemetry_on=True,
)
print(solution.score, str(solution.plaintext_rune)[:120])
```

Notes
- GA combines and mutates permutation keys.
- Expect score to rise quickly and then plateau.
- Deterministic: same seed -> same run history.

See also
- `../architecture/optimisers.md`
- `../architecture/keyops.md`

Related tests
- `tests/tutorials/test_mono_substitution.py`
- `tests/tutorials/test_ga_stage2_regression.py`

