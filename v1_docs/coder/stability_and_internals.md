# Stability And Internals

Status: staged V1 draft

Owner paths:
- `src/rune_decrypter_prime/`
- `tests/`

Related pages:
- `public_api.md`
- `extension_points.md`
- `telemetry_and_reports.md`

Stability:
- Semi-stable contributor guidance.

## Purpose

This page separates supported V1 surfaces from implementation details.

Importable does not mean public. A helper can be useful inside the codebase and
still be unsafe for external callers or tutorials to depend on.

## Stability Labels

| Label | Meaning |
| --- | --- |
| Public V1 surface | Supported user-facing API. Changes need docs and compatibility review. |
| Semi-stable contributor surface | Useful for contributors, but may change with clear notes and focused tests. |
| Internal helper | Implementation detail. Do not document as public API. |
| Test-only helper | Exists for tests, fixtures, or contract checks. |
| Legacy / transitional | Kept for compatibility while the preferred surface is elsewhere. |

## Public V1 Surfaces

Use `public_api.md` and `../reference/public_api_allowlist.md` as the support
boundary for public imports.

Public or semi-stable changes should update:

- docs
- focused tests
- public allowlist when appropriate
- compatibility notes when existing users may be affected

## Internals To Treat Carefully

These areas can be read and documented for contributors, but should not be
promoted casually:

- solver internals and `_SOLVER_TABLE`
- scorer runtime builders
- private report-builder helpers
- telemetry payload internals
- generated run output layout outside known artifact paths
- experimental cipher-development workspaces outside the runtime package
- asset loader internals
- local benchmark or cache outputs

## What Not To Rely On

Do not rely on:

- exact console wording
- local absolute paths
- generated logs in the repo
- cache directory names
- private helper names beginning with `_`
- unregistered artifact files being portable
- report-only fields changing ranking
- telemetry as a resume format

## Promotion Checklist

Before moving an internal helper into a supported surface:

1. Decide whether it is public V1 or semi-stable contributor API.
2. Add or update tests for the supported behavior.
3. Add docs that name the support level.
4. Add it to `../reference/public_api_allowlist.md` if it is import-supported.
5. Check whether old callers need a legacy or transitional path.

Do not promote a helper only because a tutorial happens to import it. Prefer a
small public wrapper when the underlying implementation is not stable enough.
