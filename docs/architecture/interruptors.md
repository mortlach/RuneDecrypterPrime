# Interruptors (Design Spec)

Status: implemented baseline for a first-class interruptor configuration and optimization path.
Scope: positions only; interruptor symbols are fixed from ciphertext (no value search).

## Goals
- Make interruptors a core, typed config (not ad-hoc fields).
- Allow flexible search behavior (fixed, ranged, brute force, heuristic) without blocking future modes.
- Keep the pipeline invariant: remove interruptors -> encrypt/decrypt core -> reinsert unchanged.
- Integrate with KeyOps so all optimizers share one robust mechanism.

## Non-goals (for now)
- No scoring changes (full-text scoring only).
- No interruptor value optimization.
- No redefinition of the core cipher pipeline.

## Proposed Config Surface
New core dataclass (name aligned to other configs):

```python
@dataclass(slots=True)
class InterruptorConfig:
    # Primary mode
    mode: str = "disabled"          # "disabled" | "exact" | "pool"

    # Exact positions (absolute indices in ciphertext/plaintext by default)
    exact: list[int] | None = None

    # Pool search
    pool: list[int] | None = None
    min_count: int = 0
    max_count: int | None = None    # default: len(pool) when pool is set

    # Index space (default is pre-transposition absolute indices)
    index_space: str = "absolute"   # "absolute" (others reserved)

    # Search strategy
    search_strategy: str = "auto"   # "auto" | "bruteforce" | "keyops"
    bruteforce_max: int = 5000      # cap on combinations before switching to heuristic

    # Reserved for future expansion (kept visible and documented)
    score_mode: str = "full"        # "full" | "core_only" | "masked"
    value_mode: str = "fixed"       # "fixed" | "override" | "optimize"
```

Defaults and rules:
- If `mode == "exact"`, `exact` is required and overrides all search settings.
- If `mode == "pool"`, `pool` is required and `min_count`..`max_count` defines the range.
- Default range is `min_count=0`, `max_count=len(pool)` when pool is set.
- `index_space="absolute"` means indices refer to the raw ciphertext/plaintext positions
  before any transposition or permutation. Other spaces are reserved and currently rejected.

## API Integration
Expose interruptor config via the public API, with a normalizer that:
- Validates uniqueness, bounds, and type.
- Applies defaults for `min_count` and `max_count`.
- Preserves `index_space` and `search_strategy` for future use.

Current implementation notes:
- API accepts `interruptors=InterruptorConfig(...)` (or a dict) and maps legacy
  `interruptors_exact/pool/max` into the new config when present.

## Search Integration
For the normal optimiser path, pooled interruptors are integrated with KeyOps so
optimisers share one search representation.

Specialised constraint solvers may resolve interruptor choices as deterministic
structural hypotheses before their key search when the chosen positions change
the mathematical problem itself. They must still use the same
`InterruptorConfig`, the same remove/core/reinsert semantics, and the same
configured pool/count bounds. They must not silently fall back to a different
search strategy or truncate the requested hypothesis space.

Representation (current):
1) Fixed-size sorted picks with a sentinel:
   - Key segment length = `max_count`.
   - `-1` marks unused slots, enabling variable counts between `min_count` and `max_count`.
   - Mutation swaps in pool values or sentinel, then normalizes (unique + sorted + padding).

Reserved (future):
2) Bitmask over pool:
   - Could represent variable counts more compactly for very large pools.

Normalization rules:
- Always return sorted, unique indices.
- Enforce min/max count (drop or add elements deterministically).
- Convert pool indices to absolute indices at the final split point.

## Search Strategy
When `search_strategy="auto"`:
- If total combinations across `min_count..max_count` are <= `bruteforce_max`,
  expand interruptor positions exhaustively per-position (beam-style).
- Otherwise fall back to KeyOps mutation/recombination with a capped expansion.

This is configurable to prevent runaway search space growth.

Specialised constraint routes may reject the KeyOps fallback when it cannot
preserve that route's mathematics. In that case `auto` must fail clearly once
the exhaustive combination count exceeds `bruteforce_max`; an explicit
`bruteforce` request may opt into exhaustive structural enumeration.

## Pipeline Impact (Default)
Index space defaults to pre-transposition absolute indices. If a full-text permutation
is configured, interruptor indices are interpreted in the pre-permutation space and
mapped before removal.
1) Remove interruptors at absolute indices.
2) Transpose core if configured.
3) Decrypt/encrypt core.
4) Undo transposition.
5) Reinsert interruptors unchanged at their original positions.

TODO: Document the conversion rules for `index_space="core"` and
`index_space="post_permutation"` once the permutation pipeline is formalized.

## Implementation Touchpoints (Planned)
- `src/rdp/core/config/interruptor.py`
  Define `InterruptorConfig` and its validation rules.
- `src/rdp/core/config/cipher.py`
  Add `interruptors_cfg: InterruptorConfig | None` and map legacy fields.
- `src/rune_decrypter_prime/api/run.py`
  Accept interruptor config and pass to pipeline.
- `src/rune_decrypter_prime/api/normalize.py`
  (not required; config validation lives in core)
- `src/rdp/core/problem/runtime.py`
  Resolve interruptor indices, split key, and pass to decrypt.
- `src/rune_decrypter_prime/keyops/*`
  Add a KeyOps family or composite mechanism for interruptor selection.
- `src/rune_decrypter_prime/solvers/solver_base.py`
  Optional hooks for brute-force expansions when enabled.
- `docs/architecture/interruptors.md`
  (this document) as the canonical design reference.

## Compatibility Notes
Existing fields (`interruptors_exact`, `interruptors_pool`, `interruptors_max`)
map into the new config so old scripts keep working. Legacy pool/max are treated
as fixed-count (min=max); use `InterruptorConfig` for ranged counts.

## Tests (Coverage)
- Unit: normalize/validate interruptor configs.
- Integration: exact positions and pooled search (including sentinel for variable count).
