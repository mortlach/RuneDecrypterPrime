# Cipher development

`cipher_development/` contains a small set of deterministic investigations that
remain useful after their production behaviour has stabilised. It is not a
public API, tutorial collection, solver framework, or robustness campaign.

- Production ciphers, scorers and solvers live under `src/rdp/`.
- Public teaching examples live under `tutorials/`.
- Repeatable multi-family qualification lives in `tools/robustness/`.
- This directory holds only focused diagnostic or scientific fixtures.

## Run an experiment

Edit the four constants at the top of `cipher_development/run_experiment.py`:

```python
EXPERIMENT = "autokey"
MODE = "smoke"
SEED = 20260822
OUTPUT_LOCATION = ... / "run_outputs" / "cipher_development"
```

Then run:

```text
python cipher_development/run_experiment.py
```

There are no environment-variable or command-line configuration layers. The
script resolves the repository from its own location, prints the selected
recipe/profile, seed, asset profile and output path, and refuses repository
output or silent overwrite.

`smoke` is the default and performs the smallest meaningful deterministic
check. Pack 09 also exposes its retained long `development` study. Autokey is
deliberately one-case replay only; run its 20-case qualification through
`tools/robustness/cipher_solver_campaign.py`.

## Retained experiments

| Entry-point name | Purpose | Smoke assets | Development assets |
|---|---|---|---|
| `autokey` | Replays one deterministic case with the canonical qualified Autokey Beam recipe | `ci_light` | Use `tools/robustness` for 20 cases |
| `two_period_pack09` | Preserves the final Pack 09 P13/P31 d30 scientific fixture | `ci_light` | `full_v1` |
| `periodic_columnar_staged` | Qualified the P7/C7 RTL periodic-columnar solve through deterministic head reduction, exhaustive C7 tails and one integrated refinement | `full_v1` | `periodic_columnar_decomposed_v2` |

The periodic-columnar qualification uses the same single entry point as every
retained development experiment. Set its constants to:

```python
EXPERIMENT = "periodic_columnar_staged"
MODE = "development"
SEED = 12345
```

Then run:

```text
python -X utf8 cipher_development/run_experiment.py
```

It fixes the recipe in source and enforces a 60-minute wall-clock limit.
Standard output and errors are mirrored to the visible terminal and to a
timestamped transcript under
`run_outputs/tests/cipher_development/`. Search-visible evidence contains
no benchmark truth; exact recovery is assessed only in the separate terminal
evaluation artifact. The retained qualification recovered all 2,489 plaintext
symbols in 36 minutes 38 seconds; full evidence and hashes are recorded in the
workflow README.

Autokey obtains its scorer, Beam budget, restart count, seed handling and
acceptance rule directly from `CAMPAIGN_RECIPES`. It does not redefine them.
Its WLI1+2 recipe is correctly supported by the `ci_light` asset profile.

Pack 09's recursive source closure is recorded in
`docs/release_contracts/v1/two_period_fixture_manifest.json`. Its smoke mode is
a bounded contract preflight. Its development mode is a long specialist run,
requires the downloaded `full_v1` asset pack and must not be started as a
normal test or tutorial.

Missing required language-model assets fail through the canonical RDP asset
resolver. Do not add local asset roots, copied books, fallback searches or
sample-as-full substitutions here.

## Evidence rules

- Seeds and frozen recipes/profiles are explicit.
- Truth, plaintext and known keys may classify a completed benchmark result;
  they must never select candidates, rank attempts or stop production search.
- Generated JSON, JSONL, logs and review packs belong under the configured
  external `run_outputs/cipher_development/` root and are never committed.
- A repeated smoke run with the same seed reconstructs the same case and
  result. Use a fresh output location when preserving both runs.

## Adding a future experiment

Before adding one, confirm that it:

1. asks a distinct unresolved question;
2. uses existing RDP ciphers, scorers, solvers and asset resolution;
3. has an explicit deterministic seed and bounded smoke path;
4. keeps truth out of ranking and selection;
5. writes only to external `run_outputs`;
6. blocks clearly when its declared asset profile is missing;
7. has focused tests and a short README entry;
8. does not duplicate `tools/robustness` or introduce a public framework.
