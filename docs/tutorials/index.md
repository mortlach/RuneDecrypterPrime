# V1 Pretty-Print Tutorials

The V1 tutorial command is:

```text
python tutorials/v1/run_tutorials.py
```

The runner keeps the tutorial list, run-set choice, thresholds, console-output
policy, and log folder as constants near the top of
`tutorials/v1/run_tutorials.py`. There are no RDP tutorial environment
variables, CLI switches, or separate config files for the normal tutorial path.

For a full printout review, edit this constant in the same file:

```python
CONSOLE_OUTPUT = ConsoleOutput.FULL
```

## Final V1 List

| Tutorial | Acceptance | Minimum match |
| --- | --- | ---: |
| `Tutorial_Start_Here.py` | `exact` | 1.000 |
| `Tutorial_Autokey.py` | `exact` | 1.000 |
| `Tutorial_Railfence.py` | `exact` | 1.000 |
| `Tutorial_Vigenere_Interruptors_Exact.py` | `exact` | 1.000 |
| `Tutorial_ColumnarTransposition.py` | `exact` | 1.000 |
| `Tutorial_Vigenere_GeneralMap.py` | `exact` | 1.000 |
| `Tutorial_Vigenere_Interruptors_Solve.py` | `exact` | 1.000 |
| `Tutorial_MonoSubstitution_GA_RTL.py` | `human_readable` | 0.970 |
| `Tutorial_MonoSubstitution_GA_LTR.py` | `human_readable` | 0.970 |
| `Tutorial_Repeating_multiply.py` | `exact` | 1.000 |
| `Tutorial_MonoSubstitution_HYBRID_RTL.py` | `near_exact` | 0.995 |
| `Tutorial_Vigenere_Interruptors_NonTrivial.py` | `exact` | 1.000 |
| `Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py` | `exact` | 1.000 |
| `Tutorial_ScheduledStreamLookup_RealSolve_P13Primes.py` | `exact` | 1.000 |
| `Tutorial_ScheduledStreamLookup_RealSolve_P13P31Segmented.py` | `partial_recovery` | 0.900 |
| `Tutorial_LP_Welcome_Pilgrim_Solve.py` | `exact` | 1.000 |
| `Tutorial_MonoSubstitution_SA_LTR.py` | `near_exact` | 0.995 |
| `Tutorial_PeriodicSubstitution.py` | `near_exact` | 0.995 |
| `Tutorial_PeriodicSubstitution_Simple_P7.py` | `near_exact` | 0.995 |
| `Tutorial_PeriodicColumnar.py` | `near_exact` | 0.995 |
| `Tutorial_PeriodicColumnar_Simple_P7_ColThenSub.py` | `exact` | 1.000 |

The runner writes full per-tutorial output under:

```text
output/tutorial_logs/
```
