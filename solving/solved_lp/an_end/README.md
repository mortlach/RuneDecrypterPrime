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
payload_from_label loads real master-transcript payload
current boundary granularity: full canon page 56
runner not implemented yet
```

Goal:

RDP should reproduce this solved LP text using a stream-sequence approach with
interrupters.

Planned technical path:

```text
1. Use the live red_rune.an_end payload.
2. Build the early-word candidate search.
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
