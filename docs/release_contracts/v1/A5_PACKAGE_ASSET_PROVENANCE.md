# A5 package, asset and provenance closure

A5 hardens the V1 release boundary; it does not introduce a second release framework.

## Implemented software contracts

- Source checkout asset lookup prefers the checkout `assets/` root.
- The wheel stages **only** the exact source-bundled CI-light runtime assets named by `assets_manifest_ci_light_v1.json`, plus the LM `index.json` metadata required to load them.
- Wheel/sdist asset staging is allowlist-based. A developer's locally downloaded full LM1-LM4 tree is never swept into an artifact by a recursive asset glob.
- Installed-wheel lookup resolves those staged package assets only; it does not search CWD/home/env locations.
- Complete external LM1-LM4 data remains explicit through the existing `model_root` contract.
- `ciphers.dev`, `keyops.dev`, and `data.liber_primus.old` remain repository development/history material and are excluded from the distributable Python package/sdist.
- Production KeyOps registration is strict and deterministic; duplicate registration is an error unless replacement is explicit.
- The development `MatrixKey` must not register itself as the production MATRIX family.
- Source ZIP members use frozen metadata so identical source bytes create identical archive bytes.
- Release qualification is claimed for Python 3.11 on Windows and Ubuntu/Linux; metadata may permit newer Python without claiming it has been qualified.

## F-008 bounded source/data review

The 2026-08-22 review covered the principal material data families that RDP actually redistributes. Detailed rows are recorded in `A5_PROVENANCE_REVIEW_TEMPLATE.csv`.

### Review conclusion

- RDP software is distributed under `LICENSE_MIT.txt`.
- The Alice's Adventures in Wonderland test passage is from Lewis Carroll's 1865 public-domain work and is transformed into rune/numeric fixtures.
- A5 does not vendor the source of its Python or build dependencies.
- No concrete copyright, licence, attribution or redistribution blocker was identified for the reviewed data families.

### Runtime language-model and normalisation assets

RDP's full runtime language-model and normalisation assets are distributed through the separately managed RDP V1 asset release. These include the character models, WLI 1-4 gram assets and associated normalisation data. The core repository and wheel carry only the explicitly allowlisted CI-light LM1/LM2 subset needed by the normal CI-light runtime contract.

A5 verifies that package/asset release boundary. Exhaustive reconstruction of historical training-data provenance is outside the V1 release scope.

### Other reviewed source/data families

- The `raw1grams`, dictionary-policy variants and short rune wordlists are RDP lexical/frequency and curated fixture assets. A5 excludes the repository-level raw asset trees from the wheel and sdist.
- The Liber Primus material is public community puzzle-research transcription data with RDP punctuation and adapter transformations. The reviewed upstream reference is <https://github.com/rtkd/iddqd/tree/master/liber-primus__transcription--master>.

## Closure status

F-008 is **closed for A5 publication**. The bounded review identified no concrete redistribution blocker. Future provenance reconstruction or broader data-governance work may be recorded separately, but is not a V1 A5 release gate.

Do not copy secrets, private URLs, credentials, or restricted source material into the public repository merely to prove provenance. This review records engineering release evidence; it is not a legal opinion.
