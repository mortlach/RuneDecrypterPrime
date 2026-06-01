# Candidate 3 closure decision note

Date: 2026-04-18

Decision:

- close candidate 3 without promotion
- do not run another broad overnight replay batch for candidate 3
- do not schedule a final narrow confirmation run
- keep the code and exact-lane tooling as analysis reference only

What candidate 3 was:

- runtime label:
  - `phaseb_topk_anchor_swap_v1`
- narrow idea:
  - reorder the saved Phase-C start surface so the first distinct
    `phaseB_topk` start is tried ahead of the retained anchor
- intended role:
  - test whether some late-region cases were being hurt by a too-sticky anchor
    ordering rather than by an upstream search failure

What exact saved-surface evidence it showed:

- whole-panel saved-start shadow:
  - `19/20` retained runs were engageable
  - `11` favored the first actual `phaseB_topk` start
  - `7` favored the retained anchor
  - `1` was equal
- full supported exact saved-surface matrix:
  - `19` total supported cases
  - `10` usable decision gates
  - `9` drifted context lanes
  - usable-gate read:
    - `3` positives
    - `6` neutrals
    - `1` negative
- clean usable positives:
  - `611/search7003`
  - `1111/search7002`
  - `1111/search7004`
- clean usable negative:
  - `1511/search7004`
- nearby local variant comparison:
  - `phaseb_topk_frontload_all_v1` was the strongest one-seed neighbor
  - but it traded extra wins for extra harms rather than dominating cleanly
- retained-seed sweep:
  - anchor-swap mean delta vs control:
    - `-0.002`
  - frontload-all mean delta vs control:
    - `+0.001`
  - frontload-two mean delta vs control:
    - `-0.003`

What candidate 3 did not prove:

- it did not prove a broad panel-wide solver improvement
- it did not prove a stable positive-control improvement on `1511`
- it did not prove live-runtime readiness
- it did not prove that the best nearby variant is robust enough to promote
- it did not remove the need for case-qualified decision gates and control-lane
  fidelity checks

Why it is being closed:

- the line is operationally closed already:
  - supported exact-lane coverage is complete
  - the nearby local variant comparison is complete
  - the retained-seed robustness sweep is complete
- the current read is mixed, small-effect, and case-dependent
- additional broad replay work is unlikely to change the decision enough to
  justify the cost
- the right next move is a new paradigm or a narrower conditioned rule, not
  more unstructured candidate3 replay work

Lesson carried forward:

- when full replay drift blocks fair judgment, the saved-surface exact lane is
  a useful case-qualified evaluation tool
- future candidates should aim for:
  - explicit conditioned mechanisms
  - stable or near-stable decision gates
  - honest separation between clean utility reads and context-only drifted lanes
- candidate3 leaves behind a methodological lesson about how to test late-order
  hypotheses, but it does not graduate as a promoted solver rule
