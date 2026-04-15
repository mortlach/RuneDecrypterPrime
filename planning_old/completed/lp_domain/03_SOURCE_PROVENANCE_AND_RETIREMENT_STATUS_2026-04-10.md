# LP registry review bundle provenance and retirement status

Status: completed-home provenance mapped
Work status: done for first provenance pass
Project: completed/lp_domain

## Purpose

This note records where the LP registry review bundle now lives inside the new
planning system and what remains of the old source surface.

## Preserved working copy inside the new system

Canonical preserved review bundle:
- `planning/completed/lp_domain/review_bundle/`

Preserved evidence snapshot:
- `planning/completed/lp_domain/95_evidence_snapshots/lp_registry_review_bundle.zip`

## Old source provenance

Original old source surface:
- `planning/drafts/lp_registry_review_bundle/`
- `planning/drafts/lp_registry_review_bundle.zip`
- `planning/old/lp_domain_spec_v1.txt`
- `planning/old/lp_domain_implementation_plan_v1.txt`
- `planning/old/lp_registry_integration_review_20260307.txt`

These old paths were provenance residue during migration and have now been
retired from their old surfaces.

## Retirement read

Directory source:
- absorbed into `review_bundle/`
- old copy is retired from `planning/drafts/`

Zip source:
- now explicitly preserved in `95_evidence_snapshots/`
- old copy is retired from `planning/drafts/`

Completed LP-domain source docs:
- now explicitly preserved in `source_docs/`
- old copies are retired from `planning/old/`

## Working rule

When completed-home docs need to reference the LP registry review bundle, point
to:
- `review_bundle/` for readable preserved content
- `95_evidence_snapshots/lp_registry_review_bundle.zip` for zipped provenance

Do not send readers back to `planning/drafts/` unless a source-provenance
or `planning/old/` unless a source-provenance question specifically requires
the historical retired path.
