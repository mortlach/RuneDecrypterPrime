# Liber Primus solved source labels

Status: user guide

This page explains Liber Primus source labels used by RDP tutorials and examples.

A source label answers:

```text
Which Liber Primus text fragment is this?
```

It does not answer:

```text
Which solver should be used?
Which key is correct?
Which period is correct?
Which score is expected?
```

Those are part of a tutorial or solve recipe, not the source label itself.

## Common labels

Examples of user-facing labels may include:

```text
welcome_pilgrim
koan_during_lesson
an_end
parable
```

A tutorial may use one of these labels to load a known source fragment.

## Why labels matter

Labels make examples easier to read.

Instead of asking users to remember page and line offsets, a tutorial can say:

```text
welcome_pilgrim
```

The label should resolve to the same rune text and word-location information each
time.

## Labels are not recipes

Keep this distinction clear:

```text
source label = what text is being solved
solve recipe = how RDP tries to solve it
```

## Where to see this in use

Start with:

```text
docs/guides/first_real_solve.md
tutorials/v1/
tutorials/v1/tutorial_manifest_v1.json
```

## Troubleshooting labels

If a labelled LP tutorial fails, check:

```text
- the tutorial name
- the tutorial manifest row
- the selected tutorial gate
- the asset profile
- the generated output under output/tutorials/
```

Then read:

```text
docs/guides/troubleshooting.md
```
