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
python tutorials/v1/run_all.py
```

The runner uses the settings at the top of:

```text
tutorials/v1/run_all.py
```

Default V1 settings:

```text
GATE_PROFILE = "release"
ASSET_PROFILE = "lm2_baseline"
ECHO_OUTPUT = False
```

## 3. Show full tutorial output

For a user-facing run where you want to see each tutorial's full output, edit:

```text
tutorials/v1/run_all.py
```

and set:

```text
ECHO_OUTPUT = True
```

Then run:

```text
python tutorials/v1/run_all.py
```

## 4. What success looks like

The runner prints a summary similar to:

```text
Summary
gate_profile       : release
asset_profile      : lm2_baseline
selected           : ...
run                : ...
passed             : ...
near_solve_accepted: ...
failed             : 0
skipped            : ...
```

The important line is:

```text
Selected tutorial gate completed successfully.
```

## 5. Run the full expert tests

After install:

```text
python -m pytest -q -p no:cacheprovider
```

That is the full local pytest gate. It is slower than the tutorial runner.
