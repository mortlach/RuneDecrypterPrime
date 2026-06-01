# Community Benchmark -> V1 Release TODO

## Goal
Move from internal validation to:
1) a friendly community benchmark push (v1.1 campaign), then
2) a clean, stable RDP v1 release candidate.

---

## Track A: Community Benchmark Push (v1.1)

### A0. Freeze campaign baseline
- [ ] Freeze campaign git SHA for community testing.
- [ ] Freeze `campaign_config_v1_1.json` + `profile_catalog_v1_1.json`.
- [ ] Freeze schema versions (`manifest_schema_v1_1.json`, `result_schema_v1_1.json`).
- [ ] Record frozen versions in a short `campaign_release_notes.md`.

### A1. Asset packaging + distribution
- [ ] Decide artifact channel:
  - [ ] Option 1: keep split parts in `assets_packed/`.
  - [ ] Option 2: move large payloads to GitHub Release assets.
- [ ] Keep/produce `assets_manifest_v1.json` with sha256 + size for each final asset.
- [ ] Verify recombine path in setup (`assets_packed` -> `assets`) is atomic and idempotent.
- [ ] Add explicit failure messages for missing part / hash mismatch / size mismatch.

### A2. `_fastlm` multi-target binaries
- [ ] Publish prebuilt wheels/binaries for:
  - [ ] win_amd64
  - [ ] win_arm64
  - [ ] manylinux_x86_64
  - [ ] manylinux_aarch64
  - [ ] macos_arm64 (or universal2)
- [ ] Add setup logic: install matching prebuilt first, build fallback second.
- [ ] Keep compliance rule: official leaderboard requires `fastlm_present=true`.
- [ ] Keep non-compliant mode allowed for local debugging only.

### A3. Setup + preflight hardening
- [ ] Verify setup writes all required artifacts:
  - [ ] `setup.log`
  - [ ] `setup_report.json`
  - [ ] `preflight.log`
  - [ ] `preflight_report.json`
  - [ ] `benchmark_ready.json`
- [ ] Add explicit preflight checks for:
  - [ ] CPU backend only
  - [ ] scoring backend numpy
  - [ ] LM asset hash verification
  - [ ] `_fastlm` presence
- [ ] Re-run `tests/community` after all setup changes.

### A4. Friendly community pilot
- [ ] Run mandatory canary campaign first (6-12 jobs).
- [ ] Pilot with at least 3 environments:
  - [ ] Windows x64 (maintainer reference run)
  - [ ] Windows ARM64 volunteer
  - [ ] Linux x64 or ARM64 volunteer
- [ ] Collect pilot bundles and run `validate_run_bundle.py` on all bundles.
- [ ] Fix onboarding/documentation issues found in pilot before wider invite.

### A5. Community launch readiness gate
- [ ] Confirm bundle validation passes for pilot submissions.
- [ ] Confirm deterministic manifest/shard generation on two different machines.
- [ ] Confirm resume behavior logs `RESUME_SKIP_ALREADY_RECORDED`.
- [ ] Publish "How to run a shard" and "How to submit run_bundle" one-pagers.
- [ ] Mark campaign state as `community-ready`.

---

## Track B: Repo Tidy-Up for RDP V1

### B0. Branch and scope freeze
- [ ] Create/announce `release/v1` branch.
- [ ] Define what is in v1 vs deferred to v1.1+.
- [ ] Freeze solver-tuning churn during release hardening window.

### B1. Repository hygiene
- [ ] Remove or archive obsolete experimental files/scripts.
- [ ] Ensure generated artifacts are ignored or moved out of source tree.
- [ ] Enforce output-path policy (v1 rule):
  - [ ] all tool/test/benchmark generated files must write under `output/`
  - [ ] output paths should mirror repo structure (example: `tools/benchmarks/periodic_sub_trans/...` -> `output/tools/benchmarks/periodic_sub_trans/...`)
  - [ ] no writes to source directories except intentional tracked fixtures/configs
- [ ] Normalize folder structure for:
  - [ ] `src/`
  - [ ] `tools/benchmarks/community/`
  - [ ] `docs/`
  - [ ] `planning/`
- [ ] Ensure no local-only absolute paths remain in tracked files.

### B2. Documentation completeness
- [ ] Add a top-level Quick Start for contributors.
- [ ] Add benchmark campaign quick path (setup -> canary -> shard -> bundle).
- [ ] Add troubleshooting page:
  - [ ] missing assets
  - [ ] `_fastlm` build/install failure
  - [ ] ARM64 fallback behavior
- [ ] Add release notes for solved benchmarks + known limitations.

### B3. CI and test gates
- [ ] CI matrix includes at least:
  - [ ] Windows x64
  - [ ] Linux x64
  - [ ] one ARM64 target (native or emulated runner)
- [ ] Add mandatory checks before merge to `release/v1`:
  - [ ] unit/integration tests pass
  - [ ] community setup/preflight smoke test
  - [ ] benchmark schema validation smoke
- [ ] Define minimum acceptance gate for v1 tag.

### B4. Packaging and release
- [ ] Build release artifacts (code + required benchmark tooling).
- [ ] Publish checksums/signatures for release artifacts.
- [ ] Tag release candidate (`v1.0.0-rc*`) then final (`v1.0.0`).
- [ ] Publish post-release support plan (issue template + triage cadence).

---

## Exit Criteria

### Community benchmark push complete when:
- [ ] Friendly pilot passes canary + shard + bundle validation on mixed targets.
- [ ] Setup/preflight is reproducible and documented.
- [ ] Asset + `_fastlm` distribution path is stable.

### V1 release complete when:
- [ ] Repo is tidy and structure is stable.
- [ ] CI + docs + release artifacts are complete.
- [ ] `v1.0.0` tag is published with release notes.
