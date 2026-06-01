# Final no-WLI science state and next-run recommendation

## Executive summary

The no-WLI work has moved through four main layers:

```text id="5kfm1p"
1. Establish fixed-panel benchmark behaviour.
2. Map late-family / Stage-3.5 failure modes.
3. Test whether Phase-C saved-surface ordering can rescue weak routes.
4. Test whether broader surface reshuffling or Stage-3 entry allocation is the next lever.
```

The current evidence says:

```text id="o86k7l"
- The Stage2 checkpoint branch is review-ready after provenance reconciliation.
- Broad Phase-C surface reshuffling is now a clean negative result.
- Exact saved-surface replay is deterministic across repeated passes.
- Full-pipeline Stage-3 entry panels are too expensive as configured.
- The next highest-value direction is late-stage-only handoff/archive rescue.
```

The next target should not be another broad atlas or full-pipeline rerun.

Recommended next branch:

```text id="0o1qfs"
stage35_resume_from_handoff_focus_family_rescue_v1
```

with target priority:

```text id="mmjgcb"
1. 1111/search7005  primary selector/rescue target
2. 1111/search7004  fragmentation target
3. 1111/search7002  aligned control / runner proof case
```

---

# 1. Longer journey so far

## 1.1 Fixed-panel baseline: learning the landscape

The early retained fixed-panel work established that the no-WLI solver does not fail uniformly. The useful structure was seed/family dependent.

The broad read became:

```text id="brrom7"
1511:
  strongest non-solved family / high-scoring useful reference

611:
  mixed family with some useful positive cases

1111:
  main conversion-failure family

1411:
  useful but caveated, especially for late-family/focus-family interpretation
```

This mattered because it stopped us treating no-WLI as one homogeneous solver failure. We moved from:

```text id="9vjvjs"
“does the solver work?”
```

to:

```text id="3yppuq"
“which mechanism is failing on which seed family?”
```

That has been the main scientific shift.

## 1.2 Late-family mapping: the key 1111 split

The later Stage-3.5 / family mapping work made the `1111` family much clearer.

The important distinction is:

```text id="d6nezn"
1111/search7002:
  aligned strong case
  good control
  not the best primary rescue target

1111/search7004:
  fragmented late-family case
  good route/family instability target

1111/search7005:
  strongest late selector/rescue target
  retained best is low, but focus-family / archive evidence suggests headroom
```

This is why the next work should not just chase the biggest current score. `7002` is already strong and aligned. It is useful as a control. `7005` and `7004` are more scientifically interesting because they expose late-stage failure modes.

## 1.3 Stage2 checkpoint branch: learning evidence discipline

The Stage2 selected-family Phase-A checkpoint branch answered a narrower question:

```text id="nspmf5"
Can an early Phase-A checkpoint rescue a mixed upstream selector by filtering
collapse lanes while keeping viable lanes?
```

The carried contract became:

```text id="l7l72h"
fixture family:
  fixed 1111/search7001-7005

checkpoint:
  restart 32

field:
  phaseA_best_init_match

threshold:
  0.3865

filter:
  fallback + early stop

keep:
  no action
```

After the provenance reconciliation work, the branch is now carried as:

```text id="a9eaaf"
review-ready after provenance reconciliation
live runtime still blocked
production/general policy not claimed
```

The scientific lesson is:

```text id="cjlyam"
Early Phase-A evidence can separate collapse-like selected-family lanes from
viable/no-harm selected-family lanes in this fixed family.
```

The engineering lesson is just as important:

```text id="5d4k03"
A result is not review-ready until raw rows, state/events, summaries,
recommendations, readouts, and row-level recomputation agree.
```

That lesson should now apply to all future review packs.

## 1.4 Phase-C saved-surface ordering: what we tested

The Phase-C work asked:

```text id="2fdgqa"
Can we rescue weak late routes by changing the saved Phase-C surface ordering?
```

The early useful policies were:

```text id="yjbhzs"
phaseb_topk_anchor_swap_v1
phaseb_topk_frontload_all_v1
```

Then we tested whether more aggressive or more detailed surface reshuffling helped:

```text id="vx09yf"
frontload-depth
quota
phaseB_topk-only replacement
```

The four-case pilot completed cleanly and showed weak/negative signal. The larger multi-thread long harvest then tested the same idea properly.

## 1.5 Phase-C multi-thread long harvest: decisive result

The long harvest completed:

```text id="cbfx77"
19 cases
27 policies
3 passes
1539 / 1539 policy units
19h21m runtime
```

It proved two things.

First, exact saved-surface replay is deterministic:

```text id="q2lly9"
513 repeated case-policy pairs
score consistent:         513 / 513
delta consistent:         513 / 513
winner consistent:        513 / 513
surface-class consistent: 513 / 513
```

Second, the extension families did not help:

```text id="yk1ats"
frontload-depth:
  no positive usable-gate result beyond reorder controls

quota:
  no positive usable-gate result beyond reorder controls

replacement:
  no positive usable-gate result beyond reorder controls
```

So the conclusion is:

```text id="kpfm79"
Close broad Phase-C saved-surface reshuffling in this form.
```

The only remaining Phase-C ordering signal is the narrow chooser between:

```text id="iujb8l"
anchor_swap
frontload_all
```

But the effect sizes are small. That is not the best next compute target.

## 1.6 Stage-3 entry / constant-local-depth panel: useful failure

The Stage-3 entry constant-local-depth panel was designed to ask:

```text id="mejeo2"
Can wider constant-local-depth Stage-3 entry allocation improve the 1111
reorder-signal lanes?
```

The six-job panel launched correctly, but the first child job alone took:

```text id="up3h2e"
13h32m47s
```

The matrix stopped after:

```text id="0w47iy"
1 / 6 jobs complete
```

The completed child was:

```text id="pzncx0"
1111/search7002
best_match_ratio = 0.754
best_stage = stage35_substitution_only
```

The completed child appears to be the control / legacy-entry configuration:

```text id="ed0m3i"
allocation_policy = legacy_fixed_budget
init_keys_cap = 192
```

not the intended constant-local-depth candidate:

```text id="yenwrl"
allocation_policy = constant_local_depth
init_keys_cap = 288
```

So the intended paired comparison was not answered.

But the run taught a very useful operational lesson:

```text id="52bij5"
Do not use full-pipeline six-job panels for this next question.
They are too expensive and they recompute too much.
```

It also produced a fresh handoff/archive for `1111/search7002`, which is useful for a late-stage resume runner.

---

# 2. What is now closed

## 2.1 Closed: Stage2 checkpoint packaging/provenance issue

Carry as:

```text id="elllvf"
review-ready after provenance reconciliation
live runtime still blocked
```

No new checkpoint science should be run until a separate reason appears.

## 2.2 Closed: broad Phase-C surface reshuffling

Closed in this form:

```text id="n7mvyq"
frontload-depth
quota
replacement
more width variants
more repeated exact-replay passes
```

Reason:

```text id="ief5xq"
The 1539-unit long harvest found no extension-family win over reorder controls,
and replay results were deterministic.
```

## 2.3 Closed: full-pipeline six-job entry panel as configured

Reason:

```text id="cmd6lq"
First child took 13h32m.
Only the control-style 1111/search7002 job completed.
No candidate comparison completed.
```

Do not rerun this panel as-is.

---

# 3. What remains open

## 3.1 Late-stage handoff/archive rescue

This is the highest-value branch.

Question:

```text id="u9gzob"
Can we start from retained stage3/stage35 handoff artefacts and test late-stage
selector/rescue variants without recomputing the whole pipeline?
```

This directly follows from the evidence:

```text id="9ni7rl"
surface reshuffling is not enough
full-pipeline recomputation is too expensive
late-family packs show target-specific headroom
handoff/archive artefacts exist
```

## 3.2 Narrow anchor_swap vs frontload_all chooser

This remains open, but lower priority.

It is clean analytically, but likely lower impact because:

```text id="0hh4rg"
effect sizes are small
ordering differences are now well bounded
the bigger problem is late conversion / rescue
```

---

# 4. Highest-value next run

## Branch

```text id="9dqv8x"
stage35_resume_from_handoff_focus_family_rescue_v1
```

## Main question

```text id="5zstpi"
Starting from retained handoff/archive artefacts, can a late-stage-only selector
or rescue variant improve beyond the retained route without recomputing the full
pipeline?
```

## Target priority

### 1. `1111/search7005` — primary target

Why:

```text id="wxglhu"
retained best is low
family/focus evidence suggests latent headroom
final-best family diverges from the dominant/focus family
frontload_all showed a strong clue, although in a drifted/non-usable gate
```

This is the best selector/rescue target.

### 2. `1111/search7004` — secondary target

Why:

```text id="orsln9"
fragmented late-family structure
frontload_all had the best usable atlas clue
good case for route/family instability
```

This is the best fragmentation target.

### 3. `1111/search7002` — control/proof target

Why:

```text id="4bd4kr"
aligned strong case
fresh handoff/archive exists from the v79 child bundle
full-pipeline control reached 0.754
good for proving the resume runner works
lower likely upside
```

## Do not start by optimising `7002`

`7002` is important, but mostly as a control. The next run should not be framed as:

```text id="14o2j3"
improve 7002
```

It should be framed as:

```text id="0df3zv"
prove the late-stage resume harness on 7002, then target 7005 and 7004 for
actual rescue headroom.
```

---

# 5. Dev integration actions

## 5.1 Update `00_CURRENT_STATE.md`

The local dev finding is correct: `01_EXPERIMENT_INDEX.md` is updated, but `00_CURRENT_STATE.md` does not yet carry matching entries for:

```text id="qnuhrm"
Phase-C multi-thread harvest
v79 Stage-3 entry panel
next handoff-rescue direction
```

Add a new section like this.

```markdown id="gglz8l"
## Current no-WLI science state as of 2026-04-28

### Stage2 selected-family Phase-A checkpoint

Status: review-ready after provenance reconciliation.

Carried claim:
On the fixed `1111/search7001-7005` replay family, the restart32
`phaseA_best_init_match >= 0.3865` checkpoint reproduces the intended
keep/filter split.

Boundary:
This is not a general live-runtime policy. Live runtime remains blocked.

### Phase-C saved-surface ordering / reshuffling

Status: broad saved-surface reshuffling closed for now.

The Phase-C multi-thread long harvest completed:

- 19 cases
- 27 policies
- 3 passes
- 1539 / 1539 policy units
- repeated exact replays were stable for score, delta, winner, and surface class

Result:
No frontload-depth, quota, or replacement family beat the reorder-only controls
on usable decision gates.

Carried conclusion:
Do not add more width/quota/replacement variants now. If Phase-C ordering is
revisited, keep it narrow: `phaseb_topk_anchor_swap_v1` versus
`phaseb_topk_frontload_all_v1`.

### Stage-3 entry constant-local-depth reorder-signal panel

Status: useful incomplete comparison; do not rerun as-is.

The six-job panel launched correctly, but capped after one completed child job.
The completed child was `1111/search7002`, reached `best_match_ratio = 0.754`,
and appears to be the control / legacy-entry configuration.

Provenance caveat:
The completed child bundle has `dirty: 1` in `run_manifest.json`; carry this
flag anywhere the result is used.

Carried conclusion:
The intended constant-local-depth candidate comparison did not complete.
The full-pipeline panel shape is too expensive as configured.

### Next highest-value branch

Recommended next branch:

`stage35_resume_from_handoff_focus_family_rescue_v1`

Question:
Starting from retained handoff/archive artefacts, can a late-stage-only selector
or rescue variant improve beyond the retained route without recomputing the full
pipeline?

Target priority:

1. `1111/search7005` — primary selector/rescue target
2. `1111/search7004` — fragmented route/family target
3. `1111/search7002` — aligned control and resume-runner proof case

Required first step:
Verify handoff/archive paths for `1111/search7005`, `1111/search7004`, and
`1111/search7002` before writing the runner.
```

## 5.2 Fix the analyser reference

The local dev finding is correct:

```text id="a7tx37"
planning/projects/no_wli/20_active_plans/april_28_2026_summary_so_far.md
```

lists:

```text id="84wmkp"
analyse_phasec_multi_thread_long_harvest_v1.py
```

but dev reports that file does not exist.

Choose one of two actions.

Recommended simple action:

```text id="i5f1xg"
Drop that expected analyser path from april_28_2026_summary_so_far.md.
```

Reason:

```text id="bxh8t2"
The run output already contains readout, summary, family summary, pass summary,
science-thread summary, and repeat-consistency rows.
```

Only create the analyser later if there is a concrete need.

## 5.3 Carry the dirty flag

For the v79 child bundle, carry this caveat into every review/current-state surface:

```text id="dyv5oo"
Provenance caveat:
The completed v79 child run has `dirty: 1` in `run_manifest.json`.
The result is useful for diagnosis, but future reviewers should not treat it as
a pristine release-build benchmark.
```

## 5.4 Confirm runner-path hygiene

Dev has already confirmed:

```text id="oq0bkp"
v79 parent matrix files exist
intended Stage-3 runner exists
scratch fixed_instance_solver_development_v1.py does not exist
handoff/archive folders and expected files exist for 7002, 7004, and 7005
```

That resolves the earlier uncertainty. No further action needed except making sure `00_CURRENT_STATE.md` records the state.

---

# 6. Proposed next planning entry

Once `00_CURRENT_STATE.md` is updated, create the next active plan:

```text id="gctudz"
planning/projects/no_wli/20_active_plans/no_wli_stage35_resume_from_handoff_focus_family_rescue_plan_2026-04-28.md
```

It should not be too broad. It should start with a proof run.

Recommended shape:

```text id="1fp9xq"
Phase 1:
  verify loader can read stage3_prep.json and stage35_seed_archive.json
  for 7002, 7004, 7005

Phase 2:
  run one late-stage-only control replay on 7002

Phase 3:
  run one or two selector/rescue variants on 7005

Phase 4:
  only if Phase 3 is interpretable, add 7004
```

Hard constraints:

```text id="xrpn4f"
no full-pipeline recomputation
no Stage2 checkpoint changes
no new Phase-C surface-width variants
write state/events/rows/summary/readout after each variant
```

---

# 7. Final programme read

The longer journey now makes sense:

```text id="1oc0z1"
We started by mapping solver performance across fixed panels.
We found that failure was structured by seed/family, not uniform.
We used late-family tools to identify 1111 as the main conversion-failure family.
We proved one narrow Stage2 checkpoint contract after fixing provenance.
We tested Phase-C saved-surface reshuffling and closed broad width/quota/replacement variants.
We attempted a full-pipeline Stage-3 entry comparison and learned that the full-pipeline shape is too expensive.
The evidence now points to late-stage-only handoff/archive rescue as the highest-value next step.
```

That is the actual scientific arc.

The next run should be small, direct, and late-stage-only:

```text id="rxjlkf"
stage35_resume_from_handoff_focus_family_rescue_v1
```

not another atlas and not another full-pipeline panel.
