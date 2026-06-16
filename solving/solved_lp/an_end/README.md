# AN END

Source label:

```text
red_rune.an_end
```

Primary recipe:

```text
recipe.an_end.stream_sequence_interruptors
```

Status:

```text
source catalogue entry exists
exact master-transcript locator pending verification
runner not implemented yet
```

Goal:

RDP should reproduce this solved LP text using a stream-sequence approach with
interrupters.

Planned technical path:

```text
1. Verify exact master-transcript locator for red_rune.an_end.
2. Build a dictionary/two-gram search over early plaintext candidates.
3. Recover early key material from the first words.
4. Compare candidate key material against canonical zero-shifted sequences
   such as primes-minus-one, emirps, Fibonacci-like sequences, and other simple
   named sequence candidates.
5. Select the matching sequence recipe.
6. Solve/replay the page with interrupters and record the result.
```

This is expected to be the trickiest initial solved-page reproduction. Keep the
source label method-free; all sequence and interrupter details belong in the
recipe/runner.
