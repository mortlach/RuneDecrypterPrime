# Anatomy of an RDP run

To search for a key, we need to tell RDP what text we have, which cipher we think
was used and which keys to try. We also choose how to search and how to judge
the resulting plaintext. `RunSpec` brings those choices together.

The getting-started files introduce each part as we need it. This page keeps
them in one place for when you want to put together your own run.

## Input: what text do we have?

Use `RawTextInput` for visible rune text. RDP converts it to rune indices and
records the word positions, called word-location information or WLI. If you
already have the numbers, use `RuneIndexInput` and supply WLI separately if you
have it. Named source inputs let you refer to bundled material, including
Liber Primus passages, without putting a local file path in the request.

Use the information the source gives you. Adding spaces means giving the
scorer word boundaries, so it changes more than how the text looks.

## CipherSpec: which cipher are we trying?

`CipherSpec` selects the cipher and its fixed settings. For rail fence, those
settings can include the allowed rail counts. A scheduled-stream cipher also
needs the known schedule.

The key is supplied separately. If we already know it, we can pass it with the
cipher to `api.encrypt` or `api.decrypt` and get the result straight back.
To find an unknown key, we first need to describe the possibilities.

## KeySpec: which keys can we try?

`KeySpec` defines the keys the solver may consider. Different ciphers need
different kinds of key:

| Key space | What the solver can change |
| --- | --- |
| `scalar(minimum, maximum)` | One integer within a range, such as the number of rails. |
| `repeating(length)` | The values in a repeating key of a known length. |
| `repeating_range(minimum_length, maximum_length)` | Both the values and the length of a repeating key. |
| `permutation(length)` | An ordering, such as the columns in a transposition. Each position appears once. |
| `periodic_substitution(...)` | Substitution alphabets used over a repeating period. |
| `periodic_columnar(...)` | Periodic substitutions together with a column ordering. |

A concrete key contains actual values, such as `(3, 1, 4)`. A `KeySpec` tells
RDP which possible values to search. Choosing the wrong length or range can
exclude the key before the search has even started.

Custom key types and their search operations can also be implemented as part
of cipher development. See [key spaces and extension](keyops.md) for the
available options and where to start adding your own.

## SolverSpec: how should RDP search?

`SolverSpec` chooses the search algorithm and how much work it can do. Depending
on the solver, you might change beam width, rounds, generations or the number
of starts. A wider beam keeps more alternatives; extra rounds give the search
more opportunities to improve them. Both cost time. The [solver guide](solvers.md)
explains the choices in more detail.

A seed lets us repeat the random choices in a run. Keep it fixed when comparing
settings, along with the scorer and the rest of the request.

You can also give a search initial keys or cribs. Explain where these came
from: a search with a useful hint answers a different question from one that
started with ciphertext alone.

## ScoringConfig: which candidates look promising?

The scorer ranks candidate plaintexts so the solver has something to work
with. Character scoring looks at rune sequences. Word-length scoring uses the
word information supplied with the input. `ScoringConfig` selects those parts
and sets their weights and orders.

Changing the scorer can change which candidates the search prefers. Keep its
settings with the result, and compare scores using the same model. A high score
alone doesn't tell us that we have recovered the original message.

## Direction and interruptors

Text direction affects how RDP reads the runes and their word information.
Choose it to match the source you are using.

Interruptors are positions the cipher leaves alone. If you know their positions,
use `InterruptorConfig.exact(...)`. If you want RDP to find them, `search(...)`
lets you supply possible positions and bounds for the search. Supplying the
positions saves work, but it also gives RDP more information about the problem.

## RunSpec: put the request together

Once those parts are defined, the usual call looks like this:

```python
request = api.RunSpec(
    problem_input=problem_input,
    cipher=cipher,
    key_space=key_space,
    solver=solver,
    scoring=scoring,
    text_direction=direction,
)

result = api.run(request)
```

The getting-started files contain complete runnable versions. As the problem
gets more involved, we add settings to this same request.

## RunResult: what did we get back?

Start with the candidate key and plaintext, then look at how the run reached
them. The result keeps both:

| Result section | What to look for |
| --- | --- |
| `key`, `plaintext`, `score` | The best candidate returned and its score. |
| `status` | Whether the run completed, was blocked or failed, and why it stopped. |
| `solver_report` | How much work the search performed. |
| `scorer_report` | Which scoring components and assets were used. |
| `configuration` | The settings RDP actually used, including resolved defaults. |
| `reproducibility` | Seed, backend, device, version and assets needed to repeat the run. |
| `oracle` | Whether a known answer affected scoring, ranking or stopping. |
| `artifacts` | Any output files requested for the run. |

A run can finish successfully and still recover only part of the message.
When we know the original, we can compare it directly. With an unknown message,
we have to investigate the candidate and explain why we think it is right.

Continue through the numbered
[`getting_started`](../../tutorials/v1/getting_started/) files, then choose a
problem from the [example catalogue](../../tutorials/v1/README.md).
