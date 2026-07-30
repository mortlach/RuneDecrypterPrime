# RDP V1 authority and resolved decisions

This file is repository-owned contract evidence for final V1 integration.
It records which sources control decisions when documents, implementation and
tests disagree. It does not replace the detailed design and implementation
records referenced below.

## Authority hierarchy

Use the following order for V1 contract decisions:

1. The June 10 D0-D7 unified hardening handoff is the primary V1 design authority.
2. `v1_docs/` and the hardened pre-WP7 implementation provide detailed intended shape.
3. Explicit approved WP6, WP7 and final-integration additions extend that baseline.
4. Canonical `docs/` explain the resulting supported behaviour.
5. Tests enforce the approved contracts, but do not automatically redefine them.

Obvious drift is corrected against this hierarchy. A new product decision is
required only for a genuine conflict that has no controlling authority or
precedent.

## Final-integration baseline

Final integration began from:

- repository: `mortlach/RuneDecrypterPrime`
- reviewed source branch: `prelease/v1.0.0_o2p`
- final-integration working branch: `prelease/v1.0.0._h`
- reviewed GitHub commit: `a7a8439c8c3a6bc0b9110577ba93630857e08156`
- reviewed source ZIP SHA-256: `3af42108db33a0e7b20062d1c1f2f06f276e043bb119bdd6576f9681c7eb1309`

The ZIP is a static review snapshot. The GitHub branch and the active local
checkout are the implementation sources. Relevant local tracked, untracked and
ignored differences must be recorded and reconciled before destructive work.
Local-only assets, notes and results must be backed up once outside the checkout.

## Resolved decisions

The machine-readable record is `v1_resolved_decisions.csv`. Its decisions are
approved implementation constraints, not open review questions.

In particular:

- silent loss of supported inputs or configuration is a defect;
- only `tutorials/v1/` is the V1 tutorial surface;
- the staged two-period solver is a normal RDP feature and reuses the V1 interruptor model;
- accepted LM/scorer design is not weakened to fit CI-light;
- `v1_docs/` is selectively merged into one canonical `docs/` tree;
- release artefacts remain wheel, sdist, full V1 assets and curated Pack 09 evidence;
- Python 3.11+ is required, with formal release proof on Windows and Ubuntu/Linux;
- the risk-based test-system review is release work;
- `main` holds releases and `develop` becomes the post-V1 integration branch.

## Change rule

A resolved decision may be changed only by an explicit later authority record.
When that happens, update this file, `v1_resolved_decisions.csv`, affected
contracts, implementation, tests and release notes in the same reviewed change.
