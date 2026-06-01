# Active co-ordination board

This is the short cross-project board.

| Project | Why active now | Depends on | Current planning state | Next concrete step |
|---|---|---|---|---|
| `no_wli` | template, upstream solver-learning stream, and active PhaseB scorer work | none | active n-gram Hamming coherence scorer contract promoted after exact filtered n-gram v1 closed as too brittle | inspect backend/build patterns and n-gram asset schema before coding the scorer |
| `rdp_v1` | needed for release-shaping and repo-level truth | no-WLI lessons, current code cross-check | active home with support/reference layers and round-2 crosscheck | decide which support notes stay live versus move to archive later |
| `benchmark_campaign_v1_1` | general community benchmark and p13-learning stream | current benchmark code/tests; some v1 boundary truth | active home with several support/reference layers and round-2 crosscheck | re-check scoring/Torch support notes against current tests |
| `p13_real_ciphertext_campaign` | real-ciphertext solving frontier including `5455` | no-WLI pipeline lessons; solve-proof tooling; LP transcript/API capability | starter home with readiness-context pack and round-2 crosscheck | choose first exact `5455` comparison/control question and add first result note |
| `completed/lp_domain` | completed capability record | none | completed home exists | keep as completed reference, not active frontier |
| `legacy/v1_old_active_index` | preserve old execution context safely | replacement live homes | legacy home exists | leave as reference only; do not treat as live truth |
| `archive/phased_refactor_and_review` | preserve older planning/review pack safely | none | archive home exists | reference only unless a live project points back |
| `archive/no_wli_planning_refactor_20260404` | preserve older no-WLI planning-shape pack safely | none | archive home exists | reference only unless a live project points back |
| `archive/no_wli_stage35_transition_20260402` | preserve older no-WLI transition pack safely | none | archive home exists | reference only unless a live project points back |
| `archive/forensic_audit_2026` | preserve older forensic audit pack safely | none | archive home exists | reference only unless a live project points back |

## Current migration rule

For now, each chat should aim to complete one small safe slice:
- create or improve one control file
- create or improve one project home
- move only a small set of live documents
- do not bulk-move legacy material until the destination is stable
