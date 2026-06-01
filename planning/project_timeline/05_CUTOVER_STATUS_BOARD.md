# Cut-over status board

This is the short board for how close each active home is to acting as default
planning truth.

| Home | Current cut-over status | Main blocker |
|---|---|---|
| `rdp_v1` | coherent and promoted | no remaining old-path source copy |
| `benchmark_campaign_v1_1` | coherent and usable | support/archive trimming still pending, but the old `planning/drafts/` surface is gone |
| `p13_real_ciphertext_campaign` | coherent and usable as a thin downstream home | method/run maturity is still earlier-stage, but not a planning-structure blocker |
| bundle-wide control layer | canonical and promoted | no structural blocker; only the explicit `planning/no_wli/` exception and `planning/working/` stub remain outside the bundle, and the no-WLI internal legacy residue is now retired |

## Practical reading

Today's bundle is the **main working planning surface**.

Practical stance:
- use this bundle by default now
- keep `planning/no_wli/` explicit as an upstream live exception
- treat `planning/working/` as a deprecated compatibility stub only
