# No-WLI Solver Development Pivot Synthesis

Date: 2026-05-02

Status:

- external review synthesis
- broad local-rescue widening closed for now
- recommends moving up a level before more runtime

## Current Benchmark Basis

The active benchmark basis is still the retained fixed `p9/c3/l1000/no-WLI`
panel:

- fixed instances: `611`, `1111`, `1411`, `1511`
- search seeds: `7001-7005`
- retained completed jobs: `20`

Current case roles:

- `1511`: strong / positive-control-like non-solved case
- `611`: middle unsolved case
- `1111`: conversion-failure and fragmentation focus case
- `1411`: caveated cross-check

No recent branch has earned a general production claim against this retained
panel. The official benchmark position is therefore unchanged, but the
mechanism map is much sharper.

## Recent Movement

Saved-surface reshuffling is closed in the tested form.

- Phase-C multi-thread long harvest completed `1539 / 1539` units in
  `19:21:02`.
- No frontload-depth, quota, or replacement family beat the reorder-only
  controls on usable gates.
- Repeated exact saved-surface replay rows were stable:
  - score: `513 / 513`
  - delta: `513 / 513`
  - winner: `513 / 513`
  - surface class: `513 / 513`

Richer upstream supply is real but expensive and did not convert.

- The `1111/search7002` richer-supply retake created true spare challengers.
- The completed microbatch took about `18.82h`.
- Downstream replacement on the richer pool remained flat; the useful lift was
  still the existing reorder-control surface.

Stage-2 checkpointing remains the cleanest review-ready candidate family, but
not a general runtime policy.

- The selector-checkpoint line survived provenance reconciliation.
- It remains a branch-specific semantic/provenance pass with a kept-lane
  throughput caveat.
- It should be reviewed as a candidate mechanism and validation design, not as
  a deployed default.

Stage-3 entry allocation remains active as a mechanism but closed in the
tested constant-local-depth handoff form.

- Prior six-job full-pipeline panel capped after one control job.
- Saved-handoff constant-local-depth activation was structurally real:
  candidate init3 `288`, legacy init3 `64`, candidate new init3 keys `80`.
- Runtime results split:
  - `1111/search7005`: `0.372 -> 0.374`, `+0.002`, `7139.745s`
  - `1111/search7004`: `0.423 -> 0.406`, `-0.017`, `7755.439s`
- Stage 3.5 accept-pass fallback was rejected by broader offline stress:
  `151` rows, `75` negatives versus retained, `18` negatives versus selected
  start.

Local rescue is real but not policy-clean.

- Frontier-space robustness harvest completed `48 / 48` cells in `3.501h`.
- Selected rows:
  - `32 / 48`
  - `27 / 32` better than shallow
  - `3 / 32` worse than shallow
  - `28 / 32` nonnegative versus selected start
  - `4 / 32` negative versus selected start
- Acceptance-boundary audit scanned `1087` single-rule and `20292` two-feature
  sketches.
- It found `0` perfect single-rule separators and `0` perfect two-feature
  separators.

## Current Interpretation

We are no longer data-starved on the local-rescue surface. We are
policy-starved.

The repeated pattern is:

- broad runtime finds real pockets of lift
- posthoc audit finds tempting separators
- small confirmation or broader stress exposes regressions
- the candidate becomes mechanism evidence rather than a safe policy

That is the stalled shape. It explains why progress has looked like quantum
jumps rather than smooth improvement: each useful run discovers a new pocket,
but the current tooling does not yet turn pockets into validated decision rules.

## Wider Approach Changes Worth Reviewing

1. Build a first-class experiment ledger/query layer.

   We need one retained table keyed by fixture, search seed, stage, candidate
   hash, source bundle, and decision label. It should join runtime outputs,
   offline audits, closeout recommendations, and timing rows without manual
   reconstruction from planning notes.

2. Add held-out validation design tooling.

   Before more threshold or local-rescue work, require a frozen rule manifest,
   train/validation split, leakage checks, and an automatic report that says
   whether the rule used any posthoc or truth-only fields.

3. Add an oracle-gap map.

   Separate three failure modes:

   - good candidates are never generated
   - good candidates are generated but not selected
   - good candidates are selected locally but fail acceptance or propagation

   This would stop us from treating every miss as a Stage 3.5 policy problem.

4. Improve score calibration offline.

   The search-score guard keeps showing both value and missed positives. A
   calibrated score model should be trained only on retained archive outcomes
   and evaluated offline first, with strict separation from runtime decision
   evidence.

5. Instrument marginal-gain and early-stop curves by stage.

   Runtime is not smooth. We need per-stage marginal gain curves and
   early-stop opportunity curves so long runs can be sized from observed yield
   rather than from wallclock hope.

6. Create a local-rescue acceptance sandbox.

   Many policy ideas can be tested by replaying accept decisions over saved
   archives without launching new runtime. This should become a standard
   pre-runtime gate.

7. Treat timing class as part of the experiment design.

   Widened supply, altered entry allocation, and deeper local rescue are
   different timing classes. The first completed cell in each class should
   update the wallclock reference before any serial widening.

8. Move the next science branch upstream unless there is a held-out
   local-rescue validation design.

   Current evidence favors returning to representative selection,
   checkpoint-validation, and better candidate-generation diagnostics over
   more local-rescue threshold hunting.

## Review Questions

1. Is the Stage-2 checkpoint line the only surviving candidate worthy of a
   held-out validation design now?
2. Should local rescue be retained strictly as mechanism evidence until a
   formal held-out rule harness exists?
3. Which tool would most reduce overfitting risk: experiment ledger, held-out
   validation harness, oracle-gap map, or score calibration?
4. What is the smallest credible validation unit that could move the official
   benchmark, rather than only adding another local pocket of lift?

## Recommendation

Do not start another broad runtime batch from the current local-rescue work.

Next work should be one of:

- external review of this pivot pack
- a held-out validation harness for the Stage-2 checkpoint line
- an experiment-ledger/oracle-gap tool that turns the existing retained data
  into a cleaner branch-selection surface

My recommendation is to build the ledger/oracle-gap layer first, then use it to
choose the next validation branch instead of selecting the next runtime cell by
manual narrative review.
