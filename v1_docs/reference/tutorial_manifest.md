# Tutorial Manifest Reference

Status: staged V1 draft

Current file:

```text
tutorials/v1/tutorial_manifest_v1.json
```

The manifest records tutorial metadata. It should become the easy-to-check
catalogue for all working tutorials under:

```text
tutorials/v1/
```

## Target Role

The target role of the manifest is to answer:

- which tutorials exist
- which tutorials are active
- which tutorials are blocked or retired
- which runner gate each tutorial belongs to
- which asset profile is required
- what acceptance rule applies
- whether exact recovery is required
- whether truth/oracle data is used
- whether a true key is supplied to the solver
- what a reviewer needs to know

The manifest should not be a hidden control surface for beginner users. It is a
review and release metadata file.

## Current State

The current manifest names the promoted working tutorial files under
`tutorials/v1/`. Older replaced files live under `tutorials/old/`.

Target:

```text
one working tutorial catalogue, clear gates, no stale duplicate lists
```

The pretty-print runner owns the selected review list and thresholds. The
manifest owns the broader metadata.

## Suggested Fields

Each working tutorial should have enough metadata to support docs and tests:

| Field | Meaning |
| --- | --- |
| `path` | Tutorial file path under `tutorials/v1/`. |
| `title` | Human-readable title. |
| `cipher_family` | Main cipher family or workflow. |
| `tutorial_kind` | Lesson type. |
| `gate` | Beginner/release/extended/showcase/optional/blocked lane. |
| `required_asset_profile` | Asset profile needed to run. |
| `acceptance_kind` | How pass/fail is decided. |
| `min_match_ratio` | Threshold when match-ratio acceptance is used. |
| `uses_oracle_stop_score` | Whether oracle stop score is used. |
| `supplies_true_key_to_solver` | Whether the true key is supplied to the solver. |
| `current_status` | Active, optional, slow, showcase, blocked, retired. |
| `notes` | Short reviewer explanation. |

Acceptance kinds are enum values in code and serialized as strings in the
manifest:

| Acceptance | Meaning |
| --- | --- |
| `exact` | Expected to recover the full reference text. |
| `near_exact` | Expected to be effectively solved, with only tiny mismatch allowance. |
| `human_readable` | Expected to produce a readable solve above the stated threshold. |
| `showcase_near_solve` | Public showcase where exact recovery is not required. |
| `process_success` | Process success only; avoid for public V1 solve evidence. |
| `requires_asset_profile` | Runner should treat asset availability as the controlling condition. |
| `blocked_known_issue` | Known blocked entry; excluded from normal release runs. |

## Gate Ideas

The exact names can evolve, but the docs should preserve these concepts:

| Gate concept | Meaning |
| --- | --- |
| beginner/smoke | Small first check. |
| release | Normal public release tutorial. |
| extended | More confidence, slower or broader. |
| showcase | Useful public demo, possibly near-solve. |
| optional asset | Requires assets beyond the default profile. |
| slow demo | Works, but not selected by normal release runs. |
| blocked | Known issue; excluded until fixed. |
| retired | Kept only for history or removed after review. |

## Easy Update Contract

Adding a tutorial should be a small, reviewable change:

1. Add the tutorial file under `tutorials/v1/`.
2. Add or update manifest metadata.
3. Add it to the pretty-print runner if it is selected for that review set.
4. Update public docs only if the tutorial is public-facing.
5. Add or update a focused alignment test.
6. Run the pretty-print output-review runner before release.

If this becomes annoying, the next improvement should be a small checker or
generator that compares the runner, manifest, and docs table.
