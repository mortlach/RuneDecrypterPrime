# Quickstart

This is the shortest path after installation.

All paths below are relative to the repository root.

## 1. Install

```text
python install.py
```

On Windows, `install.bat` is also available.

See [`../setup/installation.md`](../setup/installation.md) for the full install
notes.

## 2. Run the release tutorials

```text
python tutorials/v1/run_pretty_print_release.py
```

The runner prints compact status lines and writes full per-tutorial logs under
`output/tutorial_pretty_print_logs/`.

The tutorial list and thresholds live near the top of
`tutorials/v1/run_pretty_print_release.py`. There are no RDP tutorial
environment variables for the normal V1 tutorial path.

To review the complete printouts in the console, run:

```text
python tutorials/v1/run_pretty_print_output_review.py
```

## 3. What success looks like

The runner prints a summary similar to:

```text
Pretty-print summary
selected=...
run=...
passed=...
failed=0
```

The important part is:

```text
failed=0
```

## 4. Run the full expert tests

After install:

```text
python -m pytest -q -p no:cacheprovider
```

That is the full local pytest gate. It is slower than the tutorial runner.
