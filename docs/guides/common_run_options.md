# Common run options

Status: user guide

Most users start with tutorials and do not need to change many settings. This
page explains the names you will see in tutorial output and examples.

## Gate profile

A gate profile chooses which tutorials to run.

Common choices:

```text
release       normal first check
full_v1       broader V1 tutorial pass
optional_lm3  optional tutorials that need extra assets
```

Manifest gate labels you may see include:

```text
v1_smoke
v1_release
v1_extended
v1_showcase_near_solve
v1_slow_demo
optional_lm3
broken_contract_fix_needed
wrapper_script_fix_needed
remove_from_pure_release
```

Blocked/fix-needed labels are for transparency. They are not normal beginner
choices.

Example:

```text
RDP_TUTORIAL_GATE_PROFILE=full_v1
python tutorials/v1/run_all.py
```

## Asset profile

An asset profile says which scoring/data assets are available.

Common default:

```text
lm2_baseline
```

Optional tutorials may require:

```text
lm3_extended
```

## Seed

A seed makes a search repeatable.

If two runs use different seeds, they are different runs.

## Match ratio

A match ratio measures how much recovered text matches the expected result in a
tutorial.

```text
1.000  exact or complete match
0.900  near-solve threshold in some showcase tutorials
```

## Exact solve versus near-solve

An exact solve recovers the expected result.

A near-solve meets a declared acceptance threshold but may not be perfect.

Tutorials should say which one they are.

## Known truth/key use

Some tutorials use known truth for checking, acceptance, or demonstration.

That does not automatically mean the solver was handed the answer. Read the
tutorial notes and manifest carefully.

## Where options are recorded

Tutorial choices are listed in:

```text
tutorials/v1/tutorial_manifest_v1.json
```

Generated output is under:

```text
output/
```
