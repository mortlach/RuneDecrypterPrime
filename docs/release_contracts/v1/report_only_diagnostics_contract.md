# V1 report-only diagnostics contract

Report-only diagnostics may add observability, but they are score-neutral.

A report-only scorer lane must satisfy all of the following:

- `rank_effect == RankEffect.REPORT_ONLY`
- unavailable diagnostics do not raise requested-production lane errors
- available diagnostics stay visible as report-only
- production lane statuses do not change when a report-only lane is enabled
- ranking, raw score, solver ordering, and tie-breaks do not depend on report-only diagnostics

Current V1 report-only lanes:

- `word_ngram_judge_report_only`
- `ngram_hamming_experimental_report_only`

Report-only metadata belongs in reports/details/telemetry. It must not be used as a scoring component.
