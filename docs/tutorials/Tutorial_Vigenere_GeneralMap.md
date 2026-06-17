# Tutorial - Vigenere / General-Map (GA)

Audience: Hands-on
Time: 4–6 minutes
Outcome: Recover a Vigenere key of known length using GA
Prereqs: Python 3.11+, quickstart complete

Goal
- Recover a Vigenere key of known length using GA and observe WLI behaviour.

Steps
1. Open `tutorials/v1/Tutorial_Vigenere_GeneralMap.py`.
2. Ensure `key_len` is set in the wrapper call.
3. Run and check plaintext clarity and final score.

Shape of the code
```python
from rune_decrypter_prime.api import run, KeySpec, SolverSpec, by_name
from rune_decrypter_prime.core.types import Direction

cipher = by_name.cipher("vigenere", key_len=5)
key = KeySpec.repeat(len=5)
solver = SolverSpec.ga(pop_size=64, generations=40, seed=5150, progress_pct=1)

solution = run(
    text="ᚠᚢᚦ…",  # ciphertext runes or indices
    cipher=cipher,
    key=key,
    solver=solver,
    scorer="rune",
    scorer_params=dict(objective="pct.logp.win10", encoding_dir=Direction.LTR),
    telemetry_on=True,
)
print(solution.score)
```

Notes
- Vector keys: GA mutations wrap values modulo 29.
- GA converges quickly for reasonable lengths.
- WLI pairs are visible in telemetry.

See also
- `../architecture/data.md`
- `../architecture/keyops.md`

Related tests
- `tests/tutorials/test_ga_stage2_regression.py`
- `tests/tutorials/test_sa_stage2_regression.py`

