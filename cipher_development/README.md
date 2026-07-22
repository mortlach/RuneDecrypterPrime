# Cipher development

`cipher_development/` is RDP's workspace for designing, benchmarking and diagnosing solvers for novel or difficult ciphers before their contracts are stable enough for the public package.

This is not a second public API, a universal solver framework or a numbered-stage campaign engine. Campaign code remains explicit and readable.

## Normal operating mode

RDP cipher development normally uses reliable WLI:

- `with_wli` is the normal mode;
- `without_wli` is an optional specialist robustness mode;
- there is no permanent `partial_wli` framework mode.

A campaign may model damaged or incomplete WLI locally when a real scientific question requires it, but that does not create another framework-wide mode.

## Intended layout

```text
cipher_development/
  README.md

  shared/
    experiment.py
    ledger.py
    archive.py
    replay.py

  <cipher_or_campaign>/
    CAMPAIGN.md
    run.py
    cipher.py
    keyops.py
    solver.py
    fixtures/
```

The example is not a requirement that every campaign contain every file. Start with the smallest readable campaign and add files only when they have a real purpose.

## Development and promotion boundary

Cipher, keyops, candidate, move and solver code may begin together inside a campaign folder while their representations and scientific assumptions are still changing.

Use existing RDP facilities unchanged when they fit. Wrap or compose them locally for experiments rather than copying them.

First-use code stays campaign-local. Move code into `cipher_development/shared/` only after it has a stable contract and a real second consumer. Move code into `src/rune_decrypter_prime/` only after its contract is stable, it is useful independently of one campaign and appropriate core tests can be written.

Do not create generic numbered stages, a universal solver inheritance hierarchy or an abstract cipher-development API.

## Evidence and outputs

Runtime outputs belong below:

```text
output/cipher_development/
```

They are not committed. A custom output root, when needed for tests or controlled runs, must remain beneath this directory.

Each established campaign should maintain one evolving `CAMPAIGN.md` and one machine-readable experiment ledger. Do not create a new Markdown plan or review pack for every run.

The shared WP1 infrastructure records experiment identity, deterministic configuration hashes, progress snapshots, terminal results and append-only ledger rows. It does not run solvers, retain candidate archives or decide campaign control flow.

The execution configuration is frozen when `ExperimentRun` is constructed. Reference truth, expected plaintext, known keys and oracle data must not be placed in that configuration; benchmark reference evaluation belongs only in the terminal `reference_evaluation` field.

Only one `ExperimentRun` may be active in a Python process because RDP's logging paths are process-global. Parallel cipher-development experiments must use separate processes.

The terminal result file is authoritative. If appending the campaign ledger fails after the result is written, the completed or failed result is preserved so a later recovery tool can rebuild the missing ledger row.

## Candidate retention and replay

WP2 adds a bounded candidate archive and self-contained replay or handoff batches. The campaign defines candidate identity, payload, named scores, provenance and any optional family identifier. Shared code only validates, ranks, retains and persists that evidence.

The archive uses one explicitly named decision score and deterministic candidate-ID tie-breaking. Family caps are optional and disabled by default. The archive does not calculate scores, infer cipher equivalence, mutate candidates or decide whether an experiment should be promoted, refined or closed.

Replay and handoff batches embed exact retained candidate records and identify their source archive by content hash. They prepare evidence for campaign code; they do not decrypt, score, run solvers or convert candidates into RDP seed keys.

Candidate identities and payloads must not contain reference truth, expected plaintext, known keys or oracle data. Large archive and batch payloads remain run artifacts; only concise summaries and relative artifact paths belong in the experiment result and ledger.

## Established campaigns

- `two_period_overlay/` tests archive handoff on a crib-constrained affine P13/P17 overlay.
- `periodic_sub_trans_wli/` tests raw versus full-WLI ranking over one periodic-columnar candidate pool, followed by equal-budget seeded exploitation.

The two campaigns deliberately use different key structures and scientific questions while reusing the WP1 experiment and WP2 archive/replay contracts unchanged.
