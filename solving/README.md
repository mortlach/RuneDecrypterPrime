# RDP solving workspace

This folder is for using RDP on real Liber Primus material.

It is deliberately separate from `tutorials/`:

```text
tutorials/ = learn how RDP works
solving/  = apply RDP to real LP sources and record the attempt
```

The first V1 solving path is built around labelled LP sources:

```python
from rune_decrypter_prime.data import liber_primus as lp

entry = lp.resolve_source_label("red_rune.welcome_pilgrim")
recipe = lp.resolve_solve_recipe_label("recipe.welcome_pilgrim.vigenere_interruptors")
```

A source label identifies the LP text fragment only. A recipe identifies the
cipher hypothesis or replay method.

## Folders

```text
solved_lp/   reproducible solved-page replays and real-solve reproductions
attempts/    reproducible attempts against unsolved or diagnostic LP sources
```

## Truth policy

Solving runs must say how truth/reference text is used:

```text
known_key_demo      the answer/key is supplied to demonstrate plumbing
reference_replay    solved text/reference is replayed or checked
real_solve          solver is not given the true key/plaintext; truth is evaluation only
near_solve          partial recovery accepted above a stated threshold
diagnostic_attempt  not expected to solve; tests a hypothesis or route
negative_result     useful failed attempt with a clear setup and result
```

## Boundary policy

LP source entries must resolve through the main transcript. Candidate red-rune
sections or page ranges are useful metadata, but they must not be silently used
as solver input until exact page/line boundaries are verified.
