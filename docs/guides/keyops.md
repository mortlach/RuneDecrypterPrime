# Keys and key spaces

A concrete key contains actual values. `api.KeySpec` describes the candidates a
solver is allowed to consider. Keeping these separate lets you specify what is
known about a key without supplying the answer.

## Choose a shape that matches the cipher

| Constructor | Meaning | Useful choice |
| --- | --- | --- |
| `scalar(minimum=2, maximum=8)` | One integer, such as a rail count. | Widen the bounds to include more candidates. |
| `repeating(length=4)` | Four values repeated across the text. | Change the length when testing a different period. |
| `repeating_range(minimum_length=3, maximum_length=6)` | Search both content and length. | Use when the period is part of the question; expect more work. |
| `permutation(length=7)` | An ordering containing each element once. | Use for column orders or a substitution alphabet of the appropriate size. |
| `periodic_substitution(...)` | Structured substitution alphabets over a period. | Set the period to match the proposed cipher. |
| `periodic_columnar(...)` | Periodic substitution plus column-order structure. | Keep the period and column count consistent with the cipher. |

These are methods on `api.KeySpec`. They are alternatives for different problem
shapes, not interchangeable settings on every cipher.

```python
from rdp import api

cipher = api.CipherSpec.vigenere()
key_space = api.KeySpec.repeating(length=4)
```

Repeating keys also support `with_fixed_alignment(offset=...)` and
`with_alignment_search(minimum_offset=..., maximum_offset=...)`. These describe
where the repeating key begins relative to the text. Use a fixed alignment when
it is known; search a bounded alignment range when it is another unknown.

## How the solver changes keys

Internally, key operations generate candidates and provide operations such as
mutation and recombination. Each implementation preserves the appropriate
invariants: a permutation must remain a permutation, while a rune-value vector
must retain its valid length and values. The solver chooses how to explore;
key operations define the changes it can make.

Custom key types and their search operations can be implemented as part of
cipher development. Start with the key's layout and validity rules, then provide
the operations needed by the intended solver. Runtime registration and public
API support are separate integration steps; a custom class is not automatically
accepted by the existing public `KeySpec` constructors.

Read the [key-operation source map](../../src/rdp/keyops/README.md), then
[build a cipher and key operations](../howto/build_keyops.md) for the contributor
route. For ordinary use, return to [the first search](../../tutorials/v1/getting_started/02_first_search.py).
