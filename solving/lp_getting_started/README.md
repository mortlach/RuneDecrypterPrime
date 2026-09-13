# Start solving Liber Primus

This is the point where the examples stop using made-up ciphertext and start
working with Liber Primus itself.

We begin with  Welcome Pilgrim  because it gives us a useful solved problem to
play with. We already know some things about its construction, but we can choose
what to give the search and see what each assumption buys us.

After that we use A Man for a very small complete search, then An End for
a more exploratory sequence experiment.

These are not proof workbooks. They are small solving examples where the
assumptions are kept close to the code and the known plaintext is used only
afterwards to check what we found.

If the RDP API itself is still unfamiliar, start with
[Learn RDP by solving](../../docs/learn/README.md).

Run these from the repository root:

```text
python -m solving.lp_getting_started.01_load_welcome_pilgrim
python -m solving.lp_getting_started.02_try_vigenere
python -m solving.lp_getting_started.03_add_interruptors
python -m solving.lp_getting_started.04_try_reverse_shifts
python -m solving.lp_getting_started.05_let_rdp_search
python -m solving.lp_getting_started.06_explore_an_end
```

The first example is immediate. The Welcome Pilgrim searches take longer. The
last three examples use the complete LM1-LM4 language-model assets. Search
budgets limit the work; elapsed time depends on the machine.

## Contents

- [1. Look at the ciphertext first](#1-look-at-the-ciphertext-first)
- [2. Try the period-eight model](#2-try-the-period-eight-model)
- [3. Add interruptors](#3-add-interruptors)
- [4. Try all 29 shifts](#4-try-all-29-shifts)
- [5. Make the solver agree](#5-make-the-solver-agree)
- [6. Explore An End](#6-explore-an-end)
- [Where next?](#where-next)

## 1. Look at the ciphertext first

`01_load_welcome_pilgrim.py` loads Welcome Pilgrim as an RDP source and prints a
few useful parts of its record.

Nothing clever happens. That is the point. Before testing a cipher idea, it is
worth checking which text you are actually about to attack.

## 2. Try the period-eight model

`02_try_vigenere.py` uses one known fact from the solved page: the Vigenere
period is eight.

The eight key values are not supplied to the search. Nor are interruptors.

The model gets part of the way, but not all the way. That is useful information:
period eight is probably real, but ordinary Vigenere alone does not explain the
whole page.

## 3. Add interruptors

`03_add_interruptors.py` gives the search one more known fact: there are eleven
interruptors among the ciphertext-zero positions.

It still has to find the eight key values and choose the eleven positions.

With that missing alignment rule included, the complete solved plaintext is
recovered.

The known plaintext is loaded separately with:

```python
api.liber_primus.load_plaintext("welcome_pilgrim")
```

and used only after the run to check the result.

## 4. Try all 29 shifts

`04_try_reverse_shifts.py` moves to A Man.

The proposed reverse-shift transform has only 29 possible shifts. There is no
reason to ask an optimiser to guess among 29 cases when Python can simply try all
of them.

So we do.

## 5. Make the solver agree

`05_let_rdp_search.py` expresses the same reverse-shift rule through the RDP
cipher interface and checks that Beam finds the same answer as the complete
sweep.

Then we remove that convenient structure and allow an arbitrary substitution.
The same small budget is suddenly nowhere near enough. Search spaces have a
sense of humour like that.

## 6. Explore An End

`06_explore_an_end.py` tries primes, Fibonacci numbers, triangular numbers and
squares as key streams, with different offsets and shifts.

The language model chooses the best stream without being given the known
plaintext.

There are then only five ciphertext-zero positions, so every possible
interruptor subset means just 32 cases. We try all 32 and compare the winner
with the solved `An End` plaintext afterwards.

## Where next?

The fuller solved-LP workbooks retain the more detailed diagnostics and evidence:

[solving/solved_lp/README.md](../solved_lp/README.md)

Or take one of these examples and change something. That is rather more the
point of having RDP in the first place.
