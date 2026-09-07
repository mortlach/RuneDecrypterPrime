# api.display parameters

The display namespace builds a compact, shareable view of a run. It does not
change solver or scorer behaviour.

## SummaryOptions

| Parameter | Type | Default |
| --- | --- | --- |
| `mode` | `str` | `"standard"` |
| `include_plaintext` | `bool` | `True` |
| `include_ciphertext` | `bool` | `True` |
| `include_key` | `bool` | `True` |
| `include_solver_report` | `bool` | `True` |
| `include_scorer_report` | `bool` | `True` |
| `include_telemetry_summary` | `bool` | `True` |
| `plaintext_preview_chars` | `int` | `500` |
| `ciphertext_preview_chars` | `int` | `240` |
| `max_sequence_preview` | `int` | `40` |
| `include_scope_notes` | `bool` | `True` |

Preview lengths must be non-negative.

Convenience constructors are `standard()`, `for_console()`, `for_tutorial()`,
`for_lp_evidence()` and `for_debug()`.

## build_summary

```python
api.display.build_summary(
    value,
    spec=None,
    scorer_report=None,
    reference_plaintext=None,
    reference_idx=None,
    tutorial_entry=None,
    lp_evidence=None,
    artifacts=None,
    artifact_manifest_path=None,
    options=None,
)
```

| Parameter | Default | Purpose |
| --- | --- | --- |
| `value` | **required** | Result, solver report, or compatible solution-like value. |
| `spec` | `None` | Original `RunSpec` when a complete problem/configuration summary is required. |
| `scorer_report` | `None` | Optional scorer report. |
| `reference_plaintext` | `None` | Optional reference text for display comparison. |
| `reference_idx` | `None` | Optional reference rune indices. |
| `tutorial_entry` | `None` | Optional tutorial metadata mapping. |
| `lp_evidence` | `None` | Optional LP evidence metadata mapping. |
| `artifacts` | `None` | Optional artifact mapping. |
| `artifact_manifest_path` | `None` | Optional display-safe artifact-manifest path. |
| `options` | `None` | Uses `SummaryOptions.standard()`. |

## Summary rendering

`format_summary(summary, **build_kwargs)` returns human-readable text.

`print_summary(summary, file=None, **build_kwargs)` writes the formatted summary.

`write_summary_json(summary, path="artifacts/rdp_display_summary.json")` writes
JSON and returns a display-safe path.

`render_summary(summary, output_format=PrintFormat.TEXT, **build_kwargs)` renders
text or JSON.

`print_result(value, file=None, output_format=PrintFormat.TEXT, options=None,
**build_kwargs)` builds, prints and returns a `DisplaySummary`.

`write_summary_artifact(summary, run_dir=..., options=None, **build_kwargs)`
writes the standard display-summary artifact under a run directory.

## PrintOptions

| Parameter | Type | Default |
| --- | --- | --- |
| `detail` | `PrintDetail | str` | `DETAILED` |
| `width` | `int` | `72` |
| `output_root` | `str` | `"output/"` |
| `banner_style` | `BannerStyle | str` | `PLAIN` |

`width` must be positive. Display paths must be relative and safe to share.

`PrintDetail` values are `COMPACT`, `STANDARD`, `DETAILED` and `DEBUG`.
`PrintFormat` values are `TEXT` and `JSON`. `BannerStyle` values are `PLAIN`
and `BOX`.

## Console formatting helpers

`format_banner` accepts `title="Rune Decrypter Prime"`,
`version_label="RDP V1"`, `output_root=None` and `options=None`.

`format_section(title, underline="-")` creates a section heading.

`format_key_value_block`, `format_preview_block` and `format_status_block`
accept a title, key/value rows and optional `PrintOptions`.

`print_text(text, file=None)` and `print_block(text, file=None)` write plain
console text.

For practical use, see [Displaying results](../../guides/displaying_results.md).

See also [Parameter reference](README.md) and [Defaults at a glance](../defaults.md).
