# Dependency map

This file records the main cross-project dependencies.

## Active-project dependency summary

### `no_wli`
Depends on:
- none as a planning template

Provides to others:
- upstream solver-learning stream
- method-development evidence
- pattern/template for planning structure

### `rdp_v1`
Depends on:
- code/test cross-check against the live repo bundle
- lessons from `no_wli` where they affect release-shaping and boundary truth

Provides to others:
- repo-level convergence and boundary decisions
- release-level control layer for what belongs in v1 vs later

### `benchmark_campaign_v1_1`
Depends on:
- current benchmark code/tests
- some repo-level rules clarified by `rdp_v1`

Provides to others:
- general campaign/benchmark discipline
- p13-learning in the general case
- setup/scoring/refactor support streams for benchmark work

### `p13_real_ciphertext_campaign`
Depends on:
- upstream no-WLI method-development
- solve-proof support machinery
- benchmark/campaign discipline where relevant

Provides to others:
- real-ciphertext frontier status
- problem-thread evidence and transfer questions

## Reference-home dependency summary

### `completed/lp_domain`
Provides:
- completed LP-domain capability context
- transcript/API background for real-ciphertext work

### `legacy/v1_old_active_index`
Provides:
- historical execution context for migration only

### `archive/phased_refactor_and_review`
Provides:
- preserved background on older planning/review phases

## Working rule

When in doubt:
- read dependencies from top to bottom
- do not let downstream problem-thread notes overwrite upstream method truth
- do not let old legacy/archive material silently override the active homes
