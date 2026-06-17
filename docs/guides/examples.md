# Beginner examples

Status: user guide

This page explains RDP using plain examples.

## The lock analogy

```text
ciphertext   the locked message
cipher       the kind of lock
key          the thing being searched
solver       the search strategy
scorer       the judge that says whether text looks good
report       the record of what happened
```

## Example: run tutorials

```text
python tutorials/v1/run_all.py
```

Look for:

```text
failed   : 0
```

## Example: exact solve

An exact solve means the recovered result matches the expected result.

In a tutorial, this often appears as:

```text
match_ratio = 1.000
```

## Example: near-solve

A near-solve is good enough for a declared threshold, but not necessarily exact.

Example:

```text
match_ratio >= 0.900
```

The tutorial should say when this is the expected success condition.

## Example: source label

A source label is a name for text.

```text
welcome_pilgrim
```

That tells RDP which text fragment to load. It does not secretly define the
solver or key.

Read:

```text
docs/guides/liber_primus_solved_sources.md
```
