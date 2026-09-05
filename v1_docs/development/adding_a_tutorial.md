# Adding runnable V1 material

Status: contributor reference

## Choose the right home

- Add a numbered `getting_started/` file only when it closes a demonstrated gap
  in ordinary use.
- Add an `examples/` file for a stable worked problem, meaningful comparison,
  novel V1 feature or real source workflow.
- Add a regression-only case to `tests/`.
- Keep exploratory work without a stable result in the relevant development
  area.

Use a descriptive lowercase `snake_case.py` filename. A direct example command
should look like:

```text
python tutorials/v1/examples/descriptive_name.py
```

## Required evidence

The file must state one purpose and declare its asset requirement, approximate
runtime, deterministic seed where applicable, semantic acceptance condition,
and truth/oracle use. It must exit non-zero when that condition is not met.

Prefer `from rdp import api`. Repository support is acceptable only when the
example’s stated purpose genuinely requires it, and the catalogue must say so.

## Registration

Add the file to `tutorials/v1/README.md`. Change an explicit set in
`tutorials/v1/run_tutorials.py` only when the example belongs in `RELEASE`,
requires full assets, or is a long qualification. `BUNDLED_EXAMPLES` otherwise
discovers it automatically.

Add focused tests for behaviour, seed/budget, truth separation and any asset or
runtime boundary. Do not add a source hash, prose-output snapshot or parallel
manifest merely to register the file.
