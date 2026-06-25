# Install RDP

Status: staged V1 draft

This page is the simple install path for Rune Decrypter Prime.

Use the same Python interpreter for every command on this page. If you install
with one Python and run tutorials with another, imports and native extension
checks can fail in confusing ways.

## Requirements

- Python 3.11 or newer
- A local checkout of the RDP repository
- Internet access for package installation, unless dependencies are already
  available locally

## Install

From the repository root:

```text
python install.py
```

The installer checks the package build, installs the project in editable mode,
and verifies the native scoring extension can be imported.

## First Tutorial Check

After install:

```text
python tutorials/v1/run_tutorials.py
```

This runs the staged V1 pretty-print tutorial gate. The console output is short.
Full tutorial logs are written under:

```text
output/tutorial_logs/
```

## If Something Fails

Run these checks with the same Python:

```text
python install.py
python tutorials/v1/run_tutorials.py
```

Then open the newest install log under:

```text
output/install_logs/
```

For tutorial failures, open the matching log under:

```text
output/tutorial_logs/
```

## What This Page Avoids

The beginner install path keeps out:

- special shell setup
- separate tutorial config files
- command-line tutorial control
- editor-specific steps

Those tools can still be useful for experienced developers, but they are not
part of the normal V1 beginner path.
