# Glossary

## RDP

Rune Decrypter Prime.

## Rune index

A numeric representation of a rune in RDP's 29-rune alphabet.

## Ciphertext

The encrypted rune text being solved.

## Plaintext

The candidate decrypted rune text.

## Solver

The search process that tries candidate keys.

## Scorer

The component that ranks candidate plaintexts.

## Key

The value or sequence the solver is trying to recover or test.

## Tutorial

A runnable example under:

```text
tutorials/v1/
```

## Tutorial manifest

The file that lists tutorial expectations, gates, and acceptance rules:

```text
tutorials/v1/tutorial_manifest_v1.json
```

## Gate profile

A tutorial runner setting that chooses which tutorials to run.

Common profile:

```text
release
```

Fuller profile:

```text
full_v1
```

## Asset profile

The set of scoring/data assets available for a run.

Common default:

```text
lm2_baseline
```

## WLI

Word-location information. It records word position/length information when
available.

## Match ratio

A tutorial success measure comparing recovered text with expected text.

## Exact solve

A tutorial where the expected match ratio is complete or effectively complete.

## Near-solve

A tutorial where the recovered text is good enough to meet a declared acceptance
threshold but is not necessarily exact.

## Output folder

Generated runtime output under:

```text
output/
```

## Telemetry

Structured runtime information written so a run can be inspected and compared.
For normal users, it is enough to know that telemetry lives in the generated
output and helps explain a run.
