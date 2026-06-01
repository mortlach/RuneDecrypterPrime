# Seed Family Triage Shadow v1 First Read

Bundle:
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/seed_family_triage_shadow_v1/20260408T172151Z__seed_family_triage_shadow_v1/`

Question:
- Can the frozen stop and family-quality stack already support a useful
  shadow-only seed and family budget layer?

First read:

- Seed-level bands are now explicit and non-trivial:
  - `high`
    - `411`, `511`, `611`, `711`, `1111`
  - `medium`
    - `1011`
  - `unclear`
    - `1311`, `1411`
  - `low`
    - `811`, `911`, `1211`, `1511`
- Policy mapping is also explicit:
  - `focus_with_exploration`
    - `411`, `511`, `611`, `711`, `1111`
  - `balanced_portfolio`
    - `1011`
  - `exploration_heavy`
    - `1311`, `1411`
  - `observe_only`
    - `811`, `911`, `1211`, `1511`

Family-enriched read:

- `1111`
  - primary family `f0`
  - secondary family `f1`
  - exploratory family `f2`
  - current read: accepted miss worth focused follow-up without pretending the
    current stop harness would have caught it
- `1311`
  - primary family `f0`
  - secondary family `f1`
  - exploratory family `f2`
  - current read: mixed enough to stay exploration-heavy rather than promoted
- `1411`
  - primary family `f1`
  - secondary family `f0`
  - exploratory family `f2`
  - current read: truth family is kept primary, but the contradictory family
    evidence still forces an exploration-heavy policy
- `411`
  - strong truth-family focus, but still keeps both a secondary and an
    exploratory family alive
- `611`
  - same overall shape as `411`, but without the same-family archive case
- `1011`
  - balanced portfolio rather than focused
  - this is the main sign that the v3 weak-truth read is actually changing the
    budget recommendation

What this does well:

- it combines stop-side and family-side evidence without mutating stop logic
- it gives all 12 review seeds a usable shadow priority band
- it keeps non-zero exploration everywhere
- it avoids collapsing entirely to one truth family

What still limits it:

- family priority still leans heavily toward truth winners plus one active
  alternative
- the current first pass does not yet prove that this allocator would change
  downstream search enough to matter
- `1311` and `1411` remain mixed rather than sharply separated

Current recommendation:

- treat `seed_family_triage_shadow_v1` as a useful offline planning layer
- do not promote it into pipeline control
- get external review on whether this is already decision-useful or whether the
  next move should skip straight to solver-side portfolio / selector modelling
