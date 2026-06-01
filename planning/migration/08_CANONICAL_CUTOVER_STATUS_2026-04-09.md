# Canonical cut-over status - 2026-04-09

This note applies the canonical cut-over criteria to the current migrated
planning bundle.

## Overall judgement

**Canonical and promoted for default day-to-day use.**

The control layer under `planning/` is now the default
planning system for repo-wide work.

Explicit exceptions still kept outside the canonical tree:
- `planning/no_wli/` as an upstream live home
- `planning/working/` as a compatibility stub only

## Criteria assessment

### A1. Each active home has a stable live pack
Assessment:
- **yes**

`rdp_v1`:
- yes, with current state / workstream / document map / runbook / remaining-work
  and crosscheck notes present

`benchmark_campaign_v1_1`:
- yes, with the same basic live pack plus crosswalk and crosscheck notes

`p13_real_ciphertext_campaign`:
- yes; the home is intentionally thin, but the thread pack is coherent and the
  upstream-link hygiene is now explicit

### A2. Support/reference layers are clearly secondary
Assessment:
- **yes**

Both `rdp_v1` and `benchmark_campaign_v1_1` now have:
- freshness notes
- recommended keep sets
- clearer split between active support and historical-but-useful support

`p13_real_ciphertext_campaign` also now clearly separates:
- direct `5455` thread files
- broader p13 readiness context
- explicit upstream no-WLI routing

### A3. Cross-project control layer is readable
Assessment:
- **yes**

The bundle now has:
- project index
- master timeline
- co-ordination board
- dependency map
- problem-thread index
- remaining-work file
- crosscheck status file
- cut-over criteria file
- old-surface retirement matrix

### A4. Legacy/archive no longer compete with live entry points
Assessment:
- **yes**

The old top-level competing surfaces are now retired.
Archive and legacy material remains preserved, but it no longer competes with
the active homes.

## Remaining non-blocking exceptions

### Exception 1 - `planning/no_wli/` remains intentionally live
That is still explicit and acceptable.
It is an upstream live home, not a competing repo-wide control surface.
Its internal legacy residue is now retired into
`planning/legacy/no_wli_live_surface_residue_2026-04-14/`, so the exception is
structural rather than a mixed live/legacy tree problem.

### Exception 2 - `planning/working/` remains as a compatibility README stub
This is no longer a competing planning surface.
It only exists so older log/watch path habits do not break abruptly.

## Practical conclusion

The bundle is now the **main working planning surface**.

Use it by default.
Treat old top-level planning surfaces as retired history.
Keep `planning/no_wli/` explicit as the one upstream live exception.
