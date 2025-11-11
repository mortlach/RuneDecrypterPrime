[Tutorial script]
  run.solve(text=..., cipher=..., key=..., solve=...,
            device="cpu", scorer="rune", scorer_params=... )
          |
          v
[ui/api.py]
  - normalize text → (ct, wli)
  - cipher spec → CipherConfig via _build_cipher_config_wrapper(...)
  - assemble RunConfig
          |
          v
[core/solver_engine.py]
  engine = RuneSolverEngine(cfg)
    ├─ build_cipher(cfg.cipher)        -> cipher instance
    ├─ build_scorer(cfg.cipher, s_cfg) -> (see below)
    └─ problem = DecryptionProblem(...)
          |
          v
build_scorer(c_cfg, s_cfg):
  - impl = (s_cfg.impl or "auto")
  - device_req = (c_cfg.device or "cpu")
  - impl == "numpy" → return RuneScorer(c_cfg, s_cfg)
  - impl == "auto" and device_req not "cuda"/"torch" → RuneScorer
          |
          v
[scoring/rune_scorer.py]
  RuneScorer.__init__(cfg, s_cfg)
    ├─ s_cfg normalized (_normalize_scfg)
    ├─ derive orders, windowing, weights, objective
    ├─ self._rt = LmPrimeRuntime(...)
    │     (loads char/wli n-gram tables + ECDF from disk)
    └─ self._ecdf = self._rt.ecdf



data structures and flow !!! oh my

```
[rune string + spaces]
      │
      ▼
ui.api.normalize  →  pt: uint8[ L ]    wli: uint8[ L,2 ]    (indices 0..28)
      │
      ▼
RuneScorer / RuneScorerTorch
  └─ LmPrimeRuntime(...)  →  load LM assets (char & WLI, ECDF) for direction
      │
      ▼
windowing (win=10, stride=1)
  pt_w:  list of uint8[10]
  wli_w: list of uint8[10,2]   (or None if disabled)
      │
      ▼
per-window scoring (n-gram tables)
  → window stats (logp / zsum / madsum) per active model
  → ECDF percentiles (0..1) for “pct.*” objectives
      │
      ▼
mix across models (char + WLI, weights normalized)
      │
      ▼
mean across windows  →  scalar score in [0,1]
```

---

# step-by-step (with the real code touchpoints)

## 1) tutorial input → indices

You hand the solver a **rune string with spaces**:

```python
sol = run.solve(text=ct_runes, ..., scorer="rune", scorer_params={...})
```

Inside `ui/api.py`:

* the text is **normalized** into:

  * `pt`: `np.uint8` vector of rune indices in **\[0..28]** (letters only),
  * `wli`: `np.uint8` matrix **shape (L,2)** giving *Word Length Index* info (spaces/word breaks).
* if you pass `wli_data` explicitly, it uses that; otherwise it reconstructs `wli` from spaces in `text`.

So at scorer time you have:

* `pt: np.ndarray(dtype=uint8, shape=(L,))`
* `wli: np.ndarray(dtype=uint8, shape=(L,2))` **or** `None`

## 2) scorer selection & LM bootstrap

In `core/solver_engine.py → build_scorer(...)`:

* If `scorer_params.impl == "numpy"` → **`RuneScorer`** (CPU).
* If `impl == "torch"` or `device` is torch/cuda and available → **`RuneScorerTorch`**.
* If `impl == "unified"` → **`UnifiedRuneScorer`** (wraps one of the above).
* Otherwise “auto” uses device hints.

In **`RuneScorer.__init__`** ():

* The config is normalized (`_normalize_scfg`), giving:

  * `objective` (e.g., `"pct.logp.win10"`)
  * `n_char`, `n_wli` (orders, typically 1..3)
  * `win=10`, `stride=1`
  * `include_char`, `use_word_breaks`
  * pair weights or per-order weight maps
  * `direction` (normalized to `"ltr"` or `"rtl"` using `_norm_dir`)
* Then it constructs:

```python
self._rt = LmPrimeRuntime(
    root=s_cfg.model_root,    # optional override
    smoothing=s_cfg.smoothing,
    alpha=float(s_cfg.alpha or 0.0),
    oov_policy=s_cfg.oov_policy,
    include_char=bool(s_cfg.include_char),
)
self._ecdf = self._rt.ecdf
```

→ **This is where LM assets are loaded** (see next step).

## 3) LM assets (files & structures)

In **`scoring/language_model_prime_runtime.py`** (runtime loader):

* functions like `load_char_probs(order=1..4, direction="ltr"/"rtl")`,
  `load_wli_probs(order=1..4, direction=...)`, and `load_ecdf(...)` pull tables from:

```
rune_decrypter_prime/data/language_model/
  lmp/char/{fwd,rev}/...    # character n-gram tables
  lmp/wli/{fwd,rev}/...     # WLI n-gram tables
  ecdf/char/{fwd,rev}/...   # ECDFs (for percentile mapping)
  ecdf/wli/{fwd,rev}/...
```

**Encoding & dtype** (typical; matches how you use them):

* Tables are stored in `.npz` (NumPy) with **float32** arrays of **log-probabilities** (or smoothed values).
* Rune alphabet is **size 29**, indices 0..28. All arrays are aligned to that indexing.
* ECDF assets contain precomputed empirical CDF info to map a raw statistic (e.g., mean logp) → **percentile** in **\[0,1]**.

Internally, `LmPrimeRuntime` keeps these as numpy arrays and exposes scoring helpers the scorers call. (Torch scorer will convert the loaded arrays to torch tensors on the chosen device, but the *source data* is the same.)

> If you enable the little debug prints we discussed, you’ll see the exact filenames as they’re loaded.

## 4) windowing

Back in **`RuneScorer`**:

* `_windows(pt, wli)` builds **overlapping windows** of length `win` (default 10), stride 1:

  * `pt_w`: `List[np.uint8[win]]`
  * `wli_w`: `List[np.uint8[win,2]]` (or `None` if WLI disabled)
* If `L < win`, it returns empty windows (score becomes degenerate).

## 5) per-window n-gram scoring

For each window:

* Determine **active models** via `_active_models(use_wli_now)`:

  * char channel models: e.g., `(channel="char", n=self._n_char, weight=self._w_char)`
  * wli channel models: e.g., `(channel="wli",  n=self._n_wli,  weight=self._w_wli)`
  * If you supply `char_weights`/`wli_weights` dicts, they select/weight multiple orders (1..4). Otherwise the single order (`n_char`/`n_wli`) is used.
  * Weights are **L1-normalized** to sum to 1 across the active set.

Each active model computes per-window summary stats—`logp`, `zsum`, `madsum`—using the runtime tables. The scorer then:

* Packages those stats in a `bucket_out` dict with families like:

  * `"avg"`: raw averages over the window (e.g., mean logp)
  * `"pct"`: **ECDF percentiles** of those stats (0..1), computed via `self._ecdf` lookups
* The objective selector `_extract(bucket_out, objective)` picks the correct array:

  * e.g., for `"pct.logp.win10"` it picks the **percentile of mean logp** for each model/window.

**lookups:**
The actual n-gram lookup is table-driven using the window’s rune indices. You don’t have to manage shapes: the runtime exposes a direct “score this window” path and returns the per-window aggregate (logp/z-stats). Then ECDF maps it to a percentile.

## 6) mix models → one value per window

* For that window, take each active model’s value (after `_extract`) and mix them with the normalized weights from `_active_models(...)`.

  * e.g., `score_win = w_char * val_char + w_wli * val_wli`
* This leaves you with **one scalar per window**, already in \[0,1] for `pct.*` objectives.

## 7) aggregate windows → final score

* Average across all windows:

  * `score = mean(score_win for all windows)`
* Result: **scalar in \[0,1]** (for `pct.*`), which the optimiser maximizes.

Telemetry (that you can print from `sol.meta["telemetry"]`):

* `scorer.impl` (`"numpy"`/`"torch"`), `scorer.device` (`"cpu"`/`"cuda:0"`),
* `scorer.direction` (`"ltr"`/`"rtl"`),
* `orders` used,
* `win`, `stride`, ECDF clamps, etc.

---

# small “how to inspect” snippet (for tutorials)

After `sol = run.solve(...)`:

```python
t = sol.meta.get("telemetry", {})
print("impl:",   t.get("scorer", {}).get("impl"),
      "device:", t.get("scorer", {}).get("device"),
      "dir:",    t.get("scorer", {}).get("direction"),
      "orders:", t.get("scorer", {}).get("orders"),
      "win:",    t.get("win", 10))
```

If you enabled the debug prints near `LmPrimeRuntime` and the loaders, you’ll also see **exact file paths** for each table as they’re loaded.

---

## mental model TL;DR

* **files:** `.npz` tables (1–4-gram) + ECDFs; direction-specific (`fwd`/`rev`), channel-specific (char/WLI), aligned to **rune indices 0..28**.
* **windows:** split plaintext indices into fixed-size overlapping windows.
* **stats:** compute per-window **mean logp** (and friends) via table lookups.
* **percentiles:** map those raw stats into \[0,1] using **precomputed ECDFs**.
* **mix & mean:** blend char/WLI (and per-order) with weights, then average across windows.
* **output:** a single scalar “language-likeness” score the optimiser tries to maximize.

that’s the full pipeline from disk → score, matching the classes and helpers you’ve been using.
