# Current state

Status: active
Work status: in_progress
Project: project_workflow

## Short read

This is the project about projects.

Its job is to define:
- what counts as a project home
- what the standard active-project shape is
- how agents should update, log, and preserve planning work
- how rescued legacy material should sit behind a clean live layer

## Why it exists now

The bundle now contains enough rescued material that the main problem has
changed.

The main problem is no longer discovery.
It is normalisation.

We now need:
- one standard shape for active projects
- one lighter standard shape for completed/archive homes
- one consistent update/logging workflow for future chats and agents

## Current scope

Primary scope:
- define the standard schema
- define project-definition rules
- define agent update/logging rules
- map current active homes into the target shape
- execute that normalisation one project at a time

## Current progress

Real schema-normalisation passes completed:
- `no_wli`
- `rdp_v1`
- `benchmark_campaign_v1_1`
- `p13_real_ciphertext_campaign`

Still to do:
- lighter completed/archive simplification
- any final tidy pass only if it improves readability
