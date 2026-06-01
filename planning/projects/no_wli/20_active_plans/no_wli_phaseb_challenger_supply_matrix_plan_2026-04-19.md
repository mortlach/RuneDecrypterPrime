# Phase-B challenger supply matrix plan

Date: 2026-04-19

Status:

- closed
- operational failure
- rescued partial canary retained

## Why this note exists

The Phase-C saved-surface `phaseB_topk` mass and frontload matrix is now closed.

That line was still useful. It established that:

- frontload depth remained active but did not beat the existing reorder controls
- the quota family was mostly structurally satisfied already
- when quota was not already satisfied, there were still zero eligible
  non-selected retained `phaseB_topk` challengers
- the `phaseB_topk`-only replacement family was structurally blocked because
  no eligible retained `phaseB_topk` challengers existed outside the selected set

So the next mechanism question must move upstream.

## Main question

The next question is:

- can a wider or more diverse upstream Phase-B saved challenger supply create
  useful non-selected late challengers for downstream Phase-C use?

In plain English:

- the current retained Phase-C surface is too saturated and too constrained
  for more `phaseB_topk` mass manipulation to teach us much
- so the next likely gain is to change the supply of saved Phase-B challengers,
  not to keep rearranging the same saturated Phase-C start set

## Scope

This is a fixed-instance runtime study on the same frozen panel basis.

It is not:

- a live promotion request
- a broad benchmark expansion
- a new Phase-C reorder family
- a rescue-enabled extension

It is a supply study.

## Overnight resource rule

This batch is intended to use much more of the overnight wallclock than the
recent short offline matrices.

The goal is to spend the overnight slot on one coherent upstream mechanism
question and then use the next day to decide whether downstream Phase-C
composition work is worth reopening under a richer retained pool.

## Working hypothesis

If the retained late pool contains no spare eligible `phaseB_topk` challengers,
then downstream quota and replacement policies will stay blocked.

So the next useful study is to vary upstream Phase-B saved challenger supply and
measure whether that produces:

- more unique retained `phaseB_topk` rows
- more non-selected retained `phaseB_topk` challengers
- more usable downstream Phase-C candidate-pool variety
- and, only secondarily, any improvement in downstream best-match outcomes

## Required pre-run block

Before any overnight batch in this fixed-panel line, write all of these:

- Question
- Suspicion
- Main alternative
- If suspicion is true, expect
- If alternative is true, expect
- Tomorrow's decision rule

Also write one explicit mechanism-layer claim:

- supply
- selection
- ordering
- allocation
- or local search / rescue

The point is to keep each overnight run on one mechanism layer rather than
mixing layers inside one batch.

## Operational gate

Before treating any overnight matrix as scientifically readable, verify all of
these:

- expected job count is explicit in the plan
- the first progress event appears in the run events log
- matrix run state increments beyond `0` completed jobs
- at least one child run leaves `running` and writes normal completion artifacts

If these gates are not met, the run is not yet at a scientific branch point.
It is still in operational closure.

## Closure status

This plan is now closed as an operational failure of batch sizing.

What happened:

- the intended serial matrix had `18` jobs
- the first completed job took about `18h57m`
- the batch stopped after `1/18` jobs when the wallclock cap was finally
  checked before job `2`

What remains valid:

- one rescued completed canary:
  - `611/search7002`
  - `phaseb_supply_selected24_saved16_stage3only_v1`

Next plan:

- `planning/projects/no_wli/20_active_plans/no_wli_phaseb_challenger_supply_retake_plan_2026-04-20.md`

## Batch label

Use a label in this shape:

`phaseb_challenger_supply_matrix_v1`

## Operational v1 runtime slice

The full conceptual `5 x 4` runtime grid is not one honest overnight serial
batch on this machine.

So `v1` activates a bounded slice of the same mechanism question:

- fixed-panel slice:
  - primary trio only
  - `611`
  - `1111`
  - `1511`
  - retained search seeds:
    - `7002`
    - `7004`
- downstream Phase-C policy:
  - unchanged control lane
- Stage 3.5:
  - off
  - runtime is kept focused on Phase-B supply and Phase-C downstream variety
  - best-match outcomes stay secondary readouts, not the main gate

Active runtime presets for this batch:

- `phaseb_supply_selected24_saved16_stage3only_v1`
- `phaseb_supply_selected24_saved64_stage3only_v1`
- `phaseb_supply_selected48_saved96_stage3only_v1`

Why this is the right first runtime slice:

- it keeps the mechanism question upstream and coherent
- it spans moderate versus deep save depth
- it includes one genuinely wide and deep supply setting
- it avoids silently promising a runtime grid the current machine cannot
  complete overnight

If this slice creates real spare non-selected retained `phaseB_topk`
challengers, later runtime can widen from here.

## Core batch design

This batch varies upstream Phase-B supply knobs while keeping downstream
Phase-C selection policy fixed for interpretation.

Default downstream policy for this study:

- keep the downstream Phase-C start policy on the existing control lane
- do not mix in new Phase-C selection variants during this batch

The point is to isolate supply.

## Conceptual study axes

### Axis A - Phase-B selected width

Vary how many Phase-B seeds are preserved for downstream use.

Suggested values:

- `8`
- `16`
- `24`
- `32`
- `48`

### Axis B - Phase-B saved top-k / archive depth

Vary how much Phase-B challenger material is retained for later analysis and
downstream start construction.

Suggested values:

- `16`
- `32`
- `64`
- `96`

### Axis C - tie-band / preservation width only if already exposed cleanly

Only include this axis if the current code already exposes it cleanly and
deterministically for the fixed-panel line.

If exposed cleanly, suggested values are modest, for example:

- narrow
- medium
- wide

Do not invent a new tie metric just for this batch.

## What this batch must measure

This study is not mainly about raw best-match win counts.

The main outputs must quantify supply.

For every case and every config, record:

- retained selected Phase-B count
- retained selected Phase-B unique end-hash count
- retained Phase-B top-k saved count
- retained Phase-B unique end-hash count
- retained non-anchor selected `phaseB_topk` count
- retained non-selected `phaseB_topk` challenger count
- retained non-selected `phaseB_topk` challenger hashes
- whether downstream quota would now be genuinely engageable
- whether downstream `phaseB_topk`-only replacement would now be genuinely
  engageable

Also record downstream outcome summaries as secondary outputs:

- best match ratio
- winner hash
- winner source
- winner lane

## Required outputs

This batch must write all of these:

- machine-readable per-config summary table
- machine-readable per-case per-config table
- one short human readout
- one explicit promote / refine / close recommendation

## Primary analysis questions for the next day

The next-day readout must answer these.

### Supply questions

- does any config create a meaningful number of non-selected retained
  `phaseB_topk` challengers?
- on which cases?
- how many spare challengers appear:
  - at least `1`
  - at least `2`
  - at least `3`

### Saturation questions

- does the current saturation of non-anchor selected `phaseB_topk` rows reduce
  under any config?
- or do wider upstream settings still mostly collapse into the same downstream
  retained starts?

### Identity questions

- are new challenger hashes actually new, or mostly duplicates of already
  selected material?
- does wider supply increase unique retained late material or only archive more
  near-duplicates?

### Outcome questions

- do any supply-rich configs also improve downstream outcomes?
- if not, do they at least create enough spare challengers to justify reopening
  a downstream Phase-C composition study?

## Decision rules

### Promote to downstream follow-up only if

- one or more configs create real spare retained `phaseB_topk` challengers on
  meaningful cases
- the spare challenger count is not trivial
- and the retained downstream surfaces become genuinely engageable for quota or
  replacement style policies

### Refine if

- some supply increase appears
- but only on a narrow case subset
- or only with very large configs that may be too expensive or too noisy

### Close if

- even wider upstream supply still produces no meaningful spare retained
  `phaseB_topk` challengers
- or wider supply mostly archives duplicates without creating a more useful
  downstream late pool

## Not allowed in this batch

Do not mix in:

- new Phase-C reorder policies
- new Phase-C quota policies
- new Phase-C replacement policies
- rescue-enabled extensions
- broad benchmark widening
- speculative scoring changes

Keep this batch about upstream supply only.

## Implementation note

Proceed directly unless one of these becomes ambiguous in code rather than in
planning:

- which existing runtime knobs genuinely change retained Phase-B challenger
  supply on the fixed-panel line
- whether retained outputs already expose enough detail to count spare eligible
  `phaseB_topk` challengers honestly without inventing new semantics

If either ambiguity bites:

- stop
- write the ambiguity down explicitly
- do not patch over it with an invented metric
