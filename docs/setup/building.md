# Build and packaging notes

This page is for maintainers who need to check wheels or native extension
packaging.

Most users should start with [`installation.md`](installation.md).

## What the wheel gate proves

The wheel workflow is:

```text
.github/workflows/rdp_v1_wheel_ci.yml
```

It builds CPython 3.11 wheels on:

```text
windows-latest
ubuntu-latest
```

The wheel test imports:

```text
rdp
rdp.scoring.language_model._fastlm
rdp.scoring.hamming._hamming
rdp.scoring.span_hamming._span_hamming_fast
```

That proves the installed wheel can import the package and the required native
modules.

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

Do not move native source files without updating `setup.py`, `MANIFEST.in`, and
the install-surface tests.

## Wheel artifacts

Successful wheel CI uploads:

```text
rdp-v1-wheelhouse-windows-latest
rdp-v1-wheelhouse-ubuntu-latest
```

It also uploads wheel build logs:

```text
rdp-v1-wheel-build-log-windows-latest
rdp-v1-wheel-build-log-ubuntu-latest
```

## Local build notes

For normal development:

```text
python install.py
```

For manual packaging/debugging, use the workflow as the authority. Local wheel
builds can differ depending on installed compiler tools and Python layout.
