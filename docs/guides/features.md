# Feature overview

Status: user guide

This page lists the main RDP features a user can see or choose.

For a deeper expert view, read:

```text
docs/expert/component_model.md
docs/expert/contracts_overview.md
docs/expert/plugin_design.md
```

## Main idea

RDP combines these parts:

```text
source text
cipher model
key or stream model
solver
scorer
report/output
```

A tutorial chooses these parts for you.

## User-facing feature groups

| Feature group | What it means | Where to learn more |
| --- | --- | --- |
| Tutorials | runnable examples that prove RDP works | `docs/guides/tutorial_catalogue.md` |
| Ciphers | the kind of encryption/decryption model | `docs/expert/component_model.md` |
| Key models | what key shape the solver searches | `docs/expert/component_model.md` |
| Solvers | search strategies that try candidate keys | `docs/guides/common_run_options.md` |
| Scorers | judges that rank candidate plaintext | `docs/guides/common_run_options.md` |
| Reports | records of what happened | `docs/guides/outputs.md` |
| LP labels | names for Liber Primus source fragments | `docs/guides/liber_primus_solved_sources.md` |
| GUI/front-end surfaces | stable inputs and outputs for overlays | `docs/expert/gui_frontend_interfaces.md` |

## Tutorial-surface cipher families

The tutorial manifest describes the active tutorial surface. Current families
include examples around:

```text
vigenere
autokey
railfence
vigenere interruptors
columnar transposition
mono substitution
scheduled stream lookup
custom map repeating multiply
periodic columnar
periodic substitution
Liber Primus labelled source examples
crib-drag/API examples
```

Use the tutorial catalogue for the current list:

```text
docs/guides/tutorial_catalogue.md
```

## Common user choices

Common choices users may see:

```text
gate profile
asset profile
cipher family
solver type
seed
match ratio
exact solve versus near-solve
```

Read:

```text
docs/guides/common_run_options.md
```

## Expert feature details

Expert users and GUI developers should read:

```text
docs/expert/README.md
```
