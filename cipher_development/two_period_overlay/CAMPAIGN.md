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
2. `technical_canary_v1` — execute the existing tiny P13/P17 archive-handoff path and replay its bound batch.
3. `coordinate_supply_v1` — retain and diagnose every unique coordinate optimum on lower rungs before P13/P17.
4. `candidate_diversity_v1` — diagnose affine and expanded-key basin diversity without new search.
5. `candidate_selection_v1` — compare deterministic top-score and diverse-high-score selections.
6. `archive_handoff_v1` — compare selected candidates with matched independent controls.
7. `candidate_replay_v1` — verify every cross-experiment candidate surface without discovery or exploitation.

## Control arm

The same number of independently generated starts receive the same SA and coordinate-polish budgets. Comparison index `i` uses the same exploitation RNG seed in each arm. Final control candidates are retained.

## Archive-handoff arm

Each completed coordinate restart offers its optimum to a bounded archive. Selected candidates are written to self-contained bound batches, exploited and returned to the archive with parent provenance.

## Decision rule

Canaries always refine. Full comparisons also refine when candidate supply is below the declared minimum. Otherwise promote when archive wins exceed control wins and archive best is no worse; close when there are no archive wins and archive best is no better; otherwise refine.

A wall-clock safety interruption is incomplete or underpowered evidence and cannot promote or close a mechanism.

## Replay plan

Each source run writes a truth-free replay context containing the exact benchmark contract, ciphertext, WLI, crib, affine matrices, scorer contract and evaluator/model provenance.

Every batch crossing an experiment boundary has a content-addressed binding joining the source run, benchmark, configuration, context, batch and source archive. Replay verifies provenance, identity-payload agreement, affine reconstruction, benchmark membership, gauge, stored score and deterministic ranking. Replay never runs discovery or exploitation.

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

The implementation writes coordinate, handoff, final and control-final candidate artifacts and binds both starting batches. No real-RDP canary or full-run archive has yet been reviewed.

## Current result

WP1-WP5 contracts are frozen. WP6 historical compatibility has been removed and the benchmark ladder contract is being established. No scientific WP6 result is claimed.

## Closed mechanisms

None.

## Next experiment

Validate all ladder contracts with the complete RDP installation and language-model assets. Then run and review `technical_canary_v1` and replay its archive-handoff batch twice.

## Candidate lessons awaiting promotion

CSL-007 remains `candidate`: real replay must show that a bound saved candidate surface can be rescored deterministically without rediscovery.
