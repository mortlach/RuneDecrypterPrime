# LP attempts

This folder is for reproducible attempts against unsolved or diagnostic Liber
Primus sources.

Attempts should be useful even when they do not solve anything. Each attempt
should record:

```text
question         what hypothesis is being tested
source_label     which LP source was loaded
recipe/model     which cipher or route family was tried
truth_policy     usually no_truth for unsolved material
expected_result  solve, near_solve, diagnostic_only, or expected_fail
result_summary   what happened and why it matters
```

Do not start unsolved attempts by hand-copying ciphertext. Use the LP source
catalogue and verified main transcript locators so attempts can be rerun and
compared later.

The solved-page reproductions in `../solved_lp/` should come first. Once the
source-label and recipe interface is proven there, unsolved attempts can reuse
it without new ad-hoc wiring.
