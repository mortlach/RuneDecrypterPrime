# Problem inputs

`RunSpec.problem_input` accepts two public types:

```python
api.RuneInput
api.SourceReferenceInput
```

`RuneInput` accepts rune indices, rune glyphs, delimited RuneLatin, or English.
It infers and records the representation; `RuneInputFormat` provides an
explicit override for ambiguous text. Text input derives word boundaries from
spaces. Index input may carry `word_length_information`.

`SourceReferenceInput` records a resolver-owned source identity. The built-in
resolver supports Liber Primus labels, locators, and partitions.

See [Problem input parameters](parameters/inputs.md) for the exact fields and
constraints.
