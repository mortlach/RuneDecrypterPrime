# Getting started with Liber Primus

This short route connects the public API to a real bundled source without
hiding the important choices.

It is deliberately compact. If you want the choices unpacked one at a time,
continue with [Start solving Liber Primus](../lp_getting_started/README.md).
If the RDP run model itself is still new, start with
[Learn RDP by solving](../../docs/learn/README.md).

Read the files in this order:

1. [`load_source.py`](load_source.py) loads Welcome Pilgrim and inspects its
   identity and numeric data.
2. [`prepare_search.py`](prepare_search.py) builds the reviewed period-8
   Vigenere search without starting it.
3. [`run_search.py`](run_search.py) runs that request and prints the structured
   result. This is the longer step and takes roughly a minute on the reference
   machine.

From the repository root:

```text
python -m solving.getting_started.load_source
python -m solving.getting_started.prepare_search
python -m solving.getting_started.run_search
```

The known key length and number of interruptors are prior information from the
solved page. The search is not given the key values or the exact interruptor
positions. The full evidence-producing version remains in
[`solving/solved_lp/02_Welcome_Pilgrim.py`](../solved_lp/02_Welcome_Pilgrim.py).
