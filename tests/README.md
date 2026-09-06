# Tests

Tests are organised around the behaviour they protect.

Start with the component changed by the patch rather than the largest available
test set.

## What the tests cover

The suite includes:

- public API and request validation
- cipher and key-operation behaviour
- solver behaviour and reproducibility
- scoring and asset contracts
- Liber Primus source handling
- logging and artifact policy
- packaging and installed-wheel checks
- retained release contracts

Some solver, asset and qualification tests are expensive.

## Choosing a test

Start with the narrowest test that exercises the changed behaviour.

Examples:

```text
cipher change       -> cipher tests + relevant API binding test
KeyOps change       -> keyops tests + one solver integration test
solver change       -> solver tests + deterministic public route
scoring change      -> scorer/capability tests + one integrated run
LP source change    -> LP data/source tests
logging change      -> logging/artifact tests
```

Run larger validation only when the question requires it.

For the distinction between a focused test, smoke run and qualification
campaign, see [Development](../docs/development/README.md).

## Shared test support

`conftest.py` contains shared pytest fixtures.

`harness.py` supports controlled test execution.

Read a test before running it when it uses large assets or long solver
campaigns.

## Long campaigns

Robustness and qualification campaigns are not routine unit tests.

They answer broader questions about repeated recovery and behaviour across many
cases.

See [Robustness campaigns](../tools/robustness/README.md).
