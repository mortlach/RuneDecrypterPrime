# Install validation

Different checks answer different questions.

For normal use:

```text
python install.py
```

Then run the known-key tutorial:

```text
python -m tutorials.v1.getting_started.01_known_key
```

The normal runnable set is:

```text
python tutorials/v1/run_tutorials.py
```

See [Installation](installation.md) for the setup route and
[Tutorials and examples](../tutorials/README.md) for what those programs cover.

## Normal CI

The normal V1 CI runs on Windows and Ubuntu with CPython 3.11, 3.12, 3.13 and 3.14.

It verifies the bundled `ci_light` LM1/LM2 assets and selects pytest with
`-m "not full_assets"`, followed by the release tutorial group. Tests that genuinely
need LM3/LM4 remain marked `full_assets` and run with those assets in full proof.
See [Language-model assets](language_model_assets.md) for the profiles.

This is the routine check for supported installation and normal public
behaviour.

## Full release check

The full release workflow checks the complete V1 asset set and the tests and
examples that depend on it on CPython 3.11. It also requires all eight desktop
wheel builds for CPython 3.11–3.14 and the pinned Pyodide proof to pass.

It is separate from the normal fast path because it answers a larger release
question and costs more to run. Maintainers should follow the
[release validation guidance](../development/README.md#release-validation).

## Qualification runs

Long solver qualification programs measure behaviour over larger campaigns and
can take hours.

They are used when the claim being tested depends on repeated recovery or
behaviour across many cases.

They are not needed to validate a documentation edit or a small code change.

The same distinction appears in
[Cipher development](../development/cipher_development.md) and
[Extending RDP](../guides/extending_rdp.md).

## Wheel check

Wheel building has its own packaging check for each Python/platform pair.
It verifies that the package and compiled modules build, import and perform
the installed public API checks correctly in an isolated environment.

That proves packaging, not solver quality.

See [Build and packaging notes](building.md).
