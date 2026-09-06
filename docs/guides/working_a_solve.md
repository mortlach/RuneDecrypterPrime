# Comparing solve experiments

Most RDP solving work is comparative.

Change the cipher, period, direction, scorer, starting information or search
budget, then compare the result with a previous run.

Where possible, change one thing at a time:

```text
period 6 vs period 7
character scoring vs character + WLI
LTR vs RTL
beam width 96 vs 192
random start vs prepared start
```

Several assumptions sometimes need to move together. Record that explicitly
because attribution is then weaker.

## Source facts and solving assumptions

Keep source information separate from assumptions introduced by the solve.

For a Liber Primus example, the source may provide ciphertext and word
boundaries. A period, cipher family, interruptor count or prepared key may come
from a clue, an earlier experiment or a known solution.

Those inputs support different claims.

## Search budget

Increase the search budget when the smaller run is still improving or exposing
structure.

If nearby runs fail in the same way, revisit the cipher or key model before
assuming more compute is the answer.

See [Solvers](solvers.md).

## Starting information

`RunSpec.initial_keys` and `InterruptorConfig` make prior information explicit.

A warm-started recovery shows what can be found from that starting point. It is
not the same result as reaching the same region from an unprepared search.

See [Keys and key spaces](keyops.md) and [Interruptors](interruptors.md).

## Read the run, not only the plaintext

`RunResult` contains the candidate and score.

The status and solver report show how the search ended and how much work it did.

Telemetry records runtime behaviour.

Reproducibility metadata records the state needed for a repeat.

See [Reading a result](results.md), [Telemetry](telemetry.md) and
[Repeating a run](reproducibility.md).

## Development

The same comparison discipline continues in `cipher_development/`.

Retained experiments fix the selected experiment, mode, seed and output
location. Smoke checks remain separate from longer development studies.

Reusable production behaviour belongs under `src/rdp/`. Broader qualification
belongs under `tools/robustness/`.

See [Cipher development](../development/cipher_development.md) and
[Extending RDP](extending_rdp.md).
