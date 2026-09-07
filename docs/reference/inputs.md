# Problem inputs

`RunSpec.problem_input` accepts three public types:

```python
api.RawTextInput
api.RuneIndexInput
api.SourceReferenceInput
```

`RawTextInput` starts from a non-empty string.

`RuneIndexInput` starts from canonical rune indices and may carry WLI in its
`word_length_information` field.

`SourceReferenceInput` records a resolver-owned source identity. The built-in
source resolver currently supports Liber Primus labels, locators and partitions.

The exact fields and constraints are listed in
[Problem input parameters](parameters/inputs.md).
