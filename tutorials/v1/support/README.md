# Example support

The worked examples share helpers here so each script can concentrate on its
cipher and search settings.

`tutorial_pretty.py` and `tutorial_output.py` format output.
`tutorial_utils.py` includes reference-score calculation for stopping a search,
and `tutorial_reference.py` compares results with the original text. The report,
session-report and benchmark modules collect more detailed run information.
`scheduled_stream_lookup.py` prepares inputs for the related stream examples.

Keep the important choices in the calling example, including its cipher,
search budget and any use of a known answer to set a stopping score. See the
[worked examples](../examples/README.md) for how these helpers are used.
