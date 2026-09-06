# Robustness campaigns

Robustness campaigns test behaviour across multiple cases, recipes or seeds.

They are not part of ordinary onboarding and should not be used in place of a
focused test.

The current campaign runner is:

```text
cipher_solver_campaign.py
```

with configuration under:

```text
cipher_solver_campaign_config.py
```

Retained fixtures live under `fixtures/`.

## What a campaign is for

A campaign is appropriate when the claim depends on repeated behaviour:

```text
recovery rate across generated cases
solver behaviour across seeds
cipher/solver combinations
regression against retained fixtures
```

A single successful example cannot answer those questions.

Conversely, a documentation change does not need a multi-hour campaign.

See [Development](../../docs/development/README.md) and
[Comparing solve experiments](../../docs/guides/working_a_solve.md).
