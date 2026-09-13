# Language-model assets

A normal source install uses the `full_v1` profile: LM1 through LM4.
The smaller LM1/LM2 files are bundled with the source and form the `ci_light`
profile used by ordinary push/PR CI. LM3/LM4 are required for runs that request
those orders, including the full two-period and periodic-substitution routes.

Run `python install.py` to install or verify the full profile. If automatic
download is unavailable, put the pinned release archives in `downloads/` and
rerun the installer. See [Installation](installation.md).

## Manifests and runtime files

The machine-readable definitions are:

- [Asset profiles](../../assets/manifests/asset_profiles_v1.json)
- [CI-light manifest](../../assets/manifests/assets_manifest_ci_light_v1.json)
- [Full V1 manifest](../../assets/manifests/assets_manifest_v1.json)

The source runtime files live under `assets/language_model/lmp/`. Its
[index](../../assets/language_model/lmp/index.json) selects the runtime tables;
unreferenced shard side-products and local audit files are not release assets.

The full manifest pins the large-model release payload in `mortlach/rdp_assets`
at `rdp-v1.0.0-lm-large`. Large model files belong in release assets, not normal
Git history.

The installer verifies SHA-256 and byte size for both downloaded archives and
final installed files. Extraction is path-safe; missing or corrupt required
assets fail clearly. A requested LM3/LM4 setup never silently downgrades to LM2.

## Wheels and validation

Wheels bundle the verified CI-light subset. Installing a wheel alone does not
provide the full LM3/LM4 set; the source installer is the normal complete V1
setup route. Packaging and runtime asset-path tests check that an installed
wheel resolves its own data rather than falling back to checkout assets.

CI-light is a validation-cost choice, not a reduced product capability.
Tests requiring large models keep their `full_assets` marker.
When changing a release payload, update its pinned release identity, hashes
and sizes in the manifests, then qualify it through
[full release validation](../development/README.md#release-validation).
