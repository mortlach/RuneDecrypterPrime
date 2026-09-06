# Liber Primus sources

This package identifies and reads Liber Primus material, then builds aligned
ciphertext, WLI and source metadata.

Source selection and solve method remain separate.

## Main owners

- `lp_source_catalogue.py` owns named source and solve-recipe entries
- `lp_registry.py` owns typed page, locator and partition identities
- `lp_adapter.py` builds solver payloads
- `lp_transcript.py` parses and indexes the transcription
- `lp_main.py` resolves identities against the main transcript
- `lp_routes.py` implements line and spiral reading routes
- `lp_data.py` builds section/page data

For a known source label:

```python
payload = api.liber_primus.payload_from_label(
    "welcome_pilgrim"
)
```

Loading a solved source does not run a solver.

Changing a locator or reading route changes the source evidence supplied to the
solve.

See [Liber Primus data](../../../../docs/reference/liber_primus.md) and
[Ciphertext input](../../../../docs/guides/ciphertext_input.md).
