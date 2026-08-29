# Data and word-length information

Public run inputs are typed:

- `api.RawTextInput` for text that must be encoded;
- `api.RuneIndexInput` for already-normalized rune indices and optional
  word-length information;
- `api.SourceReferenceInput` for a supported source reference.

```python
from rdp import api

problem = api.RuneIndexInput(
    indices=(0, 1, 2, 3),
    word_lengths=((0, 2), (1, 2), (0, 2), (1, 2)),
)
```

Rune indices are validated against the 29-symbol alphabet. Word-length pairs
describe each rune's position and word length; spaces are not rune indices.
`RunSpec.word_length_policy` controls how missing information is handled.

Packaged source references are resolved by `rdp.api` and then materialised by
the existing data owners. Scoring models and large assets remain implementation
data, not public configuration objects.
