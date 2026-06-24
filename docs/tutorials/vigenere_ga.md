# Tutorial: Vigenere (GA)

> Tracks: **Hands-on** - follow the steps to run `tutorials/v1/Tutorial_Vigenere_GeneralMap.py`. **Expert** - learn which modules/tests back the preset.

Audience: Hands-on
Time: 5-10 minutes (CPU)
Outcome: Recover plaintext, score >=0.55
Prereqs: Python 3.11+, bootstrap complete (`python install.py`)

## What You Build
- Decrypt a seeded Vigenere ciphertext using the GA solver.
- Observe deterministic telemetry buckets and verify =0.55 mono score.

## Hands-on Steps
1. Open `tutorials/v1/Tutorial_Vigenere_GeneralMap.py` (setup help: `guides/quickstart.md`).
2. Keep `TUTORIAL_SEED = 12345` so your run matches other solvers.
3. Execute `python tutorials/v1/Tutorial_Vigenere_GeneralMap.py`.
4. Watch the GA progress lines (`pct=... best_score=...`). When it finishes, note the plaintext preview and score.
5. Inspect `output/tutorials/<timestamp>__tutorials__vigenere__<git>/logs/app.jsonl` for the `telemetry.run` block.

### Reference Snippet
```python
from rune_decrypter_prime.api import run, SolverSpec, KeySpec, by_name
from rune_decrypter_prime.api.specs import ScoringConfig
from rune_decrypter_prime.core.types import Direction

sol = run(
    text="??????",
    cipher=by_name.cipher("vigenere", key_len=6),
    key=KeySpec.repeat(len=6),
    solver=SolverSpec.ga(pop_size=64, generations=80, seed=1337, progress_pct=1, print_progress=True),
    scorer="rune",
    scorer_params=ScoringConfig(objective="pct.logp.win10", encoding_dir=Direction.LTR).__dict__,
    encoding_dir=Direction.LTR,
    telemetry_on=True,
)
print(sol.best_plaintext, sol.score)
```

Expected score: **=0.55** mono match on CPU.

## Expert Notes
- GA implementation lives in `src/rune_decrypter_prime/solvers/ga.py`; presets are defined at the bottom of the tutorial file.
- Progress events come from `solvers/solver_base.py`; telemetry spans are emitted via `telemetry/events.py`.
- Update docs + `tests/tutorials/test_ga_stage2_regression.py` if you change pop/generation defaults.
- Scoring preset references `scoring/scoring_adapter.py`; keep `encoding_dir` aligned with tutorial text.

## Outputs & Troubleshooting
- Logs: `output/tutorials/<run>/logs/app.jsonl`
- Traces: `output/tutorials/<run>/trace/`
- Artifacts (plaintext/key previews): `output/tutorials/<run>/artifacts/`
- If telemetry is missing or folders appear outside `output/`, follow `docs/guides/troubleshooting.md`.


