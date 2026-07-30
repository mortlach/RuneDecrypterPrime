# V1 Large Language Model Assets

LM3 and LM4 assets are required full V1 release assets.

They are needed for the public V1 capability set, especially the PeriodicSubstitution path. They must not be committed into normal Git history. The release source of truth is the GitHub Release payload, and the runtime install location remains:

```text
assets/language_model/lmp/
```

The first V1 release candidate set is the 129 files implied by the root `assets/language_model/lmp/index.json`. The unreferenced WLI n4 shard side-products and local ECDF audit files are excluded until their purpose is proven.

In the current approved root-index set, 64 files are marked `v1_lm_large_required` because they are the index-implied n=3/n=4 runtime files. Earlier local audit notes counted 96 n=3/n=4-like files because that count included 32 unreferenced WLI part files. Those 32 files are not in the first release bundle.

The release contract separates two things:

```text
release bundle assets
final installed runtime assets
```

Installers must verify SHA256 and byte size for both. They must use path-safe extraction, reject corrupt assets, and fail clearly if required LM3/LM4 assets cannot be installed. They must not silently downgrade to LM2 for the full V1 path.

Normal CI verifies the exact source-bundled `v1_lm_ci_light` LM1/LM2 set and uses fake bundles only in focused installer tests. That split is only a workflow-cost control; it does not change the product contract. `python install.py` remains the full V1 install and must install or verify LM3/LM4 by default.

The current manifest points at the final V1 asset release:

```text
mortlach/rdp_assets
rdp-v1.0.0-lm-large
```

If the asset release is rebuilt, update the tag, SHA256 values, and sizes, then rerun `.github/workflows/rdp_v1_full_proof.yml`. Real large-asset validation remains a manual release gate before publication.
