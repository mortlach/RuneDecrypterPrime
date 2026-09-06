# Build and packaging notes

This page is for maintainers checking wheels or native-extension packaging.
Most users should start with [installation](installation.md).

## Manual wheel proof

The wheel workflow is:

```text
.github/workflows/rdp_v1_wheel_ci.yml
```

It is a manual, non-authoritative packaging proof. It builds CPython 3.11
wheels on:

```text
windows-latest
ubuntu-latest
```

The installed-wheel test imports:

```text
rdp
rdp.scoring.language_model._fastlm
rdp.scoring.hamming._hamming
rdp.scoring.span_hamming._span_hamming_fast
```

That proves the built wheel can import the package and the native modules on
those CI platforms. It does not prove the full language-asset profile or replace
the manual V1 full proof.

## Native source packaging

Native C++ sources are included for source-distribution based wheel builds by:

```text
MANIFEST.in
```

The important source areas are:

```text
src/rdp/scoring/language_model/
src/rdp/scoring/hamming/
src/rdp/scoring/span_hamming/
```

Do not move native sources without checking `setup.py`, `MANIFEST.in` and the
install-surface tests together.

## Wheel artefacts

Successful wheel CI uploads:

```text
rdp-v1-wheelhouse-windows-latest
rdp-v1-wheelhouse-ubuntu-latest
```

It also uploads the corresponding wheel-build logs.

## Local development

For normal source development, use:

```text
python install.py
```

Use the wheel workflow when the question is specifically packaging. Local wheel
results depend on the available compiler toolchain and Python layout, so they
are useful diagnostics rather than a substitute for the CI packaging proof.
