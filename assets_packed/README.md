# Packed Assets (v1.1)

This folder contains split parts of large benchmark assets, suitable for GitHub file size limits.

- Files in this directory are tracked in git.
- The setup/deploy step recombines these parts into final assets under `assets/`.
- The mapping from final assets -> parts is defined in `assets_manifest_v1.json` at repo root.

Do not manually edit or recombine parts during a benchmark run.
