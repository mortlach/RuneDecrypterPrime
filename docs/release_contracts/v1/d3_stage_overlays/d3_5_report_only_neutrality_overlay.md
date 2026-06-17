# D3.5 report-only neutrality overlay

Scope: report-only scorer-lane neutrality.

Changed file:

- `tests/scoring/test_report_only_lanes_do_not_rank.py`

Locked behaviour:

- Enabling word-ngram diagnostics does not change production lane report JSON.
- Word-ngram diagnostics stay report-only and non-blocking.
- No scoring or solver behaviour is changed.
