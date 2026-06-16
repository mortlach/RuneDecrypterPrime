# D7 final review-ready note

Branch: `prelease/v1.0.0_d7`

Current status: final closeout review candidate after bounded review-pack evidence fixes and local proof reruns.

Validation status: local final closeout proof was recorded for commit `5e5372fff386378dde3f8dcd0acd8c880c70667d` on branch `prelease/v1.0.0_d7`.

Recorded local proof:

```text
focused review-pack tests: 3 passed
focused D7/tutorial framework tests: 34 passed
compact D7 smoke: 146 passed
broader focused closure gate: 676 passed
full pytest: 1220 passed, 19 skipped
full_v1 tutorial gate: 14 passed, 0 failed
```

GitHub connector status visibility: no combined status checks or workflow runs were visible for the latest checked commit through the connector when this note was written. Treat user-reported logs and regenerated review-pack metadata as the validation source until GitHub status is visible.

## Final D7 position

D7 should now move from hardening/development into final closeout review. The final evidence-tool rerun has been recorded locally for the review target commit.

The branch is not a tiny documentation-only closure branch. It contains real V1 hardening, including:

- enum-domain ownership and normalisation hardening;
- solver report semantic-domain split;
- stop-reason error classification hardening;
- scorer-lane/report-only visibility contracts;
- ScheduledStreamLookup V1 API/wrapper/cipher/tutor-lock contracts;
- tutorial/session report framework foundation;
- tutorial manifest integration and default release-gate promotion for one exact ScheduledStreamLookup real solve;
- review-pack metadata binding to git branch/head/dirty state;
- review-pack direct-root-file scanning so root patch scripts cannot be silently omitted from pack review.

This is acceptable for D7 only because the changes are contract/release hardening, evidence hardening, and tutorial-gate integration, not new solver/cipher/scorer feature expansion.

## Final tutorial-gate evidence

Local `full_v1` tutorial gate result from the final closeout proof:

```text
RDP V1 tutorial runner | gate=full_v1 | asset_profile=lm2_baseline
Selected gates: v1_smoke, v1_release, v1_extended, v1_showcase_near_solve
Selected entries: 14
selected: 14
skipped: 0
run: 14
passed: 14
failed: 0
```

Important ScheduledStreamLookup tutorial results in that run:

```text
Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py: PASS, match=1.000
Tutorial_ScheduledStreamLookup_RealSolve_P13Primes.py: PASS, match=1.000
Tutorial_ScheduledStreamLookup_RealSolve_P13P31Segmented.py: NEAR_SOLVE_ACCEPTED, match=0.901
```

## Final pytest evidence

Local full pytest proof from the final closeout target:

```text
1220 passed, 19 skipped in 355.54s (0:05:55)
```

Known skip classes:

```text
optional LM3/LM4 asset tests skip when those assets are absent from the lm2_baseline profile
optional Hill-wrapper tutorial tests skip because the wrapper is not registered yet
```

Earlier history: the last concrete CI failure before green was:

```text
test_tutorial_runner_uses_ide_defaults_without_environment_override
expected: release
actual: full_v1
```

That failure was fixed by changing the contract to require a valid configured default profile and valid environment overrides, rather than hard-coding `release` as the only acceptable IDE default.

## Review-pack evidence note

A final evidence hardening fix was applied after inspecting the generated review-pack summary: `tools/release_review_pack.py` now writes `git_branch`, `git_commit_sha`, and `git_working_tree_dirty` into both `REVIEW_PACK_MANIFEST.json` and the sidecar summary JSON.

The pack generator now scans all direct root files and records excluded direct-root files in `excluded_entries`, so root one-off patch scripts or archives cannot be silently omitted from pack review.

The final local review pack was regenerated from the review target commit. The generated manifest reports:

```text
git_branch: prelease/v1.0.0_d7
git_commit_sha: 5e5372fff386378dde3f8dcd0acd8c880c70667d
git_working_tree_dirty: false
included_files_count: 692
excluded_entries_count: 480
root_file_selection: all_direct_root_files_filtered_by_review_pack_rules
```

## Review scope

Review D7 for closure against these questions:

1. Does any requested V1 production capability still silently fall back, warn-only, or disappear?
2. Can any report-only/experimental signal affect production ranking?
3. Do tutorial/session helpers remain outside strict runtime modules?
4. Are API/tutorial compatibility surfaces documented and normalised rather than silently broken?
5. Are known-broken tutorials classified honestly and excluded from release/full_v1 gates?
6. Does the tutorial runner select and accept tutorials by manifest policy rather than ad-hoc skips?
7. Does the review evidence overclaim compared with actual tested behaviour?
8. Is the generated review pack bound to the final reviewed commit?
9. Does the generated review pack include or explicitly exclude direct root files?
10. Is the D7 scope now frozen except for reviewer-requested fixes?

## Known non-blockers / future work

These should not block D7 closure:

- optional LM3/LM4 asset tests skip when those assets are absent;
- optional Torch/CUDA tests skip when the environment lacks the required backend;
- `Tutorial_PeriodicColumnar_Simple_P7_SubThenCol.py` remains manifest-classified as known-broken and excluded from release/full_v1;
- `Tutorial_ScheduledStreamLookup.py` wrapper remains manifest-classified as known-broken and superseded by direct real-solve scripts;
- full tutorial rationalisation, optional-lm3 proof, and GPU/CPU matrix hardening belong to post-D7 work.

## Closeout recommendation

Request external review for final D7 closure using the regenerated review pack and recorded final focused/full validation for commit `5e5372fff386378dde3f8dcd0acd8c880c70667d`.

Do not continue adding broad hardening or framework scope in D7 unless review finds a concrete blocker.
