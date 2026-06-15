# D7 enum-domain policy

D7 should remove label drift, not hide it.

## Rule

A string enum value belongs to one semantic domain. A value may be shared across domains only when that reuse is deliberate, documented, and covered by a test.

Examples of separate domains:

- report-detail keys, such as `execution_route`;
- execution-route values, such as `known_key_fastpath`;
- oracle/truth-data usage labels;
- solver parameter keys, such as `test_key`;
- scorer lane names and lane state labels.

## Forbidden pattern

Do not borrow an enum member from the wrong domain merely because its string value happens to match.

For example, `OracleUse.KNOWN_KEY_FASTPATH.value` must not be used as an `execution_route` value. The execution-route domain should have its own enum, such as `ExecutionRoute.KNOWN_KEY_FASTPATH`.

Likewise, `OracleUse.TEST_KEY.value` must not be used as a `normalized_params` key. The solver-parameter-key domain should have its own enum, such as `SolverParamKey.TEST_KEY`.

## Test contract

The machine-readable ledger is:

```text
docs/v1_traceability/v1_enum_domain_ledger.json
```

The contract test is:

```text
tests/contracts/test_enum_domain_ownership.py
```

The test builds a repository-wide string-enum inventory and fails on explicitly forbidden wrong-domain borrowings recorded in the ledger. Broad duplicate-value uniqueness is intentionally not a hard gate yet because RDP still has legitimate historical overlaps such as generic direction, device, and mode labels. Tighten this by adding ledgered allow/deny rows rather than relying on accidental string equality.
