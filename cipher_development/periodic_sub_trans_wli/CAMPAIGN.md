# Periodic substitution and columnar WLI-ranking campaign

## Problem

Test whether full-WLI reranking improves handoff from one deterministic periodic-columnar seed pool into the existing Kaeding solver.

## Fixed benchmark panel

- positive control: P7/C5/L400;
- target: P13/C13/L300;
- order: `col_then_sub`;
- alphabet: 29 runes;
- canary: one case from each family;
- full panel: both families, text-offset hints 0 and 211, truth-key seeds 111 and 222.

Each text sample is resolved to an exact whole-word slice over a deterministically tiled RDP source, and its actual source offset is recorded.

## Cipher and key contract

The campaign uses RDP's existing `periodic_columnar` wrapper, structured key plan, seed generator and Kaeding solver. Candidate keys contain `period × 29` substitution values followed by a column permutation. Existing RDP permutation validation is authoritative.

## Evidence mode

`with_wli` is the normal mode. Hard crib is disabled.

## Truth policy

`benchmark_only`. Search-visible cases contain ciphertext, WLI, dimensions and execution callables. Plaintext and the deterministic benchmark key remain in a separate terminal reference object.

## Scientific question

Does full-WLI reranking of a fixed periodic-columnar candidate pool produce better downstream solutions than ranking the same pool by the raw character seed score?

## Hypothesis

Useful candidates are generated, but raw seed ranking fails to hand off the most exploitable structured keys.

## Strongest alternative

The candidate supply itself is inadequate, so changing ranking policy will not improve downstream exploitation.

## Candidate-supply policy

Generate one deterministic pool per case, validate and deduplicate it, calculate both named scores, and retain it in a capacity-64 WP2 archive. Both ranking policies consume that exact canonical pool.

## Raw-ranking control

Select by `seed_raw_score`, using candidate ID as the final deterministic tie-breaker.

## WLI-ranking arm

Select by `wli_decision_score`, using the WP2 archive's deterministic ranking.

## Exploitation contract

Selected candidates receive identical full-WLI Kaeding settings. Solver seeds depend only on benchmark ID, candidate ID, replicate and the campaign master seed. Candidates selected by both policies are executed once and their exact result is reused in both arm summaries.

Both final arms are persisted as candidate archives with parent provenance. The terminal best candidate ID, membership and containing artifact are recorded.

## Decision rule

Canaries always refine. Full panels also refine when candidate supply is short or the two ranking policies do not provide the configured minimum exclusive candidates. A valid panel promotes when WLI ranking wins more target cases than it loses without positive-control regression; it closes when no target case improves; otherwise it refines.

## Current result

Implementation only. No scientific result is claimed until the committed real-RDP canary and normal repository CI pass.

## Closed mechanisms

None.

## Next experiment

Run the committed canary with the full language-model assets, review candidate supply and policy overlap, then freeze the full-panel solver budget before any expensive run.

## Generality evidence

WP4 reuses WP1 experiment evidence and WP2 archive/replay contracts unchanged for a matrix-and-permutation key, providing a materially different second campaign after WP3's affine two-period overlay.
