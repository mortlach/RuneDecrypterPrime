# Installed-package checks

`install_light.py` installs the CI-light profile. The `a5_installed_*_smoke.py` scripts
check installed-wheel and tutorial behaviour, while `a5_artifact_contract.py` inspects
release artifacts. These are validation entry points with their own costs; ordinary
edits should use only the checks relevant to the changed boundary.

Continue with the [related guide](../../docs/setup/install_validation.md).
