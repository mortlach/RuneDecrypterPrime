# Tutorial: Columnar Transposition (Hybrid)

> Tracks: **Hands-on** - run `tutorials/v1/Tutorial_ColumnarTransposition.py`. **Expert** - tweak presets and ensure telemetry stays canonical.

Audience: Hands-on
Time: 10-15 minutes (CPU)
Outcome: Recover plaintext >=98% match, score >=0.62
Prereqs: Python 3.11+, bootstrap complete (`python install.py`)

## What You Build
- Solve a columnar transposition cipher using the Hybrid solver (beam warm start + SA polish).
- Validate the >=0.62 score / >=98% match requirement for Hybrid presets.

## Hands-on Steps
1. Open `tutorials/v1/Tutorial_ColumnarTransposition.py` (see `guides/quickstart.md` if your setup is not ready).
2. Keep `TUTORIAL_SEED = 2025` so ciphertext/key generation stays deterministic.
3. Run `python tutorials/v1/Tutorial_ColumnarTransposition.py`.
4. Observe the beam phase (`progress_pct=1` buckets) followed by SA refinements.
5. Inspect `output/tutorials/<run>/logs/app.jsonl` for `solver_spans` showing beam to SA transitions.

### Reference Snippet
```python
from rune_decrypter_prime.api import run, SolverSpec, KeySpec, by_name
from rune_decrypter_prime.core.types import Direction

solver = SolverSpec.hybrid(
    use_beam=True,
    beam_width=96,
    rounds=6,
    ga=dict(pop_size=48, generations=8),
    sa=dict(sa_iters=3000, sa_init_temp=0.8, sa_cooling=0.995),
    seed=2025,
    progress_pct=1,
    print_progress=True,
)
sol = run(
    text="<columnar ciphertext>",
    cipher=by_name.cipher("columnar", key_len=9),
    key=KeySpec.permutation(len=9),
    solver=solver,
    encoding_dir=Direction.LTR,
    telemetry_on=True,
)
```

Expected: **score >=0.62** and **match >=98%** against the reference plaintext. Falling below signals telemetry or preset drift.

## Expert Notes
- Beam + SA configs live in the tutorial file; Hybrid implementation is in `solvers/hybrid.py`.
- Pipeline block captures permutation info; verify via `tests/telemetry/test_solver_pipeline_block.py` if you change seeds/inputs.
- Regression test: `tests/tutorials/test_hybrid_stage2_regression.py` must pass after any preset tweak.
- When adjusting columns/key length, update the docs and tests accordingly.

## Outputs & Troubleshooting
- Logs: `output/tutorials/<run>/logs/app.jsonl`.
- Spans: look for `solver_spans.hybrid` entries describing beam/GA/SA stages.
- Artifacts: decrypted plaintext + key in `output/tutorials/<run>/artifacts/`.
- For issues, follow `docs/guides/troubleshooting.md` (direction/permutation mismatches are the usual culprit).


