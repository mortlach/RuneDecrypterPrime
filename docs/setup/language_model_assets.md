# Language-model assets

The source checkout and wheels include the smaller LM1/LM2 language-model files.
They are enough for the default LM2 scorer and ordinary getting-started
examples. Runs that request LM3 or LM4 need the larger files as well.

Installing a wheel, using `pip install -e .`, or building the native modules
does not download those extra assets. Choose the setup route below that fits
how you use RDP.

## Get the full V1 models

**[Download the V1 language-model assets](https://github.com/mortlach/rdp_assets/releases/tag/rdp-v1.0.0-lm-large).**

The release contains two ZIP archives. Both are needed for the complete set;
the parts are not separate LM3 and LM4 choices.

- [rdp-v1-lm-large-part001.zip](https://github.com/mortlach/rdp_assets/releases/download/rdp-v1.0.0-lm-large/rdp-v1-lm-large-part001.zip)
- [rdp-v1-lm-large-part002.zip](https://github.com/mortlach/rdp_assets/releases/download/rdp-v1.0.0-lm-large/rdp-v1-lm-large-part002.zip)

Together they are about 900 MB to download. These are data archives from
`mortlach/rdp_assets`, separate from the RDP package wheels and source archives.

### Normal source installation

From the repository root:

```text
python install.py
```

The installer installs RDP and obtains and verifies the full LM1-LM4 profile.
See [Installation](installation.md) for the other installation steps.

### Assets only, without reinstalling RDP

Use this route if you already run from source, have an editable install, or
only want to prepare the model files.

From the repository root, start Python 3.11 or newer and run:

```python
from pathlib import Path
from tools.assets.release_asset_installer import install_release_asset_set

checkout = Path.cwd()
install_release_asset_set(
    manifest_path=checkout / "assets/manifests/assets_manifest_v1.json",
    asset_set_name="v1_lm_runtime_full",
    download_dir=checkout / "downloads",
    assets_root=checkout / "assets",
)
```

This is the asset step used by the installer. It downloads or reuses the two
archives, verifies their hashes and sizes, extracts the runtime files, and
verifies the installed set. It does not install RDP, build extensions or change
your Python dependencies; the helper itself uses only the Python standard
library.

For manual downloads or offline preparation, place both ZIPs in the checkout's
`downloads/` directory with their original filenames, then run the same
snippet. Valid local archives are reused without downloading them again.
Missing or invalid archives cause a download attempt.

The prepared model root is `assets/language_model/lmp/`. It contains
`index.json`, `char/`, `wli/` and `ecdf/`. Leave the `.bin.zst` and
`.npz` runtime files in their stored formats.

Use the helper rather than extracting the ZIPs over the checkout yourself:
it keeps the verified source-bundled `index.json` instead of overwriting it
with the copy in the archives. Source and editable installs use the prepared
checkout assets by default.

### Installed wheel or a separate model directory

A wheel contains the small bundled profile, not the asset-download tools.
To prepare the full models without reinstalling the wheel, obtain the
[V1 source checkout](https://github.com/mortlach/RuneDecrypterPrime/tree/v1.0.0)
and follow the assets-only steps above. You can use GitHub's source ZIP;
installing that checkout as a Python package is not required for the helper.

You can then use the prepared `assets/language_model/lmp/` directory in place,
or copy that whole directory somewhere convenient. Keep `index.json`,
`char/`, `wli/` and `ecdf/` together.

In the Python environment where you use RDP, set the model root explicitly:

```python
from pathlib import Path
from rdp import api

# Replace this with your prepared lmp directory.
lm_root = Path("/path/to/assets/language_model/lmp").resolve()

scoring = api.ScoringConfig(language_model_root=lm_root)
```

On Windows, for example, the path could be
`Path("D:/rdp-data/language_model/lmp")`. Use an absolute path to the directory
containing `index.json`, not to a ZIP, the outer `assets/` directory, or
`index.json` itself.

Pass this configuration as `scoring=scoring` to `api.score()`,
`api.score_many()` or `api.RunSpec(...)`. If your experiment already has a
scoring configuration, preserve its settings and change only the model root:

```python
from dataclasses import replace

scoring = replace(scoring, language_model_root=lm_root)
```

Selecting a model directory does not select an n-gram order or change the
scoring recipe. Keep the orders and other settings your experiment requires.
For a wheel, preparing data beside an unrelated checkout does not change its
default asset location: supply `language_model_root` in the scoring
configuration. There is no model-root environment-variable or working-directory
search. `RDP_OUTPUT_ROOT` controls generated output, not model inputs.

## Profiles, manifests and verification

The `ci_light` profile is the source-bundled subset used by ordinary push/PR CI.
The `full_v1` profile is the full LM1-LM4 setup, including the data needed by
the full two-period and periodic-substitution examples. They use the same RDP
code; requested models must be present.

The machine-readable definitions are:

- [Asset profiles](../../assets/manifests/asset_profiles_v1.json)
- [CI-light manifest](../../assets/manifests/assets_manifest_ci_light_v1.json)
- [Full V1 manifest](../../assets/manifests/assets_manifest_v1.json)
- [Runtime index](../../assets/language_model/lmp/index.json)

The full manifest pins the release archives and installed runtime files.
The helper verifies SHA-256 and byte size for both; a missing or corrupt
required asset fails clearly. A requested LM3/LM4 setup never silently
downgrades to LM2.

Large model files belong in release assets, not normal Git history.
Unreferenced shard side-products and local audit files are not release assets.

Packaging and runtime asset-path tests check that an installed wheel resolves
its own bundled data. Tests requiring the full models keep their
`full_assets` marker. When changing an asset release payload, update its pinned
identity, hashes and sizes in the manifests, then qualify it through
[full release validation](../development/README.md#release-validation).
