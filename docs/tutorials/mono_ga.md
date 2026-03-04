# Tutorial: Monoalphabetic Substitution (GA)

> Tracks: **Hands-on** - run `tutorials/v1/Tutorial_MonoSubstitution_GA.py`. **Expert** - tune GA presets and validate regressions.

Audience: Handsâ€‘on
Time: 8-12 minutes (CPU)
Outcome: Recover plaintext, score â‰¥0.55
Prereqs: Python 3.11+, bootstrap complete (`python install.py`)

## Goal & Requirements
- Recover the mono substitution key using GA with no prior crib.
- Hit =0.55 mono score to satisfy tutorial regression tests.

## Hands-on Steps
1. Open `tutorials/v1/Tutorial_MonoSubstitution_GA.py` (environment setup: `guides/quickstart.md`).
2. Keep `TUTORIAL_SEED = 12345` and `CIPHERTEXT_SEED = 12345` for reproducible plaintext/key generation.
3. Run the script; it encrypts a reference English passage, then launches GA with seeded frequency-derived starting keys.
4. Watch the progress buckets; once finished, the script prints recovered plaintext and score.
5. Compare your `output/tutorials/.../logs/app.jsonl` to another solver's run (the telemetry pipeline hash should match).

### Snippet
```python
from rune_decrypter_prime.api import run, SolverSpec, KeySpec, by_name
from rune_decrypter_prime.core.types import Direction

sol = run(
    text="<mono ciphertext>",
    cipher=by_name.cipher("mono"),
    key=KeySpec.permutation(len=29),
    solver=SolverSpec.ga(pop_size=80, generations=120, seed=1234, progress_pct=1, print_progress=True),
    scorer="rune",
    scorer_params=dict(objective="pct.logp.win10", encoding_dir=Direction.LTR),
    encoding_dir=Direction.LTR,
    telemetry_on=True,
)
print(sol.best_plaintext, sol.score)
```

## Expert Notes
- Frequency-based seeds come from `rune_decrypter_prime.utils.seed_utils.make_seeds_from_freq`; tweaking this impacts convergence.
- GA implementation identical to the Vigenere tutorial; only cipher/keyops differ.
- Regression coverage: `tests/tutorials/test_mono_substitution.py` (GA + SA cases) ensures =0.55 score.
- Telemetry pipeline captures permutation summary; verify via `tests/pipeline/test_permutation_tracking.py` if you change inputs.

## Outputs & Troubleshooting
- Logs: `output/tutorials/<run>/logs/app.jsonl`
- Artifacts: plaintext/key preview in `output/tutorials/<run>/artifacts/`
- If GA stalls below threshold, re-run the tutorial ensuring seeds/virtualenv are correct; see troubleshooting appendix for more tips.


