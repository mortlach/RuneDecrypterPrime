# Component model

Status: expert user guide

This page explains the main RDP components and how they fit together.

## High-level flow

```text
source text
  -> cipher/key model
  -> solver proposes candidate keys
  -> cipher decrypts candidate text
  -> scorer ranks candidate text
  -> report records result
```

## Components

| Component | User meaning | Expert meaning |
| --- | --- | --- |
| Source | the text being solved | raw text, normalised indices, or labelled source reference |
| WLI | word-location hints | optional word position/length data |
| Cipher | the encryption/decryption model | transform plus key/stream interpretation |
| Key model | what is searched | searched key shape and any supplied/generated streams |
| Solver | search strategy | deterministic search loop with seed and budget |
| Scorer | ranking method | scoring backend and optional diagnostics |
| Report | what happened | structured result and metadata |
| Artefact | saved output | files written under `output/` |
| Tutorial manifest | tutorial catalogue | machine-readable tutorial selection and acceptance data |

## Important separation

### Source label versus solve recipe

A source label identifies text.

A solve recipe chooses:

```text
cipher
key shape
solver
seed
scorer
acceptance rule
```

Do not hide solve settings inside source labels.

### Supplied stream versus recovered key

Some ciphers use more than one stream.

Keep these separate:

```text
searched key        recovered by solver
fixed sequence      supplied input
generated stream    deterministic schedule
```

A supplied sequence should not be presented as a recovered key.

### Report-only versus ranking-affecting

Some diagnostics are useful to display but should not affect ranking.

A GUI should display whether a value is:

```text
ranking-affecting
report-only
blocked/unavailable
not requested
```
