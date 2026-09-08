# Start solving Liber Primus

Start with Welcome Pilgrim: inspect the ciphertext, try a cipher model, then
account for interruptors. Next, use the koan A Man to compare a manual sweep
with a solver search, then explore number-sequence streams on An End.

These are small solving tutorials, not proof workbooks. They keep the choices
visible and print ordinary results rather than producing evidence files.

Run them from the repository root:

```text
python -m solving.lp_getting_started.01_load_welcome_pilgrim
python -m solving.lp_getting_started.02_try_vigenere
python -m solving.lp_getting_started.03_add_interruptors
python -m solving.lp_getting_started.04_try_reverse_shifts
python -m solving.lp_getting_started.05_let_rdp_search
python -m solving.lp_getting_started.06_explore_an_end
```

The first example is immediate. The Welcome Pilgrim searches take longer.
The final three scoring examples use the complete LM1-LM4 assets.
The search budgets bound the work, not elapsed time.

## 1. Look at the source

[`01_load_welcome_pilgrim.py`](01_load_welcome_pilgrim.py) loads the named source
and inspects its numeric payload. Welcome Pilgrim has 515 runes. Each rune also
has a WLI pair: its position within its word and the length of that word.

The source reference is the object passed to `RunSpec`. Loaded source data gives
us the actual indices, as we will need when constructing the interruptor pool.

## 2. Try a period-eight key

[`02_try_vigenere.py`](02_try_vigenere.py) supplies the Vigenere family and a key
length of eight. The key values are unknown to the search. The language model
ranks the resulting plaintext candidates.

This is useful, but incomplete. The search finds a rotation of the real key and
reads a substantial stretch correctly without recovering the complete page.
A plausible fragment is evidence worth following, not permission to stop.

The solved text is compared only after the run. The failure tells us that the
period-eight model is missing part of the construction.

## 3. Account for interruptors

[`03_add_interruptors.py`](03_add_interruptors.py) treats selected positions as
runes that pass through unchanged without advancing the repeating key. Missing
one such position changes the key alignment for the text that follows it.

The key length and interruptor count are prior information from the solved page.
The search receives neither the eight key values nor the eleven chosen
positions. It selects them from the 25 places where the ciphertext value is
zero.

The solver, scoring weights, seed and search budget are otherwise the same as
the previous lesson. With the missing mechanism included, the search recovers
all 515 runes.

The program prints the key, selected positions and full rune plaintext, then
checks the complete result against the canonical reference. A normal solver
stop is not itself proof of recovery. The final comparison supplies that check.

The reference preserves the source spelling `WIDSOM`. Each file contains its
own reference so that it can be read and run independently.

## 4. Sweep reverse shifts

[`04_try_reverse_shifts.py`](04_try_reverse_shifts.py) tries all 29 transformations
of the form `(28 - value + shift) % 29` on `koan_a_man`. It scores the candidates
with `api.score_many`, then prints the strongest five with rune previews.

Shift 3 ranks first under the LM1-LM4 character and WLI model. The important
point is not that 29 candidates are difficult; it is that a complete manual
sweep gives us a simple result to compare with the optimiser.

The transform is its own inverse when the same shift is applied twice. That is
a useful round-trip check, but every one of the 29 possible shifts passes that
check. It would not tell us which shift to choose.

## 5. Let RDP search

[`05_let_rdp_search.py`](05_let_rdp_search.py) expresses the same rule through
`api.experimental.define_cipher_map`. A repeating key of length one holds the
unknown shift. The program compares the solver's key, plaintext and score with
the complete sweep.

The narrow search agrees with the sweep: shift 3 wins. The second experiment
then removes that structural assumption and permits any substitution of the
29-rune alphabet.

That problem is much larger. The short 2,000-iteration run previously matched
443 of the 778 runes in the narrow result. It is reported as an incomplete
experiment, not dressed up as a recovery because part of the plaintext
contains the answer.

## 6. Explore An End

[`06_explore_an_end.py`](06_explore_an_end.py) tries four sequence families as
key streams: primes, Fibonacci numbers, triangular numbers and squares.
For each family it varies the starting offset from 0 to 20 and the constant
shift from 0 to 28.

The first sweep uses language-model scores alone. It previously selected the
prime stream at offset 0 with shift 28, but the text breaks partway through.

There are five ciphertext-zero positions. The follow-up keeps the winning
stream and tries all 32 subsets as possible interruptors. Position 56 is then
selected and all 85 reference runes are recovered. The solved reference is
checked only after the language model has chosen its candidate.

The [detailed An End workbook](../solved_lp/08_An_End.py) also explores phrase
starts and interruptors. That workbook can use the reference in ranking and
remains a reference-guided diagnostic. The shorter example is a separate
language-model ranking experiment.

## Further examples

The [detailed Welcome Pilgrim workbook](../solved_lp/02_Welcome_Pilgrim.py)
retains the fuller diagnostics and evidence output. See the
[workbook index](../solved_lp/README.md) for other solved sources.
