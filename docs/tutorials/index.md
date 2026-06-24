# V1 Pretty-Print Tutorials

The normal V1 tutorial command is:

```text
python tutorials/v1/run_pretty_print_release.py
```

For a printout review where every captured tutorial printout is echoed to the
console, run:

```text
python tutorials/v1/run_pretty_print_output_review.py
```

The runner keeps the final tutorial list and thresholds as constants near the top
of `tutorials/v1/run_pretty_print_release.py`. There are no RDP tutorial
environment variables, CLI switches, or separate config files for the normal
tutorial path.

## Final V1 List

| Tutorial | Minimum match |
| --- | ---: |
| `Start_Here.py` | 1.000 |
| `Tutorial_Autokey.py` | 1.000 |
| `Tutorial_Railfence.py` | 1.000 |
| `Tutorial_Vigenere_Interruptors_Exact.py` | 1.000 |
| `Tutorial_ColumnarTransposition.py` | 1.000 |
| `Tutorial_Vigenere_GeneralMap.py` | 1.000 |
| `Tutorial_Vigenere_Interruptors_Solve.py` | 1.000 |
| `Tutorial_MonoSubstitution_GA_RTL.py` | 0.970 |
| `Tutorial_MonoSubstitution_GA_LTR.py` | 0.970 |
| `Tutorial_Repeating_multiply.py` | 1.000 |
| `Tutorial_MonoSubstitution_HYBRID_RTL.py` | 0.995 |
| `Tutorial_Vigenere_Interruptors_NonTrivial.py` | 1.000 |
| `Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py` | 1.000 |
| `Tutorial_ScheduledStreamLookup_RealSolve_P13Primes.py` | 1.000 |
| `Tutorial_ScheduledStreamLookup_RealSolve_P13P31Segmented.py` | 0.900 |
| `Tutorial_LP_Welcome_Pilgrim_Solve.py` | 1.000 |
| `Tutorial_MonoSubstitution_SA_LTR.py` | 0.995 |
| `Tutorial_PeriodicSubstitution.py` | 1.000 |
| `Tutorial_PeriodicSubstitution_Simple_P7.py` | 1.000 |
| `Tutorial_PeriodicColumnar.py` | 1.000 |
| `Tutorial_PeriodicColumnar_Simple_P7_ColThenSub.py` | 1.000 |

The compact release runner writes full per-tutorial output under:

```text
output/tutorial_pretty_print_logs/
```

The output-review runner writes its logs under:

```text
output/tutorial_pretty_print_output_review_logs/
```
