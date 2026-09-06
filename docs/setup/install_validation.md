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

The normal V1 CI runs on Windows and Ubuntu with Python 3.11.

It uses the smaller bundled language assets and runs the ordinary test and
tutorial route.

This is the routine check for supported installation and normal public
behaviour.

## Full release check

The full release workflow checks the complete V1 asset set and the tests and
examples that depend on it.

It is separate from the normal fast path because it answers a larger release
question and costs more to run.

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

Wheel building has its own packaging check. It verifies that the package and
compiled modules build and import correctly on the supported CI systems.

That proves packaging, not solver quality.

See [Build and packaging notes](building.md).
