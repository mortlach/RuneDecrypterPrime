# V1 Tutorials

Status: staged V1 draft

The V1 tutorials are small, repeatable runs that use the real RDP system. They
are teaching material and release evidence, not mock examples.

## Normal Tutorial Run

From the repository root:

```text
python tutorials/v1/run_pretty_print_release.py
```

This is the normal V1 tutorial gate. It runs the final pretty-print tutorial
list, prints compact status lines, and checks each tutorial against its minimum
match threshold.

Full output for each tutorial is written under:

```text
output/tutorial_pretty_print_logs/
```

## Full Printout Review

When the goal is to review the human-facing tutorial printouts, run:

```text
python tutorials/v1/run_pretty_print_output_review.py
```

This uses the same final tutorial list, but echoes every captured printout to the
console. It writes separate logs under:

```text
output/tutorial_pretty_print_output_review_logs/
```

Use this runner when checking whether tutorial output is clear, consistent, and
friendly enough for the V1 release.

## Final Tutorial List

The tutorial list and thresholds live as constants near the top of:

```text
tutorials/v1/run_pretty_print_release.py
```

The current list is:

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

## What Success Looks Like

The normal runner ends with a summary like:

```text
Pretty-print summary
selected=21 run=21 passed=21 failed=0
```

The important part is:

```text
failed=0
```

## How To Read Tutorial Output

Good tutorial output shows:

- what problem is being solved
- the text encoding direction, such as `ltr` or `rtl`
- the cipher and solver
- whether known truth or oracle data was used
- the match ratio or acceptance result
- the recovered key or relevant key preview
- where logs or artifacts were written

The standard RDP summary includes `encoding_dir` whenever plaintext is
being interpreted.

## What Tutorials Are Not

A tutorial proves that a specific lesson and configuration works. It does not
automatically promise that every possible cipher, key size, asset profile, or
solver setting is supported as a stable public surface.

When a tutorial uses known plaintext, a known key, or an oracle stop score, that
use must be visible in the report. Truth data may be used for teaching or
review, but it must not quietly affect production scoring or ranking.
