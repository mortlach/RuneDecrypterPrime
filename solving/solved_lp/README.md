# Solved LP runs

This folder is for reproducing solved Liber Primus material with RDP.

The goal is not to hide solved knowledge. The goal is to separate:

```text
source text     which LP fragment is loaded
solve recipe    which cipher/replay method is used
truth policy    whether reference plaintext/key is used for solving or evaluation
```

## Initial targets

```text
welcome_pilgrim/       Vigenere-with-interruptors real-solve target
koan_during_lesson/    Vigenere-with-interruptors real-solve target
an_end/                stream-sequence-with-interruptors special target
```

`AN END` is expected to be the hardest first solved-page reproduction. The
planned approach is to derive early key material from candidate words, compare it
against simple canonical sequences such as primes-minus-one, and then use the
recognised stream sequence with interrupters.

## Current status

The source-label catalogue exists. Exact master-transcript locators are still
being verified one source at a time, so runners should not bypass
`lp.payload_from_label(...)` with unverified candidate page ranges.
