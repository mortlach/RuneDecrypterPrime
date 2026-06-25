# Adding A Tutorial

Status: staged V1 draft

V1 tutorials should be easy to run, easy to read, and honest about what they
prove.

## Pick The Tutorial Type

Before writing code, decide what the tutorial is:

| Type | Use when |
| --- | --- |
| first-run lesson | the reader is learning the basic API shape |
| cipher lesson | the reader is learning one cipher family |
| real solve | the solver searches and recovers a result |
| LP example | the tutorial uses a Liber Primus source label or workbook |
| partial-recovery tutorial | exact recovery is not required and the threshold is explicit |
| advanced demo | useful, but not part of the beginner release gate |

## File Shape

Pretty-print tutorials live under:

```text
tutorials/v1/
```

The target V1 shape is that all working tutorials live in this folder. A
tutorial can be beginner, release, extended, optional, partial recovery, or advanced,
but it should still have a clear status and a direct file to run.

Use a clear filename ending in:

```text
.py
```

The tutorial should run directly:

```text
python tutorials/v1/Tutorial_Name.py
```

It should not require a separate config file for normal behavior.

## Output Shape

A good V1 tutorial printout should show:

- lesson title or problem
- plaintext/ciphertext preview when useful
- `encoding_dir`
- cipher and solver
- score or match ratio
- stop reason
- truth/oracle policy
- recovered key or key preview
- warnings

Use the standard RDP display layer where possible. It keeps the output more
consistent than hand-built print blocks.

## Runner Registration

The current pretty-print release list lives in:

```text
tutorials/v1/run_tutorials.py
```

Add the tutorial to `TUTORIALS` only when it is ready for the pretty-print
review gate.

Each entry needs:

- file name
- minimum match ratio

Full output mode shares the same list, so adding one entry affects both the
compact gate and the full printout review.

## Metadata Registration

Every working tutorial should also have metadata.

Metadata should answer:

- what gate or lane it belongs to
- what asset profile it needs
- whether exact recovery is required
- the minimum match ratio, if any
- whether it uses truth/oracle data
- whether it supplies a true key to the solver
- whether it is active, optional, partial recovery, slow, or blocked
- short notes that explain why it is classified that way

Today, that metadata is partly in `tutorial_manifest_v1.json` and partly in the
pretty-print runner constants. The target is to align those so a new tutorial
does not require several manual list updates that can drift.

## Evidence Fields

If the tutorial uses known truth, an oracle stop score, a reference plaintext, a
known key, or LP evidence, make that visible in the report.

For tutorial reports, the compact schema is:

```text
rdp_tutorial_run_report.v1
```

For standard display summaries, include tutorial metadata and LP evidence where
they apply.

## Match Thresholds

Use `1.000` for exact recovery.

Use a lower threshold only when the tutorial is intentionally a partial recovery or
stochastic example. If exact recovery is not required, the tutorial output and
docs must say so.

## Tests

At minimum, update or add focused tests for:

- runner selection or manifest policy
- report fields that the tutorial depends on
- display output if new sections are introduced
- encoding direction if the tutorial touches rune display
- docs/list alignment if the tutorial is part of a public runner

For the final human-facing review, run:

```text
python tutorials/v1/run_tutorials.py
```

## Do Not Add

Avoid:

- hidden setup outside the tutorial file
- shell-controlled tutorial behavior
- generated logs committed as examples
- absolute local paths
- truth data that affects ranking without being reported
- thresholds that are lowered without explanation

The goal is a tutorial a curious reader can run and then understand.
