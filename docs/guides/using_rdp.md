# Using RDP

Status: user guide

This page explains the normal user workflow.

## 1. Install

```text
python install.py
```

On Windows:

```text
install.bat
```

## 2. Run the default tutorials

```text
python tutorials/v1/run_all.py
```

A successful run ends with:

```text
failed   : 0
```

## 3. Read one solve

Read:

```text
docs/guides/first_real_solve.md
```

That page explains one complete run: what is known, what is searched, what the
solver finds, and what success looks like.

## 4. Inspect output

Generated output is under:

```text
output/
```

For tutorial runs, start with:

```text
output/tutorials/
```

Read:

```text
docs/guides/outputs.md
```

## 5. Run a fuller tutorial gate

For a broader local check:

```text
RDP_TUTORIAL_GATE_PROFILE=full_v1
python tutorials/v1/run_all.py
```

This takes longer than the default release tutorial gate.

## 6. Show full tutorial output

For demos or manual review:

```text
RDP_TUTORIAL_ECHO_OUTPUT=1
python tutorials/v1/run_all.py
```

## 7. Fix common problems

Read:

```text
docs/guides/troubleshooting.md
```

## 8. Work with Liber Primus labels

Read:

```text
docs/guides/liber_primus_solved_sources.md
```

A source label identifies the text fragment being solved. It is not the same
thing as a solver recipe or known key.
