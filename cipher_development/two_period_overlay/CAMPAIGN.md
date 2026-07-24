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
10. `candidate_replay_v1` — verify every later cross-experiment candidate surface without discovery or exploitation.


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

The benchmark-contract, technical infrastructure, lower-rung candidate-supply, diversity, selection, matched-exploitation and P13/P17 target-supply gates are closed.

P13/P17 coordinate candidate supply is not currently limiting: both seed blocks met their unique-candidate thresholds and the combined pool is broad. The best WLI-ranked target candidate was not an exact solve and matched only 26 runes and one complete word terminally. That single best-candidate result is insufficient to determine whether the full WLI ordering is useful or whether ranking is the next failure mechanism.

The next gate therefore replays and terminally diagnoses the entire 64-candidate target surface without exposing candidate-specific truth mappings.

## Closed mechanisms

- inadequate coordinate candidate supply on the d4 and d8 rungs;
- coordinate-basin diversity collapse on the d4 and d8 rungs;
- loss of selected d8 candidates to unmatched independent starts under the tested exploitation budget;
- inadequate coordinate candidate supply in the first bounded two-block P13/P17 panel;
- coordinate-basin identity collapse across the first two P13/P17 seed blocks.

The top-WLI versus diverse-high-WLI policy comparison remains open. The tested short-SA operator did not improve established d8 coordinate optima. WLI ranking quality on the complete P13/P17 pool remains open.

## Next experiment

Run `target_ranking_diagnostic_v1`. Replay all 64 saved P13/P17 candidates twice, verify stored scores and ranking, then compute only aggregate terminal diagnostics for WLI score versus rune matches, complete-word matches and affine-variable matches. Do not emit candidate-specific truth mappings and do not run discovery, selection, mutation, SA or handoff.

## Candidate lessons awaiting promotion

CSL-007 is supported by the technical replay suite: both bound starting surfaces reproduced their stored scores and ranking without rediscovery. Promotion to a general lesson remains a milestone decision.
