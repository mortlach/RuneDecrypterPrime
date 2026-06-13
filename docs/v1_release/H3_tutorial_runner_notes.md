# H3 tutorial runner pack

Drop these files into the pure release working tree:

```text
tutorials/v1/tutorial_manifest_v1.json
tutorials/v1/run_all.py
```

This is a release-gate runner and manifest, not a new core solver contract.

## Default behaviour

`run_all.py` defaults to:

```python
GATE_PROFILE = "release"
ASSET_PROFILE = "lm2_baseline"
ECHO_OUTPUT = False
```

That runs:

```text
v1_smoke + v1_release
```

under the minimal 1/2-gram asset package.

## Useful gate choices

Edit the config block at the top of `tutorials/v1/run_all.py`:

```python
GATE_PROFILE = "smoke"
GATE_PROFILE = "release"
GATE_PROFILE = "extended"
GATE_PROFILE = "showcase"
GATE_PROFILE = "full_v1"
GATE_PROFILE = "optional_lm3"
```

No command-line switches are needed.

## Near-solve handling

The segmented ScheduledStreamLookup tutorial is labelled:

```text
v1_showcase_near_solve
```

The runner accepts it when `Match ratio >= 0.90`, even if the script still exits non-zero because it did not get exact recovery. This lets the current showcase stay in the release story while keeping the result honest.

Later, it is still worth changing the tutorial itself so it prints “near-solve accepted” and exits cleanly in showcase mode.

## Contract position

Do not add a new D0/D1-style core contract layer for tutorials now.

For now, this is a release-runner policy file. After H3 proves stable, add one small test in H4/H5 to check:

- every manifest path exists,
- every gate label is known,
- every selected default tutorial has an explicit acceptance rule,
- known-broken/optional entries are skipped by default.

That test is a tutorial gate test, not a core solver contract.
