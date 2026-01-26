# Scorer benchmark tests (Kaeding-aligned + drift alarm)

This pack adds a set of **scoring correctness / drift** tests for RuneDecrypterPrime.

The goal is not to “solve” anything yet — it is to make sure the scorer is behaving in a **controlled, reproducible** way, and that we can **reproduce paper-style scoring** (Kaeding’s “average log tetragram fitness”, adapted to our 29‑symbol alphabet).

## Where to put these files

Copy the `tests/scoring/` subtree in this ZIP into your repo, merging with the existing `tests/scoring/` folder.

You should end up with (at least) these new files:

- `tests/scoring/test_scorer_kaeding_style_avg_logp.py`
- `tests/scoring/test_scorer_pct_edges_and_clamps.py`
- `tests/scoring/test_lm_raw_data_integrity.py`
- `tests/scoring/test_scorer_smoothing_effect.py`
- `tests/scoring/generate_scorer_baselines.py`
- `tests/scoring/_helpers/lm_test_guard.py`

## Data / LM tables (why tests skip)

The repo does not ship the full language‑model tables (they’re large), so the tests that need them **skip cleanly** unless the tables are present.

These tests look for the LM root returned by:

- `rune_decrypter_prime.scoring.language_model.paths.default_lm_root()`

In practice, that means you must place the full LM asset set under the same folder that your scorer uses by default.

If you keep the tables elsewhere, the most PyCharm‑friendly approach is:
- copy/symlink the tables into the default LM root, or
- edit `default_lm_root()` (or add a small local override in your own branch).

## Drift alarm baseline (recommended)

Some tests become *much* more valuable once you lock a baseline, so that any change to:
- LM tables (counts / zeros / ranges),
- ECDF grids (clamping behaviour),
- scoring defaults (floor/ceiling),
- smoothing behaviour,

is caught immediately.

To generate the baseline:

1. Open `tests/scoring/generate_scorer_baselines.py` in PyCharm
2. Run it (Run ▶)

It will write:

- `tests/scoring/_baselines/scorer_drift_baseline.json`

After that, the integrity tests will compare current fingerprints against that baseline and fail on drift.

## What the tests cover

- **Kaeding‑style scoring (AVG logp / tetragrams):**
  - real text scores better than random
  - standard deviation shrinks with longer passages
  - LTR score matches RTL score on reversed text (integrity of the RTL tables)

- **PCT scoring edge cases:**
  - if the text is too short for win=10, the score aliases to `ecdf_floor` (default `1e-6`)
  - window percentiles and final score respect `ecdf_floor` / `ecdf_ceiling`

- **Raw LM asset integrity:**
  - joint tables have the expected header, shapes, and contain zeros
  - non-zero entries are finite and behave like log probabilities
  - ECDF grids are monotone and map to q in [0, 1] ending at exactly 0 and 1
  - optional baseline comparison (drift alarm)

- **Smoothing sanity:**
  - changing smoothing (e.g. `none` vs `auto_gt`) changes scores for random text
  - telemetry records the smoothing choice
