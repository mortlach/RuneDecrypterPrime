# Documentation Playbook

Audience: Hands-on / Expert
Time: 3-5 minutes
Outcome: Apply consistent structure, tone, and cross-linking across docs
Prereqs: None

This guide describes how we create and maintain repo docs when iterating with ChatGPT/Codex.

## Principles
- Single source of truth - narrative pages reference code paths (for example src/rdp/core/types.py) so reviewers can jump straight to implementations.
- Neutral, concise voice - explain facts and decisions; avoid hypey language. Use the imperative for procedures and present tense for ongoing guarantees.
- Cross-link everything - every tutorial should link to scoring/backends/telemetry sections so readers can travel between guides without context loss.
- Determinism reminders - mention seeds, telemetry obligations, and output/ paths in each how-to so contributors do not miss the mission charter.

## Working With ChatGPT / Codex
1. State intent up front - include the file, the desired change, and acceptance criteria.
2. Ask for deltas, not rewrites - highlight the paragraphs that need edits so the assistant keeps surrounding context.
3. Review generated text - verify terminology, enum names, and links before committing. Re-run rg for TODOs or stray personal info.
4. Cross-link before finishing - after generating content, add reference links (for example see telemetry.md) so the docs stay interwoven.
5. Record guardrails - if a change affects determinism, telemetry, or output locations, capture that explicitly in the PR/commit description.

## Recommended Structure For New Pages
- Purpose / scope
- Required context and prerequisites
- Step-by-step procedure (code snippets and commands)
- Telemetry/output expectations
- Links to tests, tutorials, or APIs exercising the feature
- Troubleshooting or FAQ section

## Tooling
- Generate symbol indexes or release artifacts via `python tools/repo_utils/index_project_symbols.py` and `python tools/repo_utils/share_package.py`; both write to `output/share/<timestamp>` so no personal paths leak.
- Keep docs in UTF-8 and prefer ASCII punctuation unless the file already uses typographic quotes/dashes.

