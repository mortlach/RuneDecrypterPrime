# Scoring Contract and ECDF Asset ABI (RDP) - vNext draft

Status: Draft for review (rewrite per January 2026 decisions)

## Purpose
Define a strict, reproducible scoring contract and ECDF asset ABI that matches
the LMPrime pipeline and prevents silent drift. This is an enforceable spec:
hard-fail on mismatches, no aliasing, no implicit repairs.

## Scope
- PCT/ENERGY scoring semantics and ECDF assets.
- Other objectives (avg/neglogp) may use different windows, but must declare
  their window definition explicitly in telemetry and docs if ECDF-backed.

---

## 1) Terminology and naming

### 1.1 Window semantics
win means W = number of n-grams per window (not rune count).

For a given n-order:
- NOSE rune span: L_n = W + n - 1
- WISE rune span: L_n = W + n + 1 (includes start/end tags)

Within each window, the number of evaluated n-grams is:
- NOSE: ngrams_total = W
- WISE: ngrams_total = W + 2 and ngrams_interior = W

Short text:
- If T < L_max:
  - return pct = ecdf_clamp_min
  - return energy = -log(1 - ecdf_clamp_min)
  - n_windows = 0
- No ECDF lookup occurs in this case.

### 1.2 "Raw" is forbidden language
The word "raw" MUST NOT be used in any scoring identifier, telemetry key, or
public label, because it is ambiguous.

### 1.3 Statistic names (unambiguous)
For each stat in {logp, zsum, madsum} and a given
(channel, direction, se_mode, n, W):

- {stat}_sum_total
  Sum of per-n-gram contributions across all evaluated n-grams in the window.

- {stat}_mean_per_ngram_total
  {stat}_sum_total / ngrams_total

For WISE only, also define:
- {stat}_sum_interior
  Sum across interior evaluated n-grams only (excludes the first and last).

- {stat}_mean_per_ngram_interior
  {stat}_sum_interior / ngrams_interior

### 1.4 ECDF mapping names
ECDF mapping operates on a specific statistic value (usually a mean per n-gram):

- pct_{stat}_mean_per_ngram_total = ECDF({stat}_mean_per_ngram_total)
- energy_{stat}_mean_per_ngram_total = -log(1 - clamp(pct_{stat}_mean_per_ngram_total))
  ENERGY is an upper-tail transform: higher percentile -> higher energy.

For WISE, interior variants also exist:
- pct_{stat}_mean_per_ngram_interior
- energy_{stat}_mean_per_ngram_interior

### 1.5 Objective naming (machine id + human label)
Every objective MUST have:
- a stable machine id (no spaces, no "raw")
- a human label (readable English)

Example machine ids:
- avg.logp.mean_per_ngram_total.W10.n4.char.ltr.nose
- pct.madsum.mean_per_ngram_total.W10.n4.char.ltr.nose
- energy.zsum.mean_per_ngram_interior.W10.n4.char.rtl.wise

Example human labels:
- "Average log probability per n-gram (total), W=10, n=4, char, ltr, nose"
- "Percentile of MAD-sum per n-gram (total), W=10, n=4, char, ltr, nose"
- "Energy of Z-sum per n-gram (interior), W=10, n=4, char, rtl, wise"

---

## 2) Multi-n evaluation and alignment rule

### 2.1 Start-index aligned max-span windowing
For a multi-n score using n_set = {n1, n2, ...}:

1) Compute L_n for each n using the window semantics above.
2) Define L_max = max(L_n over n_set).
3) Define windows by start index i:
   i in [0, T - L_max], stepping by stride_runes (default 1)
4) For each n, the window slice is pt[i : i + L_n].

All n values for a given i are part of the same aligned window.

This rule MUST be used for all multi-n objectives so that:
- the set of start indices is shared across n
- window counts are identical across n
- telemetry and benchmarking remain stable

### 2.2 WISE tagging contract (explicit)
For WISE mode, inputs to the language model MUST include the agreed start/end tags,
and the scorer MUST clearly state whether tagging occurs:

- Caller-provided tags (strict): the scorer validates start/end tags are present.
OR
- Scorer-injected tags (explicit): the scorer inserts tags and records
  tags_injected=true in telemetry.

The policy MUST be declared and tested. Silent "sometimes tagged, sometimes not"
behavior is not allowed.

---

## 3) ECDF asset ABI and dtype boundaries

### 3.1 ECDF file format
Each ECDF asset is a .npz containing:
- grid : float64, shape (K,)
- q : float64, shape (K,)
- meta_json : UTF-8 JSON string containing required metadata

### 3.2 Canonical on-disk dtype and validation (hard fail)
Canonical ECDF assets are float64 on disk.

At runtime, the loader MUST hard-fail if any of the following are not true:
- grid.dtype == float64
- q.dtype == float64
- grid strictly increasing (no ties)
- q strictly increasing (no ties)
- 0.0 <= q[0] < q[-1] <= 1.0
- Clamp range is within the ECDF representable range:
  q[0] <= ecdf_clamp_min and ecdf_clamp_max <= q[-1]

No runtime "repair" or "nudging" is permitted.

### 3.3 Working dtype for compute (explicit boundary)
Compute backends MAY use float32 for performance (especially GPU), but this MUST
be an explicit derived representation:

- grid32 = grid64.astype(float32)
- q32 = q64.astype(float32)

The scorer MUST declare in telemetry:
- ecdf.disk_dtype = float64
- ecdf.canonical_dtype = float64
- ecdf.compute_dtype = float32 (if using derived float32 buffers)

Important: if a float32 derived representation is used for interpolation, the
implementation MUST validate that grid32 remains strictly increasing. If it does
not, the scorer MUST either:
- fall back to float64 interpolation, OR
- hard-fail (depending on configured policy).

### 3.4 Interpolation and clamp behavior (ABI-defined)
- Interpolation method is linear interpolation on the ECDF grid.
- Out-of-range handling:
  - below grid[0] -> q = 0.0
  - above grid[-1] -> q = 1.0
- Note: these are conventional extrapolations; the clamp policy defines the
  final returned range.
- Percentiles are then clamped to [ecdf_clamp_min, ecdf_clamp_max] before any
  energy transform.
- Clamp constraints (ENERGY):
  0 < ecdf_clamp_min < ecdf_clamp_max < 1.0
- Energy transform is:
  energy = -log(1 - pct_clamped)
  where pct_clamped is in (0,1) by construction of the clamp range.

### 3.5 Required metadata (meta_json, hard-checked)
These MUST match runtime configuration to load:
- model: "char" | "wli"
- direction: "ltr" | "rtl"
- se_mode: "nose" | "wise"
- n: 1..4
- stat: "logp" | "zsum" | "madsum"
- win_ngrams: W
- window_def:
    - win_ngrams: W
    - span_formula: "nose: L_n = W + n - 1; wise: L_n = W + n + 1"
    - start_index_rule: "i = 0 .. T - L_max; L_max = max_n L_n"
    - tags: "wise uses [29]... [30], nose has no tags"
    - tags_start_id: 29
    - tags_end_id: 30
- smoothing:
    - kind: "none" | "lidstone" | "jeffreys" | "auto_gt"
    - alpha: float (required even if 0.0)
- oov_policy: "floor_min_seen" | "lidstone"
- mesh:
    - kind: "linear" | "logistic" | "custom"
    - params: object (e.g., {"a": 6.0})
    - num_knots: integer K
    - custom_mesh_id: string (required if kind == "custom")
- strict_increasing:
    - enforce: true
    - method: "nextafter" | "epsilon"
- tie_policy:
    - description of how duplicate quantiles are nudged to enforce strict grid
    - note: this policy is applied by the ECDF builder; runtime does not apply it
      and will hard-fail if ties exist
- ecdf_canonical: true

### 3.6 File layout and naming (strict)
Index patterns must resolve to:
  ecdf/<model>/<direction>/<direction>_<se>_<model>_n<N>_win<W>_<stat>.npz

Only "ltr" or "rtl" may appear in paths.

### 3.7 Runtime validation (hard-fail)
Runtime MUST fail to load if any of the following are true:
- direction not in {"ltr","rtl"}
- grid or q are not float64
- grid is not strictly increasing
- q is not strictly increasing or not within [0.0, 1.0]
- clamp range is not within [q[0], q[-1]]
- meta_json missing or malformed
- any required meta_json field missing
- any required meta_json field mismatches runtime config
- win_ngrams does not match requested W
- smoothing/oov/alpha mismatch
- no ECDF asset exists for the requested bucket (direction/se/model/n/W/stat)

---

## 4) Telemetry contract (stable and human-readable)

Telemetry MUST include the following keys (names exact):

Legacy telemetry keys containing "raw" (e.g., raw_score_mean) are prohibited and
must be removed; consumers must migrate to the explicit names in this spec.

### 4.1 Window definition
- window.win_ngrams (int, W)
- window.se_mode ("nose" | "wise")
- window.n_set (list[int])
- window.stride_runes (int)
- window.L_n (map n -> L_n)
- window.L_max (int)
- window.n_windows (int)

### 4.2 Statistic definition
- stat.name ("logp" | "zsum" | "madsum")
- stat.variant ("mean_per_ngram_total" | "mean_per_ngram_interior")
- stat.ngrams_total (int) and (WISE) stat.ngrams_interior (int)
Enabled stat = any stat that the active objective requests or computes
(e.g., logp/zsum/madsum).
For se_mode="wise":
- The scorer MUST compute and emit summary statistics for both total and interior
  variants for each enabled stat.
- Per-window arrays for total/interior are emitted only when diagnostics are
  explicitly enabled.

### 4.3 ECDF asset and dtype boundary
- ecdf.asset_id (string stable identifier)
- ecdf.asset_fingerprint (string)
- ecdf.disk_dtype ("float64")
- ecdf.canonical_dtype ("float64")
- ecdf.compute_dtype ("float32" or "float64")
- ecdf.meta_hash (string)
- ecdf.meta_json (string) ONLY when diagnostics are enabled
- ecdf.interp ("linear")
- ecdf.interp_dtype ("float32" or "float64")
- ecdf.clamp_min, ecdf.clamp_max (float)

### 4.4 Direction strictness
Telemetry MUST use only:
- direction = "ltr" | "rtl"

Any appearance of fwd, rev, forward, reverse in telemetry is a contract violation.

### 4.5 Human label
- objective.id (machine id)
- objective.label (human label)

---

## 5) Transitional note (why we are doing it this way)
Historically, the runtime cast ECDF grids and quantiles to float32 on load for
convenience, but this can silently break strict monotonicity when the canonical
ECDF is built in float64 using fine-grained steps. This led to confusing behavior
and undermined deterministic benchmarking.

To fix this with minimal disruption:
- Keep canonical ECDF assets in float64 with hard validation.
- Explicitly derive float32 working buffers for GPU compute when needed.
- Record the dtype boundary in telemetry.

A future improvement may add an offline diagnostic tool to quantify how often
float64 -> float32 conversion introduces ties for a given asset set, but the
runtime will not silently "repair" assets.

---

## 6) Operational defaults and supported buckets
- W=10 is the typical operational bucket for PCT/ENERGY.
- Shipped ECDF assets MAY include only W=10 initially.
- Runtime MAY require W=10 for PCT/ENERGY until additional assets exist.

---

## 7) Non-goals
- No runtime ECDF repair.
- No direction aliasing within the ABI / core runtime. UI layers MAY accept
  legacy synonyms (forward/reverse/fwd/rev) but MUST canonicalise to ltr/rtl
  before asset resolution, scoring, or telemetry. Synonyms MUST NOT appear in
  telemetry, asset paths, ids, or tests.
- No hidden fallback to old win semantics.
