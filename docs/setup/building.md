# Build and packaging notes

[Installation](installation.md) is the normal user route.

This page covers the package build itself.

## Wheel check

The wheel workflow builds a CPython 3.11 wheel on Windows and Ubuntu, installs
it, and checks the package and compiled scoring modules.

That is a packaging check rather than a full solver or asset qualification run.

See [Install validation](install_validation.md) for the distinction between
routine, full and qualification checks.

## Compiled scoring code

The compiled scoring sources live under:

```text
src/rdp/scoring/language_model/
src/rdp/scoring/hamming/
src/rdp/scoring/span_hamming/
```

If one of these areas moves, the package configuration needs the corresponding
change.

Changes to the scoring behaviour itself should also be reflected in
[Scoring](../guides/scoring.md) and the
[Scoring parameter reference](../reference/parameters/scoring.md).

## Source development

For ordinary development from a checkout:

```text
python install.py
```

The wheel workflow is for changes where the package build itself is under test.

For the wider implementation route, see
[Development](../development/README.md) and
[Contributing](../../CONTRIBUTING.md).
