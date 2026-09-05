# Asset maintenance

`asset_profiles.py` defines profile selection. The audit and large-release-bundle
scripts inspect or package full models; `release_asset_installer.py` installs the
selected release assets. The CI-light and full profiles serve different workloads. Use
existing manifests for integrity and keep external model packs out of source control.

Continue with the [related guide](../../docs/setup/installation.md).
