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

## AN3 closure

AN3 is **PASS and closed** at the accepted local and remote commit:

```text
f7af2d2d70ae3aab0965b914024a35df2225fb2f
```

The two disclosed deterministic robustness REVIEW trials are accepted as
non-blocking qualification-recipe limitations, not API or runtime defects:

- `mono_ga.19`, seed `1799567883`, match ratio
  `0.33221476510067116`;
- `generic_map_multiply_beam.12`, seed `65126706`, match ratio
  `0.2558922558922559`.

Their future recipe refinement is separate from AN4. Beginner tutorial tiering
is likewise deferred to GitHub issue #4 and is not AN4 work.

## AN4 implementation authority

AN4-P is **READY and closed**. AN4 implementation is authorised from the exact
accepted AN3 commit above. The approved planning evidence is:

- pack: `AN4_P_REVIEW_PACK_20260901T151832Z_f7af2d2d.zip`;
- pack SHA-256:
  `12c1c780e533eaaacb971c31f4c1cf1dd1480e62793599171c8121bf6956f72f`;
- module move manifest: `an4_module_move_manifest.csv`;
- module move manifest SHA-256:
  `ebb66241432e07f0ed8d3c236e89c94f369463d1e83a2adea68dd4d74edc8c7b`;
- manifest identity: 50 reviewed rows accounting for all 234 tracked files
  under the old engine package.

`AN4_IMPLEMENTATION_PLAN.md`, the module-move manifest, dependency/consumer
matrix, native/asset/packaging matrix, test-gate matrix,
active/historical-documentation matrix, and risks/decisions record in that pack
are the implementation authority. The pack remains external review evidence;
it is not copied into the repository.

The reviewed source baseline is:

- `src/rune_decrypter_prime`: 234 tracked files, comprising 191 Python files
  and 43 other tracked files;
- `src/rdp`: 30 tracked files, comprising 27 Python files and 3 other tracked
  files;
- accepted public surface: exactly 141 paths across the accepted root and four
  subnamespaces, as snapshotted by
  `v1_docs/reference/public_api_allowlist.md` at canonical CRLF-rendered SHA-256
  `13ab2964ddc40706b0be4b01dac496e6d30005ba98a8117ae1c43bfac19c219a`;
- 69 public objects have accepted physical implementation-owner
  (`__module__`) changes during the package movement.

AN4 must preserve all 141 public paths, signatures, enum values, JSON and replay
values, equality and hashing behaviour. The accepted 69 implementation-owner
changes do not authorise public-path or schema changes. Old prerelease Python
pickle module names are not supported and receive no compatibility shim.

The final installed import namespace is only:

```text
rdp
```

Its implementation domains are `rdp.api`, `rdp.backends`, `rdp.core`,
`rdp.ciphers`, `rdp.keyops`, `rdp.solvers`, `rdp.scoring`, `rdp.telemetry`,
`rdp.data` and `rdp.io`. The distribution name remains
`rune-decrypter-prime`. There must be no installed `rune_decrypter_prime`
package, `rdp.utils`, old-name shim, forwarding module, compatibility package,
duplicate implementation owner or public API expansion.

Implementation proceeds only through the reviewed stages:

1. AN4.0 - authority and baseline;
2. AN4.1 - leaf ownership;
3. AN4.2 - core configuration and problem materialisation;
4. AN4.3 - ciphers and key operations;
5. AN4.4 - scoring and native extensions;
6. AN4.5 - solvers, engine and telemetry;
7. AN4.6 - utility, fixture and support closure;
8. AN4.7 - final consumer and package cutover;
9. AN4.8 - installation and complete validation.

Each stage must retain one real owner per implementation, migrate its callers
and focused tests together, and remain reviewable and green. Package movement
must not change algorithms or scientific behaviour. No old-name forwarding or
duplicate ownership may be used to keep an intermediate stage working.

## AN4 closure

AN4 package organisation is **PASS and complete** at the accepted implementation
commit:

```text
f30c5d09080429f64a8a7e982712a5c339c091a2
```

The final installed project namespace is solely `rdp`. The old
`src/rune_decrypter_prime` tree, compatibility packages, forwarding packages and
duplicate implementation owners are absent. The public contract remains exactly
141 paths with 32 root API exports, and its accepted canonical CRLF-rendered
snapshot SHA-256 remains:

```text
13ab2964ddc40706b0be4b01dac496e6d30005ba98a8117ae1c43bfac19c219a
```

Local ordinary and full-assets suites, active tutorial and solved-workbook
validation, strict public typing, fresh wheel and sdist construction, and
isolated installed-package validation passed. The final installer correction
verifies the canonical `import rdp` route.

The final cross-platform GitHub evidence is:

- Windows and Ubuntu push gate:
  `https://github.com/mortlach/RuneDecrypterPrime/actions/runs/33833945061`;
- Windows and Linux native-wheel proof:
  `https://github.com/mortlach/RuneDecrypterPrime/actions/runs/33833958654`.

These successful replacement runs supersede the earlier installer-gate failures
and are the final AN4 GitHub evidence.

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
