# no-WLI Phase-C Multi-Thread Long Harvest Plan

Date: 2026-04-27

Status:

- completed long-run plan
- direct-run Python file only
- no PowerShell wrapper
- planning integration updated after close-out
- completed inside the 25-hour capped data-taking budget

## Why this exists

The previous Phase-C conditioned-ordering pilot completed much faster than expected:

- planned as a long data harvest
- completed 60 / 60 units
- elapsed about 1 hour
- output was valid and useful
- recommendation was `close_or_hold` / no clear win for the extra depth/quota/replacement variants on the four-cell pilot

That pilot showed the runner shape works, but it was not enough processing time for the available scheduling window.

This branch deliberately scales the same saved-surface replay style by roughly 20x.

## Main question

Can a larger saved-surface harvest across all candidate3 cases reveal stable case-dependent structure in Phase-C ordering choices?

More simply:

- when should `phaseb_topk_anchor_swap_v1` be preferred?
- when should `phaseb_topk_frontload_all_v1` be preferred?
- do width/depth/quota/replacement policies ever beat those reorder controls?
- are exact replay results repeatable across repeated passes?
- is timing the main thing that varies?

## Suspicion

The useful Phase-C choice is not a global policy.

The likely useful principle is conditioned:

- some cases prefer anchor-swap style ordering
- some cases prefer frontload-all style ordering
- most extra width/quota/replacement variants may not beat the reorder controls
- repeated passes should give the same scores/winners if the saved replay path is deterministic, even if runtime varies

## Main alternative

The wider harvest still shows no stable conditioned structure.

If so:

- close this exact Phase-C width/quota/replacement direction
- keep the useful negative result
- move to a different mechanism layer, probably local search / rescue rather than more surface reshuffling

## Mechanism layer

- ordering
- allocation
- local search / rescue, indirectly
- determinism / repeatability check

This is not a Stage2 checkpoint branch.
This is not a live runtime branch.
This is not a production policy branch.

## Run shape

Runner:

`tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_phasec_multi_thread_long_harvest_v1.py`

Output root:

`output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/`

Output bundle shape:

`<timestamp>__phasec_multi_thread_long_harvest_v1/`

Source matrix:

`output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T042939Z__candidate3_saved_surface_exact_matrix_v1/candidate3_saved_surface_exact_matrix_summary.json`

Cases:

- all candidate3 saved-surface cases from the source matrix

Policies:

- `source_order`
- `phaseb_topk_anchor_swap_v1`
- `phaseb_topk_frontload_all_v1`
- `phaseb_topk_frontload_1_v1`
- `phaseb_topk_frontload_2_v1`
- `phaseb_topk_frontload_3_v1`
- `phaseb_topk_frontload_4_v1`
- `phaseb_topk_frontload_5_v1`
- `phaseb_topk_frontload_6_v1`
- `phaseb_topk_frontload_7_v1`
- `phaseb_topk_frontload_8_v1`
- `phaseb_topk_quota_1_v1`
- `phaseb_topk_quota_2_v1`
- `phaseb_topk_quota_3_v1`
- `phaseb_topk_quota_4_v1`
- `phaseb_topk_quota_5_v1`
- `phaseb_topk_quota_6_v1`
- `phaseb_topk_quota_7_v1`
- `phaseb_topk_quota_8_v1`
- `phaseb_topk_replace_width_1_v1`
- `phaseb_topk_replace_width_2_v1`
- `phaseb_topk_replace_width_3_v1`
- `phaseb_topk_replace_width_4_v1`
- `phaseb_topk_replace_width_5_v1`
- `phaseb_topk_replace_width_6_v1`
- `phaseb_topk_replace_width_7_v1`
- `phaseb_topk_replace_width_8_v1`

Passes:

- pass 1: `full_width_atlas`
- pass 2: `stability_repeat_pass`
- pass 3: `stability_repeat_pass`

Expected size if the source matrix has 19 cases:

- 19 cases x 27 policies x 3 passes = 1539 policy units

Timing estimate from pilot:

- pilot: 60 units in about 1 hour
- expected: 1539 units in about 25-27 hours
- hard cap: 25 hours

The cap is intentional. If the run caps cleanly, partial output is valid.

## Runtime cap

Hard cap:

- 25 hours

Cap check:

- after each completed policy unit

Partial output:

- valid
- written after every completed policy unit
- should be analysed if the run caps or is interrupted

## Expected saved artefacts

Top-level bundle files:

- `matrix_run_state.json`
- `matrix_run_events.jsonl`
- `run_config.json`
- `phasec_multi_thread_long_harvest_case_rows.jsonl`
- `phasec_multi_thread_long_harvest_case_rows.csv`
- `phasec_multi_thread_long_harvest_policy_summary_rows.csv`
- `phasec_multi_thread_long_harvest_family_summary_rows.csv`
- `phasec_multi_thread_long_harvest_pass_summary_rows.csv`
- `phasec_multi_thread_long_harvest_science_thread_summary_rows.csv`
- `phasec_multi_thread_long_harvest_repeat_consistency_rows.csv`
- `phasec_multi_thread_long_harvest_summary.json`
- `phasec_multi_thread_long_harvest_recommendation.json`
- `phasec_multi_thread_long_harvest_readout.md`
- `run_summary.json`

Per-case/per-pass files under:

`cases/pass_<NN>__<science_thread>/fixture_<fixture_seed>__search<search_seed>/`

Expected per-case/per-policy files:

- `case_manifest.json`
- `<policy_index>__<policy_name>__candidate_saved_surface_summary.json`
- `<policy_index>__<policy_name>__comparison_summary.json`
- `<policy_index>__<policy_name>__surface_diagnostics.json`

## What counts as useful data

Useful data includes:

- candidate score vs control
- candidate score vs best reorder control
- winner identity changes
- winner source/rank changes
- selected-surface membership changes
- selected-surface order changes
- effective applied width
- repeated-pass score/winner consistency
- runtime per unit
- whether timing varies while scores/winners remain stable

## Decision after run

Refine if:

- anchor-swap vs frontload-all has stable case-dependent structure
- or a width/quota/replacement family beats reorder controls in a route/surface-explainable way
- or repeated-pass diagnostics reveal a specific determinism/timing finding worth following

Hold if:

- the output is partial but useful
- the run caps before enough cases/policies complete
- results are mixed but still interpretable

Close this direction if:

- width/quota/replacement variants still do not beat reorder controls
- anchor-swap vs frontload-all differences are small/noisy
- repeated exact replays are stable and only timing varies
- no conditioned rule direction emerges

## Non-goals

Do not use this run to:

- tune the Stage2 checkpoint
- reopen live runtime
- promote a production policy
- change solver logic
- add multiprocessing
- mix in Stage-3.5 rescue changes
- interpret score alone as sufficient evidence

## First checks after launch

After the first completed unit, confirm the output bundle contains:

- `matrix_run_state.json`
- `matrix_run_events.jsonl`
- `run_config.json`
- `phasec_multi_thread_long_harvest_case_rows.csv`
- `phasec_multi_thread_long_harvest_summary.json`
- `phasec_multi_thread_long_harvest_readout.md`

If those exist, let the run continue.

## After completion or cap

Analyse the output before starting another run.

Do not modify the runner mid-run unless it fails to write data.


I extracted and analysed the uploaded bundle:

```text
20260427T020956Z__phasec_multi_thread_long_harvest_v1
```

## Overall verdict

This is a **clean, high-value negative result**.

```text
Run quality:        good
Data completeness:  complete
Determinism:        strong
Policy result:      negative for depth/quota/replacement variants
Useful signal:      only the two reorder controls matter
Next direction:     stop surface reshuffling; move to rescue/local-search or route-selection logic
```

I would close this run as:

```text
Completed long-harvest atlas. No depth/quota/replacement candidate family beat
the reorder-only controls. Repeated exact-replay rows were stable. The useful
remaining signal is case-dependent choice between anchor_swap and frontload_all,
not more Phase-C surface reshuffling.
```

This is not a failure. It is a useful narrowing result.

---

# 1. Integrity check

The bundle is internally complete.

```text
status:                 completed
bundle_complete:        1
completed policy units: 1539 / 1539
cases:                  19
policies:               27
passes:                 3
rows:                   1539
duplicates:             0 pass/case/policy duplicates
elapsed:                19:21:02
exit status:            clean
```

The 1539 rows are exactly:

```text
19 cases x 27 policies x 3 passes = 1539
```

Each pass completed:

```text
pass 1: 513 rows
pass 2: 513 rows
pass 3: 513 rows
```

So the run is not partial. We can treat it as a completed atlas.

---

# 2. Repeatability / determinism result

This is one of the strongest outcomes.

The run repeated every case-policy pair three times:

```text
513 unique case-policy pairs
3 repeated passes
```

Repeat consistency result:

```text
score consistent:         513 / 513
delta consistent:         513 / 513
winner consistent:        513 / 513
surface-class consistent: 513 / 513
inconsistent rows:        0
```

Plain English:

```text
The saved-surface exact replay is deterministic for score, delta, winner, and
surface class across repeated passes.
```

That matters a lot. It means we should stop worrying, for this branch, that the policy conclusions are random replay noise.

Runtime did vary:

```text
mean policy runtime:   45.1 s
median policy runtime: 14.0 s
max policy runtime:    305.8 s
```

The important distinction is:

```text
Scores/winners/surface classifications were stable.
Timing varied.
```

So this confirms the earlier throughput caveat: timing can move around, but the exact replay result itself is stable.

---

# 3. Usable versus non-usable cases

Only 10 of the 19 cases were usable decision-gate cases.

Usable cases:

```text
611/search7003
611/search7004
1111/search7001
1111/search7002
1111/search7004
1411/search7003
1511/search7002
1511/search7003
1511/search7004
1511/search7005
```

Non-usable / context-only cases were mostly `drifted`:

```text
611/search7001
611/search7002
611/search7005
1111/search7003
1111/search7005
1411/search7001
1411/search7002
1411/search7004
1411/search7005
```

This matters because some non-usable cases show tempting positive movements, especially:

```text
1411/search7004 frontload_all: +0.026
1111/search7005 frontload_all: +0.025
```

But both are marked `drifted`, so they should be treated as clues, not promotion evidence.

---

# 4. Main scientific result

The headline result is very clear:

```text
No depth/quota/replacement policy beat the best reorder control.
```

More strongly:

```text
No extension-family row was positive versus control.
No extension-family row was positive versus best reorder.
```

Across all extension rows:

```text
frontload_depth rows:              456
phaseB_topk_quota rows:            456
phaseB_topk_only_replacement rows: 456
total extension rows:              1368

positive vs control:     0
positive vs best reorder: 0
```

Across usable extension rows:

```text
usable extension rows:   720
positive vs control:     0
positive vs best reorder: 0
```

That is decisive for this branch.

The extra policies did not help:

```text
frontload_depth:
  changed surface order often
  did not change winners
  did not improve score

quota:
  did not produce useful selected-surface changes
  did not improve score

replacement:
  mostly effective width 0 / true no-op
  did not improve score
```

Plain English:

```text
Moving more phaseB_topk rows around is not the lever.
```

---

# 5. What did produce positive movement?

Only the two reorder controls produced positive rows:

```text
phaseb_topk_anchor_swap_v1
phaseb_topk_frontload_all_v1
```

Positive rows across all passes:

```text
total positive rows: 45
all from reorder_control
extension-family positive rows: 0
```

On usable gates:

```text
usable positive rows: 21
unique usable positive case-policy pairs: 7
all from reorder_control
```

The usable positive cases were:

```text
1111/search7002:
  anchor_swap      +0.004
  frontload_all    +0.004

1111/search7004:
  anchor_swap      +0.002
  frontload_all    +0.008

1511/search7002:
  frontload_all    +0.004

1511/search7005:
  frontload_all    +0.009

611/search7003:
  anchor_swap      +0.006
```

So the useful policy signal is not a new width/depth/quota/replacement family. It is:

```text
choose between anchor_swap and frontload_all
```

---

# 6. Anchor-swap versus frontload-all

Across all 19 cases, comparing only the two reorder controls:

```text
frontload_all wins: 6
anchor_swap wins:   4
tie:                9
```

On the 10 usable cases:

```text
frontload_all wins: 4
anchor_swap wins:   2
tie:                4
```

Usable case table:

```text
case             control  anchor  front_all  winner
611/search7003   0.466    0.472   0.463      anchor_swap
611/search7004   0.758    0.758   0.741      anchor_swap / source better than frontload
1111/search7001  0.420    0.420   0.420      tie
1111/search7002  0.750    0.754   0.754      tie between reorder controls
1111/search7004  0.432    0.434   0.440      frontload_all
1411/search7003  0.905    0.905   0.905      tie
1511/search7002  0.842    0.842   0.846      frontload_all
1511/search7003  0.844    0.844   0.844      tie
1511/search7004  0.571    0.569   0.571      source/frontload tie; anchor worse
1511/search7005  0.686    0.686   0.695      frontload_all
```

This is a real result:

```text
There is case dependence between anchor_swap and frontload_all.
```

But it is still small:

```text
largest usable frontload_all lift: +0.009
largest usable anchor_swap lift:   +0.006
```

So I would not build a big new theory from it. I would carry it as a useful route-choice clue.

---

# 7. Winner changes and surface changes

The run tells a very consistent story:

```text
Surface changes are common.
Winner changes are much rarer.
Score improvements are rarer still.
```

Across all rows:

```text
true_noop:                                  969
active_surface_change_same_winner_flat:    483
winner_change_scored:                       42
winner_change_flat:                         27
surface_change_same_winner_scored:          18
```

That means most policy work is doing one of two things:

```text
nothing
```

or:

```text
changing the order/surface but leaving the same winner and same score
```

This is the key mechanism read.

The current bottleneck is probably not “can we alter the surface?” The run proves we can alter it. The bottleneck is:

```text
Can the altered surface create a better winner or allow a better local rescue?
```

Most of the time, no.

---

# 8. Frontload-depth result

The frontload-depth family is now pretty clearly closed for this form.

It did this:

```text
selected_surface_changed_cases: 57 per policy
winner_identity_changed_cases: 0
positive_on_gate: 0
negative_on_gate: 0
neutral_on_gate: 30
mean_delta_on_gate: 0.000
mean_vs_best_reorder_on_gate: -0.0031
```

Interpretation:

```text
Frontload-depth changes ordering, but it does not change the winner or score.
```

So increasing depth from 1 to 8 does not buy anything in this exact saved-surface replay.

---

# 9. Quota result

The quota family is also not promising in this form.

It reports nonzero effective width/count-like fields, but:

```text
selected_surface_changed_cases: 0
winner_identity_changed_cases: 0
positive_on_gate: 0
mean_delta_on_gate: 0.000
mean_vs_best_reorder_on_gate: -0.0031
```

Interpretation:

```text
The quota policy is not changing the selected surface in a useful way here.
```

So quota should not be the next branch unless someone first proves the builder is applying a meaningful surface change in the intended cases.

---

# 10. Replacement result

The replacement family is the cleanest no-op.

```text
effective_applied_width: 0
selected_surface_changed_cases: 0
winner_identity_changed_cases: 0
positive_on_gate: 0
mean_delta_on_gate: 0.000
mean_vs_best_reorder_on_gate: -0.0031
```

Interpretation:

```text
Replacement is not finding/using eligible replacements in this saved-surface
setting, or the effective replacement width is zero under the current contract.
```

I would close replacement-width experiments for now.

---

# 11. Runtime findings

The run completed in:

```text
19:21:02
```

Total measured policy-runtime sum:

```text
~19.29 h
```

By pass:

```text
pass 1: 7.35 h
pass 2: 5.75 h
pass 3: 6.18 h
```

The runtime was not evenly distributed. Some cases dominated:

```text
1111/search7002: 3.17 h
611/search7004:  2.85 h
1411/search7003: 2.38 h
1411/search7001: 2.37 h
1511/search7002: 2.37 h
1511/search7003: 2.33 h
```

Most other cases were much faster.

The biggest repeated runtime variation was in `1111/search7002`, for example:

```text
phaseb_topk_frontload_6_v1:
  min runtime: ~110.8 s
  max runtime: ~305.8 s
  same score / same delta / same winner
```

So the throughput caveat is real:

```text
Runtime varies substantially even when exact replay output is identical.
```

This is useful operationally. It means future long runs should continue using:

```text
generous caps
saved artefacts after every unit
end-of-run audit
```

rather than trying to predict exact wallclock.

---

# 12. What the run does *not* show

It does **not** show:

```text
a new global Phase-C ordering policy
```

It does **not** show:

```text
that frontload_depth/quota/replacement should be widened further
```

It does **not** show:

```text
that timing variation means score variation
```

It does **not** justify:

```text
live runtime reopening
```

It also does not prove Phase-C ordering is useless. It proves this narrower thing:

```text
More saved-surface reshuffling of this type is not the next lever.
```

---

# 13. Strongest conclusion

The strongest scientific conclusion is:

```text
The useful route signal is upstream of the extension families.

The two existing reorder controls can sometimes move the winner or score.
The later width/depth/quota/replacement variants do not add value on top of
those controls.
```

That means the next useful work should not be:

```text
more width variants
more quota variants
more replacement variants
more repeated exact-replay passes
```

The next useful work should be one of:

```text
1. choose anchor_swap versus frontload_all using saved-surface features

or

2. take the best reorder-control surface and spend effort on local search /
   rescue after that point
```

I think option 2 is now stronger.

Why?

Because option 1 only has small score movements. Option 2 addresses the observed bottleneck:

```text
surface changes often do not create better winners
```

So the next mechanism should be:

```text
local search / rescue after a promising reorder surface
```

not more reshuffling.

---

# 14. Recommended close-out note

I would write this into the project notes:

```text
The 20260427 Phase-C multi-thread long harvest completed cleanly:

- 19 candidate3 saved-surface cases
- 27 policies
- 3 passes
- 1539 / 1539 policy units
- 19h21m elapsed
- zero repeat-consistency mismatches

Main result:
No frontload-depth, quota, or replacement family beat the existing reorder-only
controls on usable decision gates. No extension-family row was positive versus
control or versus best reorder.

The only positive score movements came from the existing reorder controls:
phaseb_topk_anchor_swap_v1 and phaseb_topk_frontload_all_v1.

Interpretation:
This closes the current width/quota/replacement saved-surface reshuffling
direction. The remaining useful question is either case-conditioned selection
between anchor_swap and frontload_all, or a local-search/rescue branch starting
from the best reorder-control surface.

Runtime caveat:
Repeated exact replays were score/winner/surface deterministic, but runtime
varied materially. Future long runs should keep generous caps and write valid
partial artefacts after every unit.
```

---

# 15. Recommended next experiment

I would **not** run another atlas of surface variants.

Next branch should be:

```text
best_reorder_surface_rescue_v1
```

Question:

```text
If we start from the best reorder-control surface for each case, can extra
local search / rescue convert the small route improvement into a better final
winner?
```

Target cases should be the usable cases where reorder controls showed some signal:

```text
611/search7003       anchor_swap +0.006
1111/search7002      anchor/frontload_all +0.004
1111/search7004      frontload_all +0.008
1511/search7002      frontload_all +0.004
1511/search7005      frontload_all +0.009
```

Include a couple of controls:

```text
611/search7004       anchor is safe; frontload_all hurts
1511/search7004      source/frontload tie; anchor hurts
1411/search7003      flat high-score stable control
```

This would test the actual next mechanism:

```text
not “can we rearrange the saved surface?”
but “once we have the best route, can we rescue/search it better?”
```

That is where I would spend the next long run.

---

# 16. Final decision

```text
Close this long-harvest direction as a completed negative result.

Carry forward:
- exact replay is deterministic
- timing varies
- extra depth/quota/replacement surface policies do not help
- only anchor_swap/frontload_all matter
- next mechanism should be local search / rescue from the best reorder-control surface

Do not rerun this matrix.
Do not add width 9/10/etc.
Do not repeat the same exact replay passes again.
```

