# Installation

Status: user guide

This page is the simple install path.

All commands are run from the repository root.

## Requirements

```text
Python 3.11+
```

A normal compiler/build toolchain may be needed if native extensions are built
locally.

## Simple install

```text
python install.py
```

On Windows you can also use:

```text
install.bat
```

The installer checks Python, installs RDP, checks required assets/imports, and
runs a compact smoke check.

Installer logs are written under:

```text
output/install_logs/
```

## Run tutorials after install

```text
python tutorials/v1/run_all.py
```

Success means:

```text
failed   : 0
```

## Show tutorial output

The tutorial runner normally keeps output compact. To echo full tutorial output:

```text
RDP_TUTORIAL_ECHO_OUTPUT=1
python tutorials/v1/run_all.py
```

## Longer local proof

For a fuller V1 tutorial pass:

```text
RDP_TUTORIAL_GATE_PROFILE=full_v1
python tutorials/v1/run_all.py
```

## Next pages

```text
docs/guides/quickstart.md
docs/guides/first_real_solve.md
docs/guides/troubleshooting.md
```
