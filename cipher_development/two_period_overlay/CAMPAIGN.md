# Two-period overlay campaign

## Problem

Develop and diagnose solvers for a two-period additive overlay modulo 29. The primary target is the 308-rune P13/P17 benchmark with the complete word `uncomfortable` fixed at rune offset 188.

## Clean-start decision

WP6 begins with newly generated controlled evidence. The earlier exploratory seven-hour run is not imported, replayed or supported by compatibility code.

The old work contributes only these prior exploratory assumptions:

- smaller parameter combinations can solve quickly;
- P13/P17 is deliberately difficult;
- the P13/P17 crib and gauge leave 16 affine variables;
- straightforward coordinate, short-SA and coordinate-beam searches plateaued;
- merely extending the same trajectory is unlikely to be informative;
- candidate supply, diversity, ranking, handoff and exploitation remain separate possible failure mechanisms.

These assumptions guide experiment design. They are not experiment-ledger evidence.

## Benchmark ladder

All rungs use the same 308-rune whole-word-aligned plaintext slice, complete WLI, complete crib, modulo-29 overlay, scorer contract and gauge `B[0] = 0`.

| Benchmark ID | Periods | Expected free dimension | Purpose |
|---|---:|---:|---|
| `alice_308_p05_p07_d00` | 5/7 | 0 | contract and exact-reconstruction canary |
| `alice_308_p05_p13_d04` | 5/13 | 4 | easy search benchmark |
| `alice_308_p09_p13_d08` | 9/13 | 8 | intermediate diagnostic benchmark |
| `alice_308_p13_p17_d16` | 13/17 | 16 | primary difficult benchmark |

The implementation must derive and validate each free dimension from the actual crib equations. A fifth bridge rung is added only if evidence shows that the dimension-8 to dimension-16 jump is too large.

## Frozen target contract

- benchmark: `alice_308_p13_p17_d16`;
- alphabet: 29 runes;
- periods: 13 and 17;
- schedule: full overlay;
- text length: 308;
- crib: complete `uncomfortable` at rune offset 188;
- gauge: `B[0] = 0`;
- expected affine free dimension: 16;
- normal evidence: full WLI;
- decision scorer: `pct.logp.win10` with character and WLI 3/4-grams;
- benchmark truth: terminal evaluation only.

## Known RDP contracts

Campaign configuration is explicit in source. Do not use command-line arguments or environment variables. Candidate and replay artifacts use the shared WP1-WP5 contracts unchanged.

## Evidence mode

`with_wli` is the normal mode.

## Truth policy

`benchmark_only`. Search code receives ciphertext, WLI, the crib, affine key space and scoring callback. Plaintext and benchmark key remain in a separate terminal reference object.

Truth must not influence generation, scoring, selection, stopping, archive retention, ranking, handoff or exploitation.

## Applicable prior lessons

- CSL-001 — persist exact candidates;
- CSL-002 — persist terminally evaluated candidates;
- CSL-004 — separate search evidence from truth;
- CSL-005 — canaries do not decide scientific hypotheses;
- CSL-007 — saved surfaces may support reranking without rediscovery.

## Intentional departures from those lessons

None. CSL-007 remains a candidate lesson until a real bound surface replays successfully.

## Current failure classification

Candidate supply, diversity collapse, ranking, handoff and exploitation.

## Scientific question

Does preserving and handing forward a full-WLI-ranked archive of coordinate-search candidates outperform independent exploitation starts?

## Hypothesis

Useful coordinate basins are found but discarded between independent methods.

## Strongest alternative

Coordinate discovery never reaches useful candidate regions, so archive handoff cannot improve exploitation.

## Candidate identity

The complete expanded, gauge-fixed key. Payloads retain the affine variables and benchmark ID required for replay. The terminal candidate ID, arm and artifact are recorded explicitly.

## Candidate archive policy

- capacity: 64;
- decision score: `wli_decision_score`;
- higher is better;
- candidate-ID tie-breaking;
- no family cap in the first experiment.

## Current implementation boundary

The benchmark builder and affine key-space contract support the full ladder. The archive-handoff search runner remains frozen to the P13/P17 target until lower-rung search profiles and evidence budgets are reviewed.

## Controlled experiment sequence

1. `benchmark_contract_canary_v1` — validate every ladder rung twice without an expensive search.
2. `technical_canary_v1` — execute the existing tiny P13/P17 archive-handoff path. Completed successfully on 2026-07-23.
3. `technical_canary_replay_suite_v1` — replay both bound starting batches twice in one evidence pack.
4. `coordinate_supply_v1` — retain and diagnose every unique coordinate optimum on lower rungs before P13/P17.
5. `candidate_diversity_v1` — closed from the diagnostics embedded in `coordinate_supply_v1`; no duplicate run is required.
6. `candidate_selection_v1` — compare deterministic top-score and diverse-high-score d8 selections and replay both twice.
7. `matched_exploitation_v1` — compare top-WLI, diverse-high-WLI and one common independent-control surface under matched d8 exploitation budgets.
8. `target_coordinate_supply_v1` — run two independent, equal-budget 32-restart P13/P17 seed blocks and diagnose the combined target pool.
9. `target_ranking_diagnostic_v1` — replay the complete 64-candidate target pool twice and assess aggregate WLI-to-truth rank alignment terminally.
10. `multiscale_scorer_contract_canary_v1` — execute the predeclared J0/S1/S2/S3/B1/J1/F1 panel using installed orders 1-4.
11. `multiscale_static_panel_v1` — rerank the saved d4, d8 and d16 pools under every profile and report static enrichment and cost.
12. `exact_extra_crib_contract_canary_v1` — verify the offset-206 and offset-81 complete-word d8 contracts.
13. `candidate_replay_v1` — verify every later cross-experiment candidate surface without discovery or exploitation.


## Coordinate-supply experiment contract

`coordinate_supply_v1` runs only the dimension-4 and dimension-8 ladder rungs.

For each rung:

- 32 deterministic coordinate restarts;
- eight requested coordinate sweeps;
- seed block 0;
- 900-second wall-clock safety limit;
- every unique restart optimum retained in `discovery_pool_archive.json`;
- a capacity-64 operational `coordinate_archive.json`;
- every restart, seed, starting variables, ending variables, evaluations and completed sweeps retained;
- deterministic affine and expanded-key Hamming diagnostics;
- no simulated annealing, handoff, control arm or candidate mutation.

The declared upper evaluation budget is 89,152 across both rungs. The experiment always returns `refine`. A unique-candidate threshold of 16 is reported separately for each rung but does not itself decide the campaign.

## Matched-exploitation experiment contract

`matched_exploitation_v1` uses the two verified eight-candidate d8 selection batches and one common eight-candidate independent-control batch.

For each of eight matched slots:

- top-WLI, diverse-high-WLI and independent-control starts receive the same deterministic exploitation seed;
- each arm receives 500 simulated-annealing proposals in each of two cycles;
- each arm receives up to four coordinate-polish sweeps;
- all starts, final candidates, gains, diagnostics and parent identities are retained;
- every unique final candidate is bound and replayed twice;
- terminal benchmark truth is evaluated only after all search and replay work is complete.

The panel has a 900-second wall-clock safety limit and a 46,432-evaluation ceiling, including control construction and final replay. It always returns `refine`. A policy signal requires at least six of eight matched top-versus-diverse wins and a majority over the common control; otherwise it is `inconclusive`.

## Control arm

The same number of independently generated starts receive the same SA and coordinate-polish budgets. Comparison index `i` uses the same exploitation RNG seed in each arm. Final control candidates are retained.

## Archive-handoff arm

Each completed coordinate restart offers its optimum to a bounded archive. Selected candidates are written to self-contained bound batches, exploited and returned to the archive with parent provenance.

## Decision rule

Canaries, supply, selection and the first d8 matched-exploitation panel always return `refine`. They close infrastructure gates and report bounded scientific signals; they do not promote a P13/P17 mechanism by themselves. A later predeclared P13/P17 panel may promote or close only after candidate supply, policy contrast, replay and evaluation budgets are all valid.

A wall-clock safety interruption is incomplete or underpowered evidence and cannot promote or close a mechanism.

## Replay plan

Each source run writes a truth-free replay context containing the exact benchmark contract, ciphertext, WLI, crib, affine matrices, scorer contract and evaluator/model provenance.

Every batch crossing an experiment boundary has a content-addressed binding joining the source run, benchmark, configuration, context, batch and source archive. Replay verifies provenance, identity-payload agreement, affine reconstruction, benchmark membership, gauge, stored score and deterministic ranking. Replay never runs discovery or exploitation.

## Automatic review packs

Every benchmark, search and replay run automatically writes:

```text
output/cipher_development/two_period_overlay/review_packs/
  two_period_overlay_<experiment_id>_<run_id>_review_pack.zip
```

The ZIP contains the complete run directory, campaign and relevant shared source snapshots, focused tests, evaluator/model provenance, environment metadata, a SHA-256 inventory and a generated `REVIEW.md`. ZIP ordering and timestamps are fixed so repacking unchanged evidence is byte-identical.

The pack rejects absolute repository paths in run and source evidence and truth-bearing search-visible JSON. Text validation logs are converted to UTF-8 and the exact local repository root is replaced with `<repo_root>`. Only terminal `experiment_result.json` may contain reference evaluation. A failed run still produces an explicitly incomplete diagnostic pack when the experiment directory exists.

Local validation is recorded through `write_local_validation_receipt()` after focused and real-asset tests. The receipt is bound to a content fingerprint of the packed campaign, shared-contract and focused-test source. Test logs placed below `output/cipher_development/two_period_overlay/validation/` are included automatically. A pack is `review_ready` only when required run, source and source-run artifacts are complete, the recorded tests passed and the validation fingerprint matches the packed source. Git cleanliness is retained as informational metadata, not a gate.

## Scale-up gates

Do not run a bounded full P13/P17 panel until:

- historical-import code is absent;
- every ladder contract passes;
- the real-RDP technical canary completes;
- source batches are bound and replay twice;
- stored scores and ranking verify;
- candidate identity, affine reconstruction and gauge checks pass;
- discovery supplies at least twice the intended exploitation-batch size in unique candidates;
- compared selection policies produce different candidate sets;
- exact evaluation and wall-clock budgets are frozen.

## Stop criteria

Stop scientific interpretation if replay is non-deterministic, provenance cannot be reproduced, truth enters search-visible evidence, candidate identity disagrees with payload, affine reconstruction fails, the gauge is violated, or an incomplete run is presented as complete.

Close only the current discovery mechanism if two predeclared equal-budget seed blocks cannot supply the minimum unique candidates. Do not close the whole cipher campaign on that basis.

## Current candidate archive status

The lower-rung coordinate-supply run retained 30 unique d4 optima and 32 unique d8 optima. The d4 pool contained an exact solution. The d8 pool showed no duplicate-basin collapse and supplied two verified eight-candidate selection surfaces.

The matched d8 exploitation panel retained and replayed eight finals from each of the top-WLI, diverse-high-WLI and independent-control arms. Both selected surfaces beat the common control in seven of eight matched slots, but neither selected surface improved under the tested SA-plus-coordinate-polish budget.

The bounded P13/P17 target-supply panel retained 64 unique coordinate optima across two independent 32-restart seed blocks. There was no cross-block identity overlap. Combined nearest-neighbour affine Hamming distances were 10 to 14 in the 16-dimensional space.

## Current result

The benchmark-contract, technical infrastructure, lower-rung candidate-supply, diversity, selection, matched-exploitation, P13/P17 target-supply and first target-ranking gates are closed.

The complete 64-candidate `target_ranking_diagnostic_v1` surface replayed deterministically and verified every stored score. Its recorded 3/4-order baseline showed essentially no terminal rank alignment:

- score versus rune matches Spearman: `-0.011193193796700716`;
- score versus complete-word matches Spearman: `0.029620291861395556`;
- score versus affine-variable matches Spearman: `-0.061171713672161704`;
- rune pairwise concordance: `0.49249870667356443`;
- best-rune candidates: 52 matches, with best score rank 37;
- top-score candidate: 26 rune matches, one complete-word match and zero affine-variable matches.

The present recorded 3/4 ranking is therefore not an adequate judge for this saved P13/P17 surface. This closes only that baseline-ranking question; it does not close character/WLI scoring generally or prove that no useful search gradient exists.

A scoring-contract mismatch was also confirmed. `SCORING_CONTRACT` declares character/WLI pair weights `0.25/0.75`, while simultaneously supplying per-order maps that each sum to one. Both current NumPy and Torch scorer implementations prefer the per-order maps and globally normalise them, so the recorded baseline actually applies effective character/WLI family weights `0.5/0.5`. The campaign preserves that exact historical contract as `J0` and tests the intended `0.25/0.75` weighting separately as `J1`. Core scorer behaviour is not changed silently.

The exact complete-word spans at offsets 206 and 81 are both the eight-rune word `dormouse`. Each adds modular rank eight to the original d16 affine space and therefore defines a d8 contract. These positions remain declared oracle assistance for Experiment A only.

## Closed mechanisms

- inadequate coordinate candidate supply on the d4 and d8 rungs;
- coordinate-basin diversity collapse on the d4 and d8 rungs;
- loss of selected d8 candidates to unmatched independent starts under the tested exploitation budget;
- inadequate coordinate candidate supply in the first bounded two-block P13/P17 panel;
- coordinate-basin identity collapse across the first two P13/P17 seed blocks;
- adequacy of the exact recorded J0 3/4-order ranking on the saved 64-candidate P13/P17 surface.

The top-WLI versus diverse-high-WLI policy comparison remains open. The tested short-SA operator did not improve established d8 coordinate optima. The usefulness of lower-order, staged and correctly weighted character/WLI profiles remains open.

## Pack 01 multiscale result

Pack 01 completed with deterministic scoring, replay and source-bound validation across all seven profiles.

The static surfaces did not justify freezing a ladder, but they gave a clear next-step signal:

- on d4, `S2 WLI12` and `S3 char12 + WLI12` gave rune-match Spearman values of approximately `0.858` and `0.833`;
- on the saved lower-rung d8 pool, `S3` and `S2` gave approximately `0.672` and `0.645`;
- on the saved P13/P17 d16 pool, `S3` and `S2` gave approximately `0.511` and `0.500`;
- J0 and J1 remained effectively uninformative on the saved d16 pool;
- B1 was mixed across surfaces;
- F1 retained useful static ranking but was the slowest profile.

These are static supplied-candidate results. They do not show whether any profile can generate useful candidates from matched starts.

## Pack 02A dynamic and shell result

Pack 02A completed with 224 deterministic d16 perturbation-shell candidates and 112 timed exact-d8 search attempts.

The shell diagnostic showed a strong local gradient for every profile, but the clearest ordering was:

- `S2 WLI12`: rune-match Spearman `0.976963`, complete-word Spearman `0.975388`, and all six median shell steps monotonic towards truth;
- `S3 char12 + WLI12`: rune-match Spearman `0.973496` and all six steps monotonic;
- `F1 char1234 + WLI1234`: rune-match Spearman `0.972030` and all six steps monotonic;
- `B1 char23 + WLI23`: rune-match Spearman `0.961279`, with five of six median steps monotonic.

The exact-d8 matched pilot showed that the earlier runs were diagnostic rather than solve-length runs. The complete shell run took approximately 25 seconds and the complete matched pilot took approximately 3 minutes 6 seconds. Individual calibrated search attempts lasted approximately 0.7 to 3.5 seconds.

Dynamic results were nevertheless decisive enough to freeze roles:

- `S2` reached a median 289 of 308 rune matches under both fixed and calibrated arms, ranked its strongest candidate first and retained eight unique calibrated candidates;
- `B1` reached the same 289-rune basin and improved seven of eight calibrated starts, but its low median makes it unsuitable as a broad scout;
- `F1` reached a 289-rune median in both arms, improved six of eight starts and ranked the strongest retained candidate first;
- `J1` reached only 90 runes at best in the calibrated arm;
- `J0` found one 289-rune candidate but remained inconsistent across starts.

No exact solve was generated. Several profiles repeatedly saturated at 289 rune matches and 63 complete-word matches. Simply requesting more coordinate sweeps is not a useful long-run strategy because coordinate descent stops when a complete sweep makes no improvement. Longer work must therefore increase independent candidate supply and use the staged pool handoff rather than only extending an already-converged restart.

## Frozen Pack 02B ladder

The ladder is frozen as:

```text
scout  : S2 WLI12
bridge : B1 char23 + WLI23
judge  : F1 char1234 + WLI1234
```

Pack 02B runs `staged_d8_handoff_v1` with 96 deterministic scout starts. Every unique scout candidate enters B1. The F1 judge receives the deduplicated union of scout and bridge candidates. The final evidence surface is the deduplicated union of scout, bridge and judge candidates rescored under F1. This preserves earlier basins and prevents later-stage refinement from silently erasing them from the evidence.

Pack 02B is the last handoff-validation and runtime-calibration pass before the standard Experiment A panel. It records per-attempt and per-stage timing and projects fixed 256, 512 and 1,024-start panels plus an eight-hour capacity. It does not itself authorise an overnight run.

The intended progression is now explicit:

1. Pack 02B: staged handoff validation and runtime projection, expected to be a moderate multi-minute run rather than another seconds-long pilot.
2. Pack 03A: substantially longer standard Experiment A baseline-versus-staged panel, with a declared target of roughly one to two hours based on returned Pack 02B timing.
3. Pack 03B: eight-hour overnight Experiment A continuation only if Pack 03A demonstrates an exact solve, repeated near-truth enrichment, reliable correct-basin promotion or clear staged improvement over the fixed high-order baseline.
4. Experiment B follows after the A ladder and scaling behaviour are understood.

This inserts a separate standard and overnight A pass before candidate-list Experiment B. It does not remove or postpone B indefinitely; it applies the overnight gate already required by the governing WP6 specification.

## Pack 02B exact-solve result

Pack 02B completed `staged_d8_handoff_v1` with 96 independent deterministic
offset-206 d8 starts.

The run generated, persisted and replayed one exact plaintext, one canonical
key and one combined shift:

```text
308 / 308 rune matches
82 / 82 complete-word matches
```

The exact candidate first appeared in the truth-blind `S2 WLI12` scout and
remained score rank one in scout, bridge, judge and final-union evidence. Eight
independent scout starts converged to that same exact candidate. The first
post-hoc exact convergence occurred at scout input index 2 after approximately
1.03 seconds of that attempt.

The complete scientific run took approximately 218.18 seconds:

```text
scout       104.00 s
bridge       34.58 s
judge        75.10 s
final score   0.29 s
replay        2.14 s
terminal      0.25 s
```

The bridge generated no terminal rune-count improvements and seven regressions
across its changed candidates. The judge generated three improvements and four
regressions. The retained union prevented those later regressions from deleting
the exact scout candidate.

This closes the question of whether the frozen handoff can produce and preserve
an exact offset-206 d8 solve. It does not yet establish independent block solve
rate, comparative J0 performance or positional generalisation.

## Pack 03A standard Experiment A panel

Pack 03A runs `experiment_a_standard_panel_v1`.

The primary panel uses eight new independent blocks of 128 starts. Every block
runs:

```text
recorded J0 char34 + WLI34 baseline
versus
S2 scout -> B1 bridge -> F1 judge
```

Both arms receive identical starting vectors, equal archive capacity and equal
wall-clock ceilings. All candidate surfaces are persisted and replayed before
current-run terminal metrics are opened.

A separate positional confirmation uses four new 128-start staged blocks on the
offset-81 d8 contract.

The measured planning estimate is approximately 93 minutes centrally and about
116 minutes with the declared 1.25 safety factor. This is the first genuinely
long standard solve panel; it is not an overnight run.

Experiment A is promoted when:

- every block and replay completes deterministically;
- at least one new primary staged block solves exactly;
- at least one offset-81 staged block solves exactly.

An assisted-d8 overnight repeat is recommended only if either staged exact-block
rate is below 50 percent. Otherwise the overnight budget moves to Experiment B
candidate-branch scaling or, after B evidence, a meaningful full-d16 strategy.

## Candidate lessons awaiting promotion

CSL-007 is supported by the technical replay suite: both bound starting surfaces reproduced their stored scores and ranking without rediscovery. Promotion to a general lesson remains a milestone decision.

### Pack timing evidence

WP6 execution packs must preserve explicit UTC start/end and elapsed-time
evidence for tests, experiments, scorer profiles, search arms and individual
restart attempts. Human-readable summaries must accompany the machine-readable
logs. Timing is observational unless a later experiment predeclares a
wall-clock decision rule.

## Pack 03A completed Experiment A result

Pack 03A completed `experiment_a_standard_panel_v1` in approximately 87 minutes
24 seconds of scientific work.

All predeclared blocks completed and replayed deterministically:

```text
primary J0 exact blocks        : 1 / 8
primary staged exact blocks    : 8 / 8
offset-81 staged exact blocks  : 4 / 4
```

The exact candidate first appeared in the truth-blind `S2 WLI12` scout in all
twelve staged blocks. The result therefore establishes:

- reliable independent replication at offset 206;
- a large staged advantage over the exact recorded J0 baseline;
- positional generalisation to the equally ranked offset-81 crib;
- no scientific case for spending the next overnight budget on another
  assisted-d8 Experiment A repetition.

Experiment A is promoted. The next long-run question is Experiment B branch
identification and scaling.

## Pack 04 candidate-word branch panel

Pack 04 runs Experiment B in the governing nested sequence:

```text
B10
-> B100 only when the predeclared B10 terminal gate passes
```

The candidate lists are deterministic, nested and built from the installed
selected `raw1grams_*.csv` word/frequency assets:

- every candidate encodes to exactly eight runes;
- duplicate rune encodings collapse to one representative;
- the controlled word is included exactly once;
- list ordering does not mark or reveal its role;
- asset names, sizes and SHA-256 hashes are recorded;
- whether the controlled word occurred naturally or required insertion is
  reported only in terminal evidence.

Every branch receives the same 160 deterministic S2 starts and the same scout
budget. Eight candidates may be retained from each branch before a global
score-only selection with capacity four times the branch count. The global
selection has no one-candidate-per-branch quota. Surviving branch pools continue
under the same B1 and F1 policies, and each branch retains the deduplicated union
of scout, bridge and judge candidates.

All branch search, persistence and replay complete before the controlled branch
identity is opened.

B10 authorises B100 only when:

- all ten branches and all replay surfaces complete;
- the controlled branch survives global scout selection;
- it solves exactly or has final branch rank at most three;
- the safety-adjusted linear B100 projection fits within eight hours.

When that gate passes, B100 begins in the same pack and is the first
overnight-scale WP6 branch run. B100 branch-identification success requires the
controlled branch to survive and finish in the final top ten. That success does
not itself authorise B1000; B1000 remains a later explicit decision requiring
the complete B100 scientific and runtime evidence.

Pack 04 records UTC start/end times, total scientific duration, every
per-branch/per-stage attempt, evaluations, throughput and the B10-to-B100
runtime projection. No B1000 or full-d16 overnight run is started.


## WP6 Pack 05 — compressed B1000 scaling

Pack 04 established that B100 identifies and exactly solves the controlled
branch at rank 1, but the full 160-start budget projects to roughly 61 hours at
B1000. Pack 05 therefore makes the permitted intermediate scaling change
explicit:

1. analyse the complete saved B100 scout attempts in disjoint reduced-start
   blocks;
2. authorise B1000 only when the frozen eight-start diagnostic gate passes;
3. run 1,000 nested distinct branches with eight shared S2 starts per branch;
4. retain a global score-only pool of at most 400 candidates, with no
   per-branch quota;
5. continue surviving branches through the frozen B1 and F1 stages;
6. preserve and replay all retained stage surfaces before terminal branch
   evaluation.

This is a budget-compression experiment, not a silent reduction of Experiment
B. The full B100 evidence remains the source used to justify the new frozen
B1000 budget. B1000 does not authorise any larger list or new work package.
