# Displaying results

`RunResult` is the main programmatic result from `api.run(...)`.

For a quick human-readable view, RDP also provides `api.display`.

## Print a result

```python
result = api.run(request)

api.display.print_result(
    result,
    spec=request,
)
```

Passing the original `RunSpec` lets the display include the problem, cipher,
key-space and scoring choices as well as the result.

The display is a view of the existing run data. It does not change the result.

## More or less detail

The standard display options are available through `SummaryOptions`.

For a compact console view:

```python
options = api.display.SummaryOptions.for_console()

api.display.print_result(
    result,
    spec=request,
    options=options,
)
```

For a more detailed debugging view:

```python
options = api.display.SummaryOptions.for_debug()

api.display.print_result(
    result,
    spec=request,
    options=options,
)
```

The available fields and defaults are listed in
[Display parameters](../reference/parameters/display.md).

## Build a summary without printing it

A display summary can also be built directly:

```python
summary = api.display.build_summary(
    result,
    spec=request,
)
```

It can then be rendered as text or JSON:

```python
text = api.display.render_summary(summary)

json_text = api.display.render_summary(
    summary,
    output_format="json",
)
```

A notebook or report can therefore use the standard RDP summary without writing
it to the console.

## What belongs in the display

The display can bring together:

- problem input
- cipher and key-space choices
- solver and scoring configuration
- recovered key and plaintext
- stop reason
- solver and scorer reports
- telemetry
- oracle use
- artifact paths

The underlying objects remain available separately. For detailed programmatic
work, use `RunResult` directly.

Plaintext entries inside the JSON display retain the public result meanings:
`plaintext_indices`, `word_length_information`, `plaintext_runes`,
`plaintext_rune_latin`, and `plaintext_reading_rune_latin`. Canonical RuneLatin
uses exact rune labels with `·` between tokens and spaces between words; the
reading field applies direction-aware presentation. Generic ciphertext and
debug previews use `rune_indices`, `rune_text`, `rune_latin`, and
`reading_rune_latin` with the same distinction. A compact undelimited
transliteration, when one is available from an internal result, is identified
separately as `plaintext_latin_compact`.

The `Artifacts` section lists files that exist or paths supplied by the caller.
In particular, `display_summary_relpath` is added only by
`write_summary_artifact(...)` after it writes the display-summary sidecar;
printing or merely building a summary does not advertise that path.

See [Reading a result](results.md),
[Telemetry](telemetry.md) and [Outputs](outputs.md).

## Runnable example

`tutorials/v1/getting_started/08_reading_a_result.py` uses the same result
inspection path and points to `api.display.print_result(...)`.

See [Tutorials and examples](../tutorials/README.md).

## Front-end integration

A GUI should retain typed `RunSpec` and `RunResult` objects and use public display
helpers for presentation. Load serialized state through the existing parsers,
then keep typed objects. Show stop status, blocked capabilities, oracle use,
partial recovery and artifact status explicitly.

Console wording and the human tutorial catalogue are not machine protocols.
A front end owns its navigation metadata rather than parsing example scripts.
