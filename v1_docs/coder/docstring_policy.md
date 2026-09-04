# Docstring Policy

Status: staged V1 draft

Owner paths:
- `src/rdp/`

Related tests:
- `tests/docs/test_v1_coder_docs_contract.py`

Stability:
- Semi-stable contributor surface

## Purpose

This page sets the rule for future code annotation. The goal is useful coder
documentation, not thousands of low-value comments.

## Policy

| Code surface | Documentation expectation |
| --- | --- |
| Public classes/functions | Full docstring covering purpose, arguments, return value, raised errors where important, and contract notes. |
| Dataclasses/config objects | Document every field, plus validation/default behaviour. |
| Public factories | Document purpose, accepted arguments, returned object, raised errors, and a short example when useful. |
| Solver code | Document seed behaviour, effective seed behaviour, stopping behaviour, randomness, and backend assumptions. |
| Scoring code | State whether values affect ranking, stopping, tie-breaks, candidate selection, or diagnostics only. |
| Report/artifact code | Distinguish stable contract fields from review-only details. |
| Complex private helpers | Add a short explanation of why the helper exists. |
| Simple private helpers | No forced docstring. |

## Style

- Prefer plain English.
- Keep exact code names unchanged.
- Use British spelling in prose only when natural.
- Use Sphinx/Napoleon-compatible docstrings where new docstrings are added.
- Avoid comments that restate one obvious line of code.
- Do not document a helper as public just because it is importable.

## Annotation Order

1. Public spec/report/config objects.
2. Public factories and builders.
3. Pipeline boundaries where silent drift would be risky.
4. Complex private helpers that explain validation, determinism, or fallback
   behaviour.

Do not start with a mass annotation pass.
