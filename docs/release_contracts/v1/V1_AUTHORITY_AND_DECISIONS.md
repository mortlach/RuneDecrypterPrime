# RDP V1 authority and resolved decisions

This file is repository-owned contract evidence for final V1 integration.
It records which sources control decisions when documents, implementation and
tests disagree. It does not replace the detailed design and implementation
records referenced below.

## Authority hierarchy

Use the following order for V1 contract decisions:

1. Explicit later owner decisions recorded here control the V1 public API.
2. The accepted AN1 and AN2 closure packs define the closed architecture,
   terminology, public surface and consumer-migration contract.
3. `RDP_CORE_DESIGN_PRINCIPLES.md` governs implementation method; live source
   determines the current concrete owner that must be repaired or migrated.
4. The June D0-D7 handoff, `v1_docs/` and earlier integration evidence provide
   historical runtime and release context where they do not conflict with AN1/AN2.
5. Canonical `docs/` explain the resulting supported behaviour.
6. Tests enforce approved contracts but do not independently redefine them.

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

## AN3 implementation authority

AN3 implementation begins from:

- repository: `mortlach/RuneDecrypterPrime`
- source branch: `prelease/v1.0.0._h`
- accepted base commit: `452228e7f4b8d4b477498c14fdbc090de79749a8`
- implementation branch: `an3/v1-api-implementation`

Accepted review evidence:

- AN1 closure pack: `rdp_an1_existing_fixture_reuse_closure_20260828T165843Z.zip`
- AN1 pack SHA-256: `29e72c0b2af0bc0c35634c34b72077c88d89dd590b1d521688abcab17b21bfa7`
- AN2 closure pack: `rdp_an2_whole_file_semantics_correction_20260829T022229Z.zip`
- AN2 pack SHA-256: `aeadd8b0081a97290321a773a966bf7677901ac9840496b9218d966d68d54726`
- AN3-P plan: `rdp_an3_p_implementation_plan_20260829T025512Z.zip`
- AN3-P plan SHA-256: `d5cbed6bd66731209c54d1c388b427f5f954e6c7d40b254743f4c600d11b5ce7`
- composite AN1: **PASS**
- composite AN2: **PASS**
- AN3-P: **READY** by explicit owner approval

The approved AN3/AN4 boundary makes `src/rdp/api` definition-owning during the
atomic AN3.6 public-package and consumer cutover. AN3.6 replaces the wildcard
`src/rdp/__init__.py`, migrates public consumers to `from rdp import api`, and
migrates internal consumers to exact owning modules. It must leave no forwarding
package, compatibility shim or duplicate public implementation.

AN4 retains deeper physical organisation of engine packages, including ciphers,
solvers, scoring, key operations, telemetry, data and native-extension ownership.
AN3 must not perform that reorganisation.

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
