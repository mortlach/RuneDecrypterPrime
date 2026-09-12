# V1 asset and CI profiles

This is the A1 contract for V1 language-model assets and validation tiers.

## Canonical asset profiles

The repository has exactly two named profiles, defined in
`assets/manifests/asset_profiles_v1.json`.

### `ci_light`

`ci_light` is the normal push and pull-request profile. It uses only the
source-bundled LM1/LM2 `nose` assets, does not download GitHub Release bundles,
runs pytest with `not full_assets`, and runs `TutorialRunSet.RELEASE`.

This profile controls CI cost. It is not the complete product capability claim.

### `full_v1`

`full_v1` is the normal user install and release-proof profile. It verifies or
downloads the complete supported LM1-LM4 runtime asset set. The authoritative
full proof then runs the canonical 53-job validator, including complete pytest,
and the separate bounded `FULL_ASSET_EXAMPLES` selection.

The default public install remains:

```text
python install.py
```

It must fail clearly when required full assets cannot be obtained or verified.
It must not silently downgrade the accepted LM1-LM4 scorer design to LM1/LM2.

## Test marker contract

Tests that require the installed full LM1-LM4 profile use:

```text
@pytest.mark.full_assets
```

The cheap push/PR gate excludes that marker. The full-proof gate does not. Tests
that only inspect the full-profile contract or exercise fake asset bundles may
run under `ci_light`.

## Tutorial profile contract

Full-asset exceptions are explicit filename sets in
`tutorials/v1/run_tutorials.py`. The human catalogue in
`tutorials/v1/README.md` records the corresponding requirement and truth use.

The two-period crib tutorials require `full_v1` because their accepted F1 judge
uses character and WLI orders 1-4. Labels must describe the assets actually
required; a successful cached run does not justify a narrower label.

## Workflow contract

There are two authoritative validation workflows:

1. `.github/workflows/rdp_v1_full_ci.yml` is the cheap automatic push and
   pull-request gate. It installs `ci_light`, excludes `full_assets` tests and
   runs the `RELEASE` tutorial set on Python 3.11 for Windows and Ubuntu.
2. `.github/workflows/rdp_v1_full_proof.yml` is the authoritative release/main
   proof: `workflow_dispatch` plus automatic `push` to `main` only. It installs
   `full_v1` with `python install.py`, runs `python tools/run_validation.py` with
   `RUN_SET = 'all'` and `INCLUDE_LONG_P7C7_EXAMPLE = True`, and requires 53/53 PASS
   on Python 3.11 for Windows and Ubuntu. The separate `FULL_ASSET_EXAMPLES`
   gate remains. Release-branch pushes and pull requests do not trigger this
   heavy workflow automatically; the final frozen candidate is dispatched manually.

The `QUALIFICATION` tutorial group is not selected wholesale. The canonical
validator includes the long production P7/C7 example individually in the rare
full proof; it must not be removed to reduce CI cost. The other longer
qualification programs remain outside that catalogue.

The full proof also reuses the qualified native package build/installed-wheel
contracts and pinned Pyodide B1-B8 procedure. It preserves validator logs and
summaries, uploads SHA-identified artifacts/checksums, and fails unless every
required hosted job passes. CUDA is not exercised on hosted runners; prior
qualified CUDA evidence remains separate. See
[V1 release acceptance gates](V1_RELEASE_ACCEPTANCE_GATES.md#ci-gate).

Other packaging and Pyodide workflows remain manual and explicitly
non-authoritative diagnostics. They do not replace either authoritative gate.

## Release asset contract

`assets/manifests/assets_manifest_v1.json` remains the file-and-hash authority. The
`v1_lm_ci_light` set identifies the exact source-bundled files. The
`v1_lm_runtime_full` set identifies the complete supported installation and the
pinned GitHub Release bundles used to obtain missing large files.

The release bundle builder must regenerate both set labels consistently.
