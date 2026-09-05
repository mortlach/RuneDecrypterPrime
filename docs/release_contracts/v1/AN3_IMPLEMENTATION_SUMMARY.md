# AN3 V1 public API implementation summary

Status: **READY FOR EXTERNAL REVIEW**

AN3 implements the accepted AN1/AN2 V1 public-interface contract. It does not
start the deeper AN4 engine-package reorganisation. The review-pack manifest is
the authority for the exact review-candidate Git head and archive hash.

## Authority and baseline

- Repository: `mortlach/RuneDecrypterPrime`
- Implementation branch: `an3/v1-api-implementation`
- Accepted base: `452228e7f4b8d4b477498c14fdbc090de79749a8`
- Runtime-validation head: `a44a2c99e9b734b5b2e6b5362dbf50340202cdcb`
- Accepted AN1 disposition: PASS
- Accepted AN2 disposition: PASS
- Accepted AN3-P disposition: READY

The implementation comprises 14 commits after the accepted base through the
runtime-validation head. The base-to-head change spans 700 tracked paths with
22,952 insertions and 49,575 deletions. The high file count includes the
approved complete consumer migration, test migration, documentation migration,
AN3.8 formatting-churn restoration and deletion of the 29-file
`tutorials/old/` tree.

## Stage delivery

| Stage | Commit | Delivered responsibility |
| --- | --- | --- |
| AN3.0 | `08f8454` | Core design principles, repository guidance and implementation authority |
| AN3.1 | `7d8d5fe` | Typed requests, results, aliases, enums and error contracts |
| AN3.2 | `28cb35b` | Typed cipher/key/solver materialisation through existing runtime owners |
| AN3.3 | `e7a004d` | Canonical `api.run` execution and unconditional `RunResult` |
| AN3.4 | `571127a` | Pure typed `api.encrypt` and `api.decrypt` known-key operations |
| AN3.5 | `a987739` | Experimental map surface and exact support boundaries |
| AN3.6 | `bf6abab` | Atomic definition-owning `rdp.api` and retained-consumer cutover |
| AN3.7 | `06e0f2e` | Retired compatibility removal and approved old-tutorial deletion |
| AN3.8 | `df9aa91` | Complete implementation validation and cleanup |
| Review correction | `bc98913` | Removal of validation-stage formatting churn |
| Documentation correction | `c36f045` | Completion of active V1 API documentation migration |
| Runtime qualification | `8452a6c` | Runtime and tutorial qualification defect corrections |
| P7/C7 evidence | `192a310` | Qualified staged periodic-columnar workflow and tutorial |
| Evidence resume | `a44a2c9` | Git-revision-scoped robustness evidence and safe resume |

## Resulting public boundary

Normal users import the definition-owning package with:

```python
from rdp import api
```

The accepted surface contains exactly:

- 32 root exports;
- 65 `api.advanced` paths;
- 22 `api.display` paths;
- 18 `api.liber_primus` paths;
- four `api.experimental` paths;
- 141 supported paths in total.

The canonical operations are `api.run`, `api.encrypt` and `api.decrypt`.
Requests are typed and immutable, successful execution always returns
`RunResult`, and public concrete keys are semantic `tuple[int, ...]` values.

There is no public `RunAPI`, `solve`, `cipher_instance`, `preview`, generic
transform operation, runtime cipher instance, `api._internal`, forwarding
package, compatibility shim or duplicate public implementation. Internal
consumers import exact implementation owners. Active tutorials use public
typed APIs; custom-map tutorials use `api.experimental`.

## Consumer and removal closure

The atomic migration covers retained source, tests, tutorials, solved-LP
workflows, cipher-development work, robustness campaigns, release tooling and
active documentation. Generated AN2 previews were treated as review inputs,
not blindly applied patches. Configuration dictionaries in ordinary examples
were replaced by typed specifications, runtime-object dataflow was preserved,
and public encryption/decryption keys are normalised before crossing the API.

The complete approved 29-file `tutorials/old/` tree was deleted. Git history
preserves it; no fragments, compatibility copies or forwarding replacements
remain.

## Recorded complete validation

The owner-run integrated proof `20260901_070234` completed all 38 planned
stages in approximately 3 hours 4 minutes:

| Gate | Evidence |
| --- | --- |
| Complete Pytest | 1,773 passed; seven expected CUDA skips |
| Canonical V1 tutorials | 26/26 passed their declared acceptance rules |
| Qualification-derived P7/C7 tutorial | Exact plaintext recovery; match ratio 1.000 |
| Decomposed P7/C7 qualification | PASS; exact plaintext recovery; one score-selected warm start |
| Solved Liber Primus workbook | 9/9 solved; every match ratio 1.000 |
| Robustness trials | 159 PASS, two REVIEW, zero FAIL across 161 completed trials |

The overall integrated-run status is FAIL because the robustness family gate is
deliberately strict: every trial must be PASS. Two deterministic recipe cases
were REVIEW:

- `mono_ga.19`, seed `1799567883`, match ratio `0.33221476510067116`;
- `generic_map_multiply_beam.12`, seed `65126706`, match ratio
  `0.2558922558922559`.

Both reproduce the exact seeds, selected attempts, solver scores and match
ratios in earlier evidence. They are established qualification-recipe
limitations, not AN3 API regressions, crashes, provenance errors or incomplete
runs. Truth was not used for attempt selection. The owner has accepted their
disclosure for AN3 external review; future robustness-recipe refinement remains
separate work.

## Exact-solve qualification

The canonical `periodic_columnar_decomposed_v2` qualification uses a P7/C7
decomposed search: 384 candidate heads, one score-selected head, 5,040 tails,
one retained complete warm start, and one integrated Kaeding restart. The
search-visible path has no oracle or target score. Reference plaintext is
consulted only for terminal qualification after `api.run` returns.

The recorded full-run qualification recovered all plaintext symbols exactly in
about 36 minutes. The corresponding public tutorial independently recovered
the same full plaintext exactly in about 36 minutes using the typed V1 API.

## AN3/AN4 boundary

AN3 makes `src/rdp/api` definition-owning and completes the public and consumer
cutover. It intentionally leaves the deeper physical ownership of ciphers,
solvers, scoring, key operations, telemetry, data and native extensions for
AN4. No AN4 engine-package restructuring is included here.

## Disposition

The AN3 implementation is complete and ready for focused external review. AN4
must not begin until the owner accepts that review. Reviewers should use
this implementation summary as the entry point and the generated pack
manifest/checksums as the exact evidence identity.
