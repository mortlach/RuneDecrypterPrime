# Tutorial - Columnar Transposition (Hybrid)

Audience: Hands-on
Time: 5–8 minutes
Outcome: Recover the column order and plaintext with a Hybrid preset
Prereqs: Python 3.11+, quickstart complete

Goal
- Solve a columnar transposition using a Hybrid strategy (Beam -> GA -> SA).

Steps
1. Open `tutorials/v1/Tutorial_ColumnarTransposition.py`.
2. Run as-is; watch phase changes in console and telemetry.
3. Inspect `logs/app.jsonl` for `"phase":"beam"` -> `"ga"` -> `"sa"`.

Shape of the code
```python
from rune_decrypter_prime.api import run, KeySpec, SolverSpec, by_name
from rune_decrypter_prime.core.types import Direction

solver = SolverSpec.hybrid(beam=dict(beam_width=128), sa=dict(sa_iters=4000), seed=2024)
cipher = by_name.cipher("columnar", cols=7)
key = KeySpec.permutation(len=7)

solution = run(
    text="ᚠᚢᚦ…",  # ciphertext runes or indices
    cipher=cipher,
    key=key,
    solver=solver,
    scorer="rune",
    scorer_params=dict(objective="pct.logp.win10", encoding_dir=Direction.LTR),
    telemetry_on=True,
)
print(list(solution.key))           # column order
print(str(solution.plaintext_rune)[:120])
```

Notes
- Beam narrows ordering; GA recombines; SA fine-tunes.
- Telemetry records spans per phase; see `telemetry.solver_spans` in `logs/app.jsonl`.
- Direction/permutation belong to the Pipeline (not the cipher implementation).

See also
- `../architecture/pipeline.md`
- `../architecture/optimisers.md`

Related tests
- `tests/tutorials/test_hybrid_stage2_regression.py`
- `tests/tutorials/test_ga_stage2_regression.py`

