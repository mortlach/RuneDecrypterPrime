# Contracts overview

Status: expert user guide

A contract is a promise that users, tests, tutorials, or GUI tools can rely on.

This page describes user-facing contracts without exposing implementation-history
notes.

## Contract types

| Contract | User-facing promise |
| --- | --- |
| Tutorial manifest | selected tutorials, gates, asset needs, and acceptance rules are explicit |
| Input/source | source text identity is separate from solve recipe |
| Config/options | user choices are explicit and repeatable |
| Solver | seed, budget, and stop reason are visible |
| Scorer | ranking and report-only diagnostics are not confused |
| Output | generated evidence is written under `output/` |
| Report | result explains what happened |
| Oracle/truth | known answers or stop scores are visible when used |
| GUI surface | front-ends should read structured data, not scrape console text |

## Tutorial manifest contract

The manifest lives at:

```text
tutorials/v1/tutorial_manifest_v1.json
```

It should tell users and tools:

```text
tutorial id/name
script path
gate labels
asset profile requirement
acceptance kind
match ratio or threshold
whether known truth/key is used
whether tutorial is active, optional, or blocked
```

## Stop reason contract

A run should make clear why it ended.

Examples:

```text
success
budget reached
blocked before run
error
known/test route
```

A user or GUI should not need to infer this from console text.

## Scorer diagnostics contract

Scorer diagnostics should distinguish:

```text
requested
effective
blocked
report-only
ranking-affecting
```

Report-only diagnostics are display evidence, not ranking changes.
