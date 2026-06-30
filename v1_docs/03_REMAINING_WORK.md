# V1 docs remaining work

Status: staged working checklist

This is the route from the current `v1_docs/` draft to public V1 docs.

## Current State

The staged docs now have:

- beginner install path
- tutorial runner page
- troubleshooting page
- output/logs page
- core design page
- runes and text page
- runs/reports/artifacts page
- tutorial evidence page
- LP examples page
- contributor testing/tutorial/docs-style pages
- initial reference pages
- source map
- cross-check ledger

This is enough for review. It is not yet enough to replace the old public docs.

## How Much Is Left

Rough estimate:

| Work | Size | Notes |
| --- | --- | --- |
| Core coder docs WP0 | complete | Docs-first/tooling-later decision recorded. |
| Core coder docs WP1/WP2 | medium | Expand module inventory and public API boundary package by package. |
| Core coder docs WP3-WP6 | high | Requires run-flow, config, pipeline, report, and artifact inspection. |
| Core contributor how-to docs WP7 | medium to high | Safe recipes for ciphers, solvers, scorers, and tutorials. |
| Targeted docstring annotation WP8 | high | Requires judgement; avoid low-value mass comments. |
| Docs drift tests WP9 | medium | Add focused checks without making brittle global assumptions. |
| Tutorial manifest alignment | low | Initial alignment done; needs review and tests. |
| Pretty tutorial runner verification | medium | Needs actual runner pass on this machine. |
| Public-doc promotion decision | medium | Decide whether `v1_docs/` replaces, merges into, or sits beside `docs/`. |
| Old docs redirect/retire pass | medium | Especially `docs/INDEX.md`, quickstart, install, troubleshooting, tutorials index. |
| Human wording review | medium | Read all staged docs as a beginner and as a contributor. |
| Reference expansion | low to medium | Add ciphers/scorers/assets only after stable surfaces are checked. |
| Link/index polish | low | Make final map easy to navigate. |

The main writing pass is mostly done. The remaining work is about making the
docs true, maintainable, and connected to the repo.

## Core Coder Documentation Work Packages

| WP | Work package | Intelligence level | Status |
| --- | --- | --- | --- |
| WP0 | Record docs-first/tooling-later decision | Low to medium | Initial slice complete. |
| WP1 | Core package inventory | High | Top-level package inventory drafted; exact source-to-test links still need expansion. |
| WP2 | Public API boundary | Very high | API run/display/wrapper boundary drafted; expand config/data surfaces only after inspection. |
| WP3 | Run flow documentation | High | Initial run-flow page drafted. |
| WP4 | Spec/config object docs | High | Initial config object page drafted; deeper core config pages pending. |
| WP5 | Pipeline pages | Very high | Initial cipher/key/solver/scoring pages drafted; deeper source-to-test mapping pending. |
| WP6 | Reports, telemetry, and artifacts | Very high | Initial report, telemetry, and artifact boundary page drafted. |
| WP7 | Extension how-to docs | High | Initial extension map and cipher/solver/scorer-lane how-to pages drafted. |
| WP8 | Docstring policy and targeted annotation | High | Policy recorded; initial public RunSpec and artifact-manifest contract docstrings added. |
| WP9 | Cross-check and drift tests | Medium-high | Focused docs-contract tests cover public API, module map, pipeline pages, how-to pages, docstrings, and navigation drift. |

Current implementation rule:

```text
Content and support boundaries first. Sphinx/autodoc/Doxygen later.
Generated documentation output must stay outside the repo, for example under
run_outputs/docs/.
```

## Must Do Before Public Promotion

1. Review the tutorial metadata owner split: runner owns selected list and
   thresholds; manifest owns classification metadata.
2. Add or update a test that checks manifest, runner, and docs alignment for the
   chosen model.
3. Run:

```text
python tutorials/v1/run_tutorials.py
```

4. Run full output mode when ready to inspect printout wording:

```python
CONSOLE_OUTPUT = ConsoleOutput.FULL
```

5. Review the generated tutorial logs.
6. Decide how `v1_docs/` moves into public docs.
7. Update or redirect old public docs so readers do not see two conflicting
   beginner paths.
8. Re-run focused docs/code contract tests.
9. Do a final beginner read-through.
10. Run focused docs-contract tests for the `v1_docs/coder/` and
    `v1_docs/reference/public_api_allowlist.md` content.

## Tutorial Alignment Options

### Chosen Direction: Manifest Owns Tutorial Metadata

`tutorial_manifest_v1.json` now lists the promoted tutorial files and classifies
working tutorials under `tutorials/v1/`.

The pretty-print runner can still keep the selected list as constants, but tests
should verify the selected list is present in the manifest.

The user-facing goal is simple:

```text
all working V1 tutorials live in tutorials/v1/ and have clear metadata
```

## Public Docs Promotion Options

### Option A: Promote `v1_docs/` Into `docs/`

Move staged pages into the public docs tree, replacing or redirecting stale old
pages.

Best when V1 docs are ready to become the main docs.

### Option B: Keep `v1_docs/` As A Prerelease Docs Tree

Link to `v1_docs/` from top-level README or `docs/README.md` while old docs stay
in place.

Best while review is still active.

### Option C: Merge Selectively

Promote beginner pages first, then core/reference pages after review.

Best if release needs the beginner path fixed before the full reference set is
settled.

## Old Docs Likely To Touch Later

Do not change these until promotion is approved:

```text
docs/INDEX.md
docs/README.md
docs/setup/installation.md
docs/guides/quickstart.md
docs/guides/troubleshooting.md
docs/guides/outputs.md
docs/tutorials/index.md
```

These are the places most likely to conflict with the staged V1 path.

## Open Questions

- Should optional/advanced working tutorials be listed in public docs, or only
  in contributor/reference docs?
- Should `v1_docs/` be promoted as a whole, or should beginner docs promote
  first?

## Stop Point For Review

The best next review point is after:

- one successful tutorial runner pass
- one full-output pass for wording

At that point the docs can move from staged draft to promotion planning.
