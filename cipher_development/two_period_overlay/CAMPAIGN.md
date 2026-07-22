# Two-period overlay campaign

## Problem

Solve a 308-rune additive P13/P17 overlay benchmark with the complete word `uncomfortable` fixed at rune offset 188.

## Frozen benchmark contract

- alphabet: 29 runes;
- periods: 13 and 17;
- schedule: full overlay;
- gauge: `B[0] = 0`;
- affine free dimension: 16;
- normal evidence: full WLI;
- decision scorer: `pct.logp.win10` with character and WLI 3/4-grams;
- benchmark truth: terminal evaluation only.

## Frozen historical baseline

The seven-hour `two_period_crib_solver_runner.py` remains untouched. Its runner has been located and its contract verified. The completed `latest_result.json` has not yet been supplied, so the baseline-import function is implemented but no historical ledger entry is claimed yet.

## Evidence mode

`with_wli` is the normal mode.

## Truth policy

`benchmark_only`. Search code receives ciphertext, WLI, the crib, the affine key space and the scoring callback. Plaintext and the benchmark key remain in a separate terminal reference object.

## Current failure classification

Candidate supply, handoff and exploitation.

## Scientific question

Does preserving and handing forward a full-WLI-ranked archive of coordinate-search candidates outperform independent exploitation starts?

## Hypothesis

Useful coordinate basins are being found and discarded between independent methods.

## Strongest alternative

Coordinate discovery never reaches useful candidate regions, so archive handoff will not improve exploitation.

## Control arm

The same number of independently generated starts receive the same SA and coordinate-polish budgets. Comparison index `i` uses the same exploitation RNG seed in both arms.

## Archive-handoff arm

Each completed coordinate restart offers its optimum to a capacity-64 archive. The best configured candidates are written to a self-contained handoff batch, exploited, and returned to the archive with their source candidate as parent provenance.

## Fixed comparison rule

Promote when archive wins exceed control wins and the archive best is no worse. Close when there are no archive wins and the archive best is no better. Otherwise refine. Canary runs always refine.

## Candidate identity

The full expanded, gauge-fixed key. Payloads also retain the affine variables required for replay.

## Candidate archive policy

- capacity: 64;
- decision score: `wli_decision_score`;
- higher is better;
- no family cap in the first experiment.

## Current result

Implementation and deterministic pure-contract canary are ready for validation. The campaign is split only at real boundaries: pure keyspace/search, benchmark/reference construction and the executable wrapper. No scientific result is claimed.

## Closed mechanisms

None yet.

## Next experiment

Run and review the committed canary on a full RDP checkout. Only then approve the bounded full paired experiment.
