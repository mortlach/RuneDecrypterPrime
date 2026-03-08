# Hamming Scorer (lexical shaping)

Audience: Hands-on / Expert  
Time: 4–6 minutes  
Outcome: Know how the Hamming component loads wordlists, computes penalties, plugs into the LM scorer, and how to tune/avoid conflicts.

---

## What it is
- Optional scorer term that penalises plaintext words not close to any real word in the rune vocabulary.
- Implemented in C++ (`scoring/hamming/_hamming`) with a thin Python wrapper (`HammingBackend`).
- Purely a **shaping** signal: subtracts an average per-word Hamming distance from the LM percentile score.

---

## Data source
- Uses `raw1grams_XX.csv` (selected rows only) from `assets/hamming_raw_1g/` by default.
- Loader: `scoring/hamming/loader.py::load_raw1grams_wordlists(wordlist_dir=None, build_rtl=False, require_selected=True)`  
  returns `(wordlists_ltr, wordlists_rtl)` mapping `word_length -> [[rune_idx...]]`.
- `WordCribConfig` helper: `data/wordlists/loaders.py::load_word_crib_config_from_raw1grams(...)` builds short-word dicts from the same source so CSP and Hamming stay consistent.

---

## Backend behaviour
- `HammingBackend(wordlists_ltr, wordlists_rtl=None, max_hd, length_weights)`
  - Splits plaintext by WLI into words.
  - For each word, finds min Hamming distance to the dictionary of that length; applies optional length weight.
  - `max_hd` short-circuits accumulation (cap cost on very bad plaintexts).
  - If a length is missing from the dictionary, it falls back to a full-mismatch cost (no crash).
  - `total_min_hd_stats(...)` returns `{"total_hd", "avg_hd_word", "n_words"}`; `avg_hd_word` is used for scoring.
- Direction:
  - `direction="ltr" | "rtl"` chooses the matching dictionary.
  - `mode="both"` takes `min(ltr, rtl)` when both are available.

---

## Scorer integration
- In `rune_scorer.py` / `torch_rune_scorer.py`:
  - Controlled by `ScoringConfig` fields:
    - `hamming_enabled` (bool) or `hamming_weight` (float)  
    - `hamming_weight_max`, `hamming_ramp_start_frac`, `hamming_ramp_end_frac` (anneal)  
    - `hamming_max_hd`, `hamming_length_weights`, `hamming_direction_mode` ("match"|"both")  
    - `hamming_wordlist_dir` (defaults to packaged data), `hamming_build_rtl` (to load RTL dictionary)
  - If enabled and the extension is available, scorer subtracts `hamming_weight * avg_hd_word`.
  - Telemetry exposes `hamming_total_hd`, `hamming_avg_hd`, and `hamming_weight`.
- Annealing: solvers call `set_hamming_progress(progress)`; weight ramps 0 → `hamming_weight_max` between start/end fractions.

---

## How to use
```python
from rune_decrypter_prime.scoring.hamming.loader import load_raw1grams_wordlists
from rune_decrypter_prime.scoring.hamming.backend import HammingBackend

wl_ltr, wl_rtl = load_raw1grams_wordlists(build_rtl=True)
backend = HammingBackend(wl_ltr, wl_rtl, max_hd=10, length_weights={1: 2.0})

runes = [1, 3, 0]          # plaintext indices
wli   = [[0, 2], [1, 2], [0, 1]]
stats = backend.total_min_hd_stats(runes, wli, direction="ltr")
print(stats["avg_hd_word"])  # average HD per word
```
Or via scorer params:
```python
scorer_params = dict(
    objective="pct.logp.win10",
    encoding_dir=Direction.LTR,
    hamming_enabled=True,
    hamming_wordlist_dir=None,   # packaged
    hamming_build_rtl=False,
    hamming_weight_max=0.08,
    hamming_ramp_start_frac=0.2,
    hamming_ramp_end_frac=0.7,
)
```

---

## Failure modes and guards
- Extension missing: scorer warns and skips Hamming (LM still runs).
- Word length missing in dictionaries: backend assigns full-mismatch cost (no exception).
- Mismatched rune length vs short-word dict: filtered out in `load_word_crib_config_from_raw1grams`.
- CSP conflicts: `build_bigram_keyspace_spec_from_word_crib` will raise if short-word/anchor constraints leave no valid patterns—use the same raw1grams source to avoid drift.

---

## Tuning tips
- Weight scale: penalty is average HD per word; start with `hamming_weight_max` in `0.05–0.12`.
- Length weights: up-weight singletons (e.g., `{1: 2.0}`) if you want to punish bad 1–2 letter words more.
- Direction: set `hamming_build_rtl=True` and `hamming_direction_mode="both"` if you decrypt mixed/unknown direction.
- `max_hd`: keep finite (e.g., 10–20) to avoid huge penalties dominating LM; it short-circuits early.

---

## References
- Code: `src/rune_decrypter_prime/scoring/hamming/{backend.py,loader.py,bindings.cpp,Hamming.*}`
- Tests: `tests/scoring/test_hamming_backend.py`, `tests/scoring/test_hamming_integration.py`
- Tutorial usage: `tutorials/v1/Tutorial_BigramSubstitution_v2.py` (Hamming enabled, ramped)
