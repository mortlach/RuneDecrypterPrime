# Global open questions

These are cross-project questions that should be answered before the planning
migration is treated as canonical.

## G1. Exact project boundary between `rdp_v1` and `benchmark_campaign_v1_1`
The current split looks right, but some planning still mixes:
- repo-level governance
- campaign-level contracts
- support/setup streams

Need to keep `rdp_v1` about repository convergence and release truth, while
keeping benchmark execution and campaign mechanics under
`benchmark_campaign_v1_1`.

## G2. How formal should the `p13_real_ciphertext_campaign` home be at first?
A small first home is probably safer:
- current state
- problem index
- document map
- active runbook
- one log folder

Do not overbuild before the problem threads are mapped.

## G3. When should old material be moved instead of merely mapped?
The answer is probably:
- once the new project home has a stable document map
- once a live replacement exists for the old entry point
- then move the old file into legacy/completed/archive

## G4. Should completed LP-domain work get its own completed-capability home?
Probably yes, but not in the first migration slice.

## G5. Should the new timeline layer be strictly one-page snapshots?
Probably yes for project snapshots, otherwise it will become another giant log.

## G6. Which status tags should be mandatory in every active document header?
Likely minimum:
- status
- owner
- parent project
- last updated
- source-of-truth parents
