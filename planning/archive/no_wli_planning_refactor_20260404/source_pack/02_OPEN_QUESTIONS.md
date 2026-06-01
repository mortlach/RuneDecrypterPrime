# Open questions

## P0 — immediate science questions

### 1. Hard-seed repeatability
Question:
- Does the `411` hard-family shape repeat on a fresh hard seed, especially
  `p9/c3 seed611`?

Why it matters:
- This is the main missing evidence for seed taxonomy.
- It decides whether the current hard-case story is one-family-specific or more
  general.

Needed evidence:
- one fresh `v62` artifact
- `space_map_v1` comparison against `seed411`

### 2. Where does the good hill disappear on fresh hard seeds?
Question:
- On a fresh hard seed, does the useful family vanish at:
  - `stage2_promoted`
  - `stage3_prep`
  - `phaseC_pool`
  - `phaseC_start`
  - `stage35_seed`
  - or only at Stage 3.5 admission?

Why it matters:
- This is the main point of the new space-map chain.

Needed evidence:
- fresh current-code artifact with full `space_map_v1`
- atlas readout on boundary-by-boundary family counts and continuity

## P1 — active but secondary science questions

### 3. Late dump/stop calibration
Question:
- Can family-aware late dump rules separate true near-solves from false
  friends strongly enough to justify an offline shadow rule?

Current rule:
- offline only
- dump and stop must stay separate
- no live policy promotion from this pass alone

Needed evidence:
- tiny panel readout from `score_stop_shadow_v2`

### 4. How much of the Stage 3 prep graph is real?
Question:
- Are Stage 3 prep parent links informative enough for hill-connectivity claims,
  or are they still too dominated by fallback-to-anchor scaffolding?

Needed evidence:
- fresh map inspection
- explicit review of `parent_link_kind`

## P2 — deferred until the above are clearer

### 5. Broad promotion criteria
Question:
- What would count as enough evidence to promote the bounded
  `score_plus_novelty + beam_width_1` lane beyond one hard family?

Current answer:
- not yet decided
- not yet close

### 6. Whole-run stop policy
Question:
- Can any non-oracle stop signal safely terminate a whole run, not just dump a
  late candidate or stop a late continuation lane?

Current answer:
- no active live policy
- treat as later than dump/lane-stop science

## Engineering / log-space open items

### 7. Stage 3 prep ancestry fidelity
- still provisional
- should remain explicitly caveated in all map interpretation

### 8. Atlas automation
- extractor exists
- not auto-run after every solve yet

### 9. Planning/log hygiene
- full logs should stay append-only
- short top-layer docs must be maintained actively
