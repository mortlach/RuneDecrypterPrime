# Anatomy of an RDP run

An RDP search is not just ciphertext plus a solver name. It is one explicit
claim about the evidence, transformation, possible keys, ranking model and work
budget. `RunSpec` keeps those parts together so the result can report what was
actually requested and executed.

## Problem input: what evidence is available?

`RawTextInput` accepts visible rune text and derives rune indices plus
word-location information (WLI). `RuneIndexInput` accepts reviewed indices and
optional WLI directly. Source-reference inputs name resolver-owned material such
as Liber Primus fragments without embedding a machine-specific path.

Choose the input form that matches the evidence. Do not invent spaces, a Latin
rendering or source provenance merely because it improves presentation.

## Cipher specification: what transformation is proposed?

`CipherSpec` identifies the cipher family and its fixed structural parameters.
For example, a rail-fence specification may bound valid rail counts, while a
periodic fixed-stream specification carries the known schedule.

The cipher specification is not the unknown key and does not initiate a search.
Known-key `encrypt` and `decrypt` operations combine a `CipherSpec` with a
concrete key and return directly.

## Key specification: what may the solver vary?

`KeySpec` describes the candidate space. Its shape must agree with the cipher:

| Key space | Cryptanalytic meaning |
| --- | --- |
| `scalar(minimum, maximum)` | One integer chosen from a bounded range, such as a rail count. |
| `repeating(length)` | A fixed-length vector repeated across the text. |
| `repeating_range(minimum_length, maximum_length)` | Repeating content and its length are both search questions. |
| `permutation(length)` | Every position appears once, as required by a column order. |
| `periodic_substitution(...)` | A structured family of substitution alphabets over a period. |
| `periodic_columnar(...)` | Periodic substitution structure combined with a column permutation. |

A concrete key is an answer. A `KeySpec` is the set of answers the solver is
allowed to consider.

Custom key types and their search operations can be implemented during cipher
development. See [key spaces and extension](keyops.md) for the supported shapes
and the contributor route.

## Solver specification: how much search is requested?

`SolverSpec` selects an algorithm and records its work controls: beam width,
rounds, generations, starts, plateau rules, seed and any target score. Larger
budgets may explore more candidates; they do not make the best candidate true.

Initial keys and cribs are prior evidence. When used, their origin matters. A
known answer inserted merely to make a run succeed is not an unknown-key solve.

## Scoring: how are candidates ranked?

`ScoringConfig` defines the evidence used to rank candidates. Character lanes
measure rune-sequence plausibility; word-length lanes use WLI. Their weights,
orders and objective are part of the recipe, not decorative output.

A score is meaningful only under its configured model. It ranks candidates; it
does not certify plaintext.

## Direction and interruptors: what structural evidence applies?

Text direction affects rune tokenisation and WLI interpretation. It must match
the source evidence.

Interruptors are positions left unchanged by a cipher. `exact(...)` supplies
positions already known; `search(...)` supplies a candidate pool and asks RDP to
select positions under explicit bounds. Those are different cryptanalytic
claims.

## RunSpec: one executable statement

The request binds the parts together:

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

There is one ordinary run path. Advanced options extend this request; they do
not create a second solver API.

## RunResult: what happened, and what was found?

Read the result in layers:

| Result section | Question answered |
| --- | --- |
| `key`, `plaintext`, `score` | What was the best candidate returned? |
| `status` | Did execution complete, block or error, and why did it stop? |
| `solver_report` | What work did the solver perform? |
| `scorer_report` | Which scoring lanes and assets were effective? |
| `configuration` | How did requested settings resolve into effective settings? |
| `reproducibility` | Which seed, backend, device, version and assets contextualise the run? |
| `oracle` | Did known truth affect scoring, ranking or stopping? |
| `artifacts` | Which declared evidence files were written? |

Search completion is an execution fact. Exact recovery is a comparison with
known truth. A plausible unknown plaintext is an interpretation supported by
evidence. RDP keeps those statements separate because they are not synonyms.

Continue through the numbered
[`getting_started`](../../tutorials/v1/getting_started/) files, then use the
[`example catalogue`](../../tutorials/v1/README.md) to select a larger problem.
