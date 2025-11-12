# Scoring – WLI & Objectives

Audience: Hands-on / Expert  
Time: 3–5 minutes  
Outcome: Understand how the scorer combines rune windows + WLI pairs, how to set objectives, and which backends/telemetry fields matter.  
Prereqs: Completed one tutorial run.

This page is the quick-reference companion to `guides/scoring_deep.md`, which dives into the LM math and percentile tables.

---

## 1. What the scorer consumes/produces
- **Rune windows:** the scorer takes contiguous windows of rune indices (`np.uint8`, length `win=10`, stride `1`). Windowing is handled internally; you just pass plaintext candidates as lists/arrays.
- **WLI pairs:** every rune also carries a `[start, length]` pair describing the word it belongs to. Tutorials infer this from spaces; you can pass an explicit `wli_data` list/array when calling `RunAPI`. WLI-aware models rely on this to reward word-shaped decrypts.
- **Outputs:** for `pct.*` objectives the scorer returns percentiles in `[0, 1]`. Telemetry records decrypt and score timing in `solution.meta["work"]` plus backend info in `telemetry.run.scorer`.

> Heads-up: if you skip `wli_data`, the scorer builds a single-word WLI (everything belongs to one word). This keeps runs deterministic but loses the WLI channel advantage.

---

## 2. Choosing objectives & params
- **Default:** `"pct.logp.win10"` — percentile of per-window log-probability over 10-character windows. Deterministic, scale-free, and available on every backend.
- **Aliases:** strings like `"energy.logp"` or `"pct.logp"` are normalised in `api/normalize.normalize_objective_spec`; they become the canonical `ObjectiveSpec`.
- **Knobs:** set objectives, channel weights, ECDF clamps, and encoding direction via `scorer_params`. Keep them explicit when sharing configs so other solvers can reproduce your run.
- **When to tweak:** increase `wli_weights` if you want word-boundary signal, or clamp ECDF floors/ceilings when experimenting with noisy language models (see `scoring/rune_scorer.py` docstring).

---

## 3. Backends & telemetry
- **NumPy** is the reference scorer; it runs everywhere and drives CI/Tier-A tests.
- **Torch** backend (CPU or CUDA) offers faster batched scoring. The unified scorer honours `Device` enums and strings (`"cpu"`, `"cuda"`). Telemetry records the chosen backend under `telemetry.run.scorer.impl` and `telemetry.run.scorer.device`.
- **C++ `_fastlm`** extension streams the LM tables quickly on macOS/Linux; Windows ships the `.pyd`. Build it via `python src/rune_decrypter_prime/scoring/language_model/setup_fastlm.py`.
- **Telemetry:** if you flip backends or channel weights, the delta shows up in `telemetry.run` and `solution.meta["work"]`. Use `guides/telemetry.md` to interpret those fields.

---

## 4. Hands-on snippet
```python
from rune_decrypter_prime.api import RunAPI, SolverSpec, KeySpec, by_name
from rune_decrypter_prime.core.types import Direction

sol = RunAPI.run(
    text="ᛏᚻᛖᚱᛖ ᚹᚪᛋ ᚪ ᛏᚪᛒᛚᛖ",
    cipher=by_name.cipher("vigenere", key_len=6),
    key=KeySpec.repeat(len=6),
    solver=SolverSpec.sa(seed=42, progress_pct=1),
    scorer="rune",
    scorer_params={"objective": "pct.logp.win10", "encoding_dir": Direction.LTR},
    telemetry_on=True,
)
print("score:", sol.score)
print("scorer backend:", sol.meta["telemetry"]["run"]["scorer"])
```
This mirrors the Start_Here defaults—objective and direction are explicit, and telemetry is enabled so logs capture the backend/device.

---

## 5. Related tests & docs
- Tests: `tests/scoring/test_pct_win10_stats_and_telemetry.py`, `tests/scoring/test_backend_selection_and_parity.py`, `tests/scoring/test_pct_win10_wli_numpy_vs_list_equivalence.py`.
- Docs: `guides/scoring_deep.md` (math/backends), `guides/telemetry.md` (scorer metadata), `howto/deterministic_run.md` (reproducing scores on another machine).
