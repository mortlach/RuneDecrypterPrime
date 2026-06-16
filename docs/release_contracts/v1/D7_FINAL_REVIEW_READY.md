# D7 final review-ready note

Branch: `prelease/v1.0.0_d7`

Final evidence status at time of this note: user reported green after the D7 tutorial-integration and runner-contract fixes.

GitHub connector status visibility: no combined status checks or workflow runs were visible for the latest checked commit through the connector when this note was written. Treat the user-reported green result and attached CI/log evidence outside this note as the validation source.

## Final D7 position

D7 should now move from hardening/development into closeout review.

The branch is not a tiny documentation-only closure branch. It contains real V1 hardening, including:

- enum-domain ownership and normalisation hardening;
- solver report semantic-domain split;
- stop-reason error classification hardening;
- scorer-lane/report-only visibility contracts;
- ScheduledStreamLookup V1 API/wrapper/cipher/tutor-lock contracts;
- tutorial/session report framework foundation;
- tutorial manifest integration and default release-gate promotion for one exact ScheduledStreamLookup real solve;
- review-pack metadata binding to git branch/head/dirty state.

This is acceptable for D7 only because the changes are contract/release hardening, evidence hardening, and tutorial-gate integration, not new solver/cipher/scorer feature expansion.

## Final tutorial-gate evidence

User-reported local `full_v1` tutorial gate result:

```text
RDP V1 tutorial runner | gate=full_v1 | asset_profile=lm2_baseline
Selected gates: v1_smoke, v1_release, v1_extended, v1_showcase_near_solve
Selected entries: 14
passed: 14
failed: 0
Process finished with exit code 0
```

Important ScheduledStreamLookup tutorial results in that run:

```text
Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py: PASS, match=1.000
Tutorial_ScheduledStreamLookup_RealSolve_P13Primes.py: PASS, match=1.000
Tutorial_ScheduledStreamLookup_RealSolve_P13P31Segmented.py: NEAR_SOLVE_ACCEPTED, match=0.901
```

## Final pytest/CI evidence

User reported the branch is green after the final runner default-profile contract fix.

Earlier full pytest evidence before the final doc-only update and runner-contract correction was:

```text
1177 passed, 41 skipped
```

The last concrete CI failure before green was:

```text
test_tutorial_runner_uses_ide_defaults_without_environment_override
expected: release
actual: full_v1
```

That failure was fixed by changing the contract to require a valid configured default profile and valid environment overrides, rather than hard-coding `release` as the only acceptable IDE default.

## Review-pack evidence note

A final evidence hardening fix was applied after inspecting the generated review-pack summary: `tools/release_review_pack.py` now writes `git_branch`, `git_commit_sha`, and `git_working_tree_dirty` into both `REVIEW_PACK_MANIFEST.json` and the sidecar summary JSON.

Regenerate the review pack from the final branch head before external review. The regenerated pack should show a `git_commit_sha` matching the final reviewed commit.

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
9. Is the D7 scope now frozen except for reviewer-requested fixes?

## Known non-blockers / future work

These should not block D7 closure:

- optional LM3/LM4 asset tests skip when those assets are absent;
- optional Torch/CUDA tests skip when the environment lacks the required backend;
- `Tutorial_PeriodicColumnar_Simple_P7_SubThenCol.py` remains manifest-classified as known-broken and excluded from release/full_v1;
- `Tutorial_ScheduledStreamLookup.py` wrapper remains manifest-classified as known-broken and superseded by direct real-solve scripts;
- full tutorial rationalisation, optional-lm3 proof, and GPU/CPU matrix hardening belong to post-D7 work.

## Closeout recommendation

Request external review for final D7 closure after regenerating the review pack from the final branch head.

Do not continue adding broad hardening or framework scope in D7 unless review finds a concrete blocker.
