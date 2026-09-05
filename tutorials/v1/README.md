# V1 runnable route and example catalogue

There are two different kinds of runnable material here.

- [`getting_started/`](getting_started/) is a ten-stop route through the
  ordinary installed API. Read it in filename order.
- [`examples/`](examples/) is a library of worked problems, comparisons,
  robustness recipes and qualifications. It is not ordered by difficulty.

All paths and commands below assume the repository root as the working
directory.

## Getting started

| Stop | Establishes | Typical runtime | Result |
| --- | --- | ---: | --- |
| [`01_known_key.py`](getting_started/01_known_key.py) | Known-key encrypt/decrypt and reviewed text forms | <1 s | exact round trip |
| [`02_first_search.py`](getting_started/02_first_search.py) | A small unknown-key search | <1 s | exact key and text |
| [`03_repeating_key_search.py`](getting_started/03_repeating_key_search.py) | Raw rune text, WLI and a repeating key | ~3 s | exact key and text |
| [`04_reproducible_runs.py`](getting_started/04_reproducible_runs.py) | Seed and reproducibility metadata | <1 s | identical observations |
| [`05_known_interruptors.py`](getting_started/05_known_interruptors.py) | Exact interruptor positions as supplied evidence | ~2 s | exact key and text |
| [`06_partial_recovery.py`](getting_started/06_partial_recovery.py) | Honest interpretation of a deliberately narrow budget | ~2 s | stable partial range |
| [`07_liber_primus_source.py`](getting_started/07_liber_primus_source.py) | Named Liber Primus source loading | <1 s | source boundary only |
| [`08_reading_a_result.py`](getting_started/08_reading_a_result.py) | Candidate, status, work, configuration, reproducibility and oracle evidence | <1 s | reports agree with exact result |
| [`09_changing_search_budget.py`](getting_started/09_changing_search_budget.py) | One-variable comparison of narrow and wider beam searches | ~3 s | same exact result; different work |
| [`10_prepare_a_real_source_search.py`](getting_started/10_prepare_a_real_source_search.py) | Assemble the reviewed Welcome Pilgrim request without launching the longer solve | <1 s | request prepared; not executed |

Run a stop directly, for example:

```text
python -m tutorials.v1.getting_started.03_repeating_key_search
```

These files use `from rdp import api` and no repository imports or path
injection. Their code works against an installed package; the files themselves
are source-checkout companions.

## Runner groups

Edit `RUN_SET` near the top of [`run_tutorials.py`](run_tutorials.py), then run:

```text
python tutorials/v1/run_tutorials.py
```

| Group | Contents |
| --- | --- |
| `GETTING_STARTED` | All ten numbered stops. |
| `RELEASE` | The numbered route plus three bounded, distinct examples. |
| `BUNDLED_EXAMPLES` | Examples that use bundled assets and exclude qualifications. |
| `FULL_ASSET_EXAMPLES` | Two bounded two-period examples proving the full assets. |
| `QUALIFICATION` | Three explicitly named, several-hour P7/C7 programs. |

There is no “everything” option. Several-hour work should require a decision
that says several hours.

Runtime below is an order of magnitude, not a service-level promise. Exact
figures marked “observed” were measured on the reference CPU during this
migration; the other classes come from the retained bounded or qualification
recipes and remain hardware-dependent.

## Cipher and public-boundary examples

| File | Purpose | Cipher / solver | Surface | Assets | Runtime | Result | Truth / oracle |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| [`vigenere_known_key_and_general_map.py`](examples/vigenere_known_key_and_general_map.py) | Compare a supplied-key operation with an unseeded general-map solve | Vigenere / beam | Public run; repo text support | bundled | seconds | exact | known key enters first comparison; plaintext validates both |
| [`vigenere_general_map.py`](examples/vigenere_general_map.py) | Express Vigenere through the experimental map boundary | general map / beam | Public + experimental API; repo fixture | bundled | seconds | exact | plaintext sets an oracle stop and validates |
| [`rail_fence.py`](examples/rail_fence.py) | Recover an unknown rail count | rail fence / beam | Public run; repo text support | bundled | seconds | exact | plaintext validates only; no oracle stop |
| [`columnar_transposition.py`](examples/columnar_transposition.py) | Recover a column permutation | columnar / hybrid | Public run; repo text support | bundled | ~4 s observed | exact | plaintext sets an oracle stop and validates |
| [`repeating_multiply.py`](examples/repeating_multiply.py) | Recover a repeating multiplicative key modulo 29 | general map / beam | Public + experimental API; repo fixture | bundled | ~17 s observed | exact | plaintext sets an oracle stop and validates |

## Autokey and mono-substitution examples

| File | Purpose | Cipher / solver | Surface | Assets | Runtime | Result | Truth / oracle |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| [`autokey.py`](examples/autokey.py) | Compare an older GA run with crib-assisted seeds | Autokey / GA | Public run; repo fixture/support | bundled | seconds | exact assisted run | plaintext sets an oracle stop; crib informs second seed pool |
| [`autokey_robust.py`](examples/autokey_robust.py) | Use the qualified multi-restart recipe | Autokey / beam | Public run; repo fixture/support | bundled | tens of seconds | exact robust evidence | truth validates after selection; no oracle stop or true-key seed |
| [`mono_substitution_ga_ltr.py`](examples/mono_substitution_ga_ltr.py) | LTR single-attempt baseline | mono substitution / GA | Public run; repo fixture/support | bundled | tens of seconds | readable ≥0.970 | plaintext sets an oracle stop and validates |
| [`mono_substitution_ga_rtl.py`](examples/mono_substitution_ga_rtl.py) | Independent RTL single-attempt baseline | mono substitution / GA | Public run; repo fixture/support | bundled | tens of seconds | readable ≥0.970 | plaintext sets an oracle stop and validates |
| [`mono_substitution_ga_robust.py`](examples/mono_substitution_ga_robust.py) | Score-select three independent attempts | mono substitution / GA | Public run; repo fixture/support | bundled | minutes | readable ≥0.970 | truth validates after score-only selection; no oracle stop |
| [`mono_substitution_hybrid_rtl.py`](examples/mono_substitution_hybrid_rtl.py) | Contrast the hybrid solver on RTL text | mono substitution / hybrid | Public run; repo fixture/support | bundled | minutes | near-exact ≥0.995 | plaintext sets an oracle stop and validates |
| [`mono_substitution_sa_ltr.py`](examples/mono_substitution_sa_ltr.py) | Use simulated annealing on an LTR fixture | mono substitution / SA | Public run; repo fixture/support | bundled | minutes | near-exact ≥0.995 | plaintext sets an oracle stop and validates |

## Interruptor and scheduled-stream examples

| File | Purpose | Cipher / solver | Surface | Assets | Runtime | Result | Truth / oracle |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| [`vigenere_interruptors_exact.py`](examples/vigenere_interruptors_exact.py) | Supply known interruptor positions | Vigenere / beam | Public run; repo fixture/support | bundled | seconds | exact | plaintext sets an oracle stop and validates |
| [`vigenere_interruptors_solve.py`](examples/vigenere_interruptors_solve.py) | Search a small interruptor pool from one start | Vigenere / beam | Public run; repo fixture/support | bundled | seconds | exact | plaintext sets an oracle stop and validates |
| [`vigenere_interruptors_nontrivial.py`](examples/vigenere_interruptors_nontrivial.py) | Search a larger interruptor case | Vigenere / beam | Public run; repo fixture/support | bundled | tens of seconds | exact | plaintext sets an oracle stop and validates |
| [`vigenere_interruptors_robust.py`](examples/vigenere_interruptors_robust.py) | Use the qualified three-restart interruptor recipe | Vigenere / beam | Public run; repo fixture/support | bundled | tens of seconds | exact robust evidence | truth validates after selection; no oracle stop |
| [`scheduled_stream_lookup_p13_sequence.py`](examples/scheduled_stream_lookup_p13_sequence.py) | Recover a P13 key with a supplied sequence schedule | scheduled stream / beam | Public run; repo fixture/support | bundled | ~22 s observed | exact | truth validates only; no key seed or oracle stop |
| [`scheduled_stream_lookup_p13_primes.py`](examples/scheduled_stream_lookup_p13_primes.py) | Recover a P13 key with a generated prime schedule | scheduled stream / beam | Public run; repo fixture/support | bundled | tens of seconds | exact | truth validates only; no key seed or oracle stop |
| [`scheduled_stream_lookup_p13_p31_segmented.py`](examples/scheduled_stream_lookup_p13_p31_segmented.py) | Recover a thresholded segmented P13/P31/P13 case | scheduled stream / beam | Public run; repo fixture/support | bundled | tens of seconds | partial ≥0.900 | truth validates threshold only; no key seed or oracle stop |

## Liber Primus and two-period examples

| File | Purpose | Cipher / solver | Surface | Assets | Runtime | Result | Truth / oracle |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| [`lp_welcome_pilgrim_solve.py`](examples/lp_welcome_pilgrim_solve.py) | Run the reviewed Welcome Pilgrim workbook from a named source | Vigenere interruptors / beam | Public run + solved-workbook bridge | bundled | ~50 s observed | exact | canonical plaintext validates; no oracle stop |
| [`two_period_cribs.py`](examples/two_period_cribs.py) | Fast two-period crib-constrained solve | two-period Vigenere / crib solver | Public run + repo fixture | full V1 | ~11 s observed | exact | key/plaintext validate only; fixed cribs constrain search |
| [`two_period_cribs_interruptors.py`](examples/two_period_cribs_interruptors.py) | Add structural interruptor-pool search | two-period Vigenere / crib solver | Public run + repo fixture | full V1 | ~11 s observed | exact | truth validates key, text and positions; no oracle stop |
| [`two_period_cribs_p13_p31_search.py`](examples/two_period_cribs_p13_p31_search.py) | Exercise the genuine P13/P31 d14 branch | two-period Vigenere / crib solver | Public run + repo fixture | full V1 | tens of seconds | exact | truth validates key, text and positions; no oracle stop |

## Qualification programs

These are scientific programs, not ordinary examples with slightly larger
numbers. Inspect the recipe and assets before starting one.

| File | Purpose | Cipher / solver | Surface | Assets | Runtime | Result | Truth / oracle |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| [`periodic_substitution.py`](examples/periodic_substitution.py) | Full periodic-substitution qualification recipe | periodic substitution / Kaeding | Public run + repo seed/support | full V1 | several hours | near-exact ≥0.995 | plaintext sets an oracle stop and validates |
| [`periodic_substitution_p7.py`](examples/periodic_substitution_p7.py) | Focused P7 periodic-substitution qualification | periodic substitution / Kaeding | Public run + repo seed/support | full V1 | several hours | near-exact ≥0.995 | plaintext sets an oracle stop and validates |
| [`periodic_columnar_p7_column_then_substitution.py`](examples/periodic_columnar_p7_column_then_substitution.py) | Exploit the qualified P7/C7 warm start | periodic columnar / Kaeding | Public run + qualified repo evidence | full V1 | ~40 min on qualification machine | exact | non-answer warm key enters search; plaintext validates only |

Candidate discovery for the last program remains in
[`cipher_development/periodic_columnar_staged/`](../../cipher_development/periodic_columnar_staged/).
The next campaign question is deliberately still open; see
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).

## Adding another example

An addition should close a real difficulty gap, cover a novel V1 problem,
demonstrate an otherwise uncovered feature, provide an important comparison, or
connect a real source to a repeatable workflow. Changed constants alone are not
a reason for another file.

Every accepted example must state its purpose, asset profile, approximate
runtime, deterministic seed where applicable, semantic result condition and
truth/oracle use. If its main value is regression protection, put it in
`tests/`. If it has no stable result yet, put it in the relevant development
area.
