# AN3 external review request

## Requested disposition

Review the AN3 V1 public API implementation and return one of:

- **PASS** — AN3 may close and AN4 may begin separately;
- **REVIEW** — identify a concrete AN3 defect with file and contract evidence;
- **BLOCKED** — identify a contradiction that prevents review or implementation.

Do not reopen accepted AN1/AN2 naming or architecture decisions, propose
compatibility shims for unreleased interfaces, or begin the AN4 engine-package
reorganisation.

## Review authority

- Accepted implementation base:
  `452228e7f4b8d4b477498c14fdbc090de79749a8`
- Branch: `an3/v1-api-implementation`
- Accepted AN1 closure: PASS
- Accepted AN2 closure: PASS
- Accepted AN3-P plan: READY
- Runtime-validation head:
  `a44a2c99e9b734b5b2e6b5362dbf50340202cdcb`
- Exact review head: recorded in `REVIEW_PACK_MANIFEST.json`

Read first:

1. `docs/release_contracts/v1/RDP_CORE_DESIGN_PRINCIPLES.md`;
2. `docs/release_contracts/v1/V1_AUTHORITY_AND_DECISIONS.md`;
3. `docs/release_contracts/v1/AN3_IMPLEMENTATION_SUMMARY.md`;
4. `v1_docs/reference/public_api_allowlist.md`.

## Focused review questions

1. Does `rdp.api` own exactly the accepted 32-root/141-path public surface?
2. Are `run`, `encrypt` and `decrypt` typed, truthful and backed by existing
   runtime owners without a parallel execution model?
3. Are request/result storage, equality, replay and configuration reporting
   mechanically implementable and internally coherent?
4. Are retained consumers migrated to public typed APIs or exact internal
   owners, with no forwarding layer or obsolete public path?
5. Are the experimental and normal tutorial boundaries respected?
6. Is deletion/removal closure complete, including the 29-file old tutorial
   tree and retired runtime-instance APIs?
7. Does the recorded validation adequately prove AN3 while honestly disclosing
   the two reproducible robustness-recipe REVIEW trials?
8. Does the implementation preserve the approved AN3/AN4 boundary?

## Evidence-pack layout

The external AN3 solve-review archive contains:

- this start document and the implementation summary;
- a standard source-review ZIP generated from a clean detached worktree at the
  exact review head;
- one Git patch per AN3 commit from the accepted base;
- the complete 38-stage integrated-run logs and JSON summary;
- the exact P7/C7 qualification artifacts;
- all current-revision robustness JSONL, provenance and campaign logs;
- SHA-256 checksums and a machine-readable outer manifest.

The pack excludes language-model assets, caches, private local configuration,
generated benchmark corpora and unrelated historical outputs. Asset identity
remains represented by the campaign provenance and repository manifests.

## Known disclosed result

All 38 integrated stages executed. Thirty-six passed. The only non-passing
stages completed scientifically but returned 19 PASS and one REVIEW each:
`mono_ga` and `generic_map_multiply_beam`. They contain zero FAIL-classified
trials and exactly reproduce earlier deterministic evidence. Treat them as
known robustness-recipe limitations unless review identifies evidence that
they result from an AN3 public-interface defect.
