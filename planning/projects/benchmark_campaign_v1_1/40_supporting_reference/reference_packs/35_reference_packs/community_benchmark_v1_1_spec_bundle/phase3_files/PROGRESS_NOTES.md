Phase 3‑5 progress notes
========================

This document records the design decisions and progress for phases 3–5 of the
RDP Community Benchmark v1.1 integration.  It is intended to provide
transparency and continuity while we prototype the manifest generator, sharder,
runner and organiser tools.  Should the session be interrupted these
notes make it straightforward to resume or handoff.

Scope and assumptions
---------------------

The implementation targets the following behaviours described in the v1.1
specification:

* Deterministic manifest generation based on a campaign seed and commit,
  enumerating periods 7–13, columns 1–13 and both cipher orders
  (``col_then_sub`` and ``sub_then_col``).  The manifest includes a
  deterministic ``job_id`` derived from the canonical JSON representation of the
  job specification hashed with SHA‑256.  The ``campaign_id`` is derived
  similarly from the campaign seed.  Canonical JSON uses sorted keys and
  minimal separators to ensure stable ordering across platforms.
* Sharding of the manifest into a configurable number of roughly equal‐sized
  files with stable ordering.  Shards are written to an output directory and
  named ``manifest_shard_XXX.jsonl``.  The sharder does not drop or duplicate
  jobs.
* A prototype shard runner that reads a shard of jobs, loads a profile
  catalogue, applies per‑job caps, and writes results rows conforming to the
  v1.1 result schema.  At this stage the runner contains a stub solver that
  returns unsolved results with a ``missing_assets`` stop reason; the actual
  solver integration will follow in later iterations.  Logging and resume
  support are present.
* Organiser tooling comprising a validator (to check run bundles against
  schemas and manifest contents), a combiner (to deduplicate and merge
  multiple runs deterministically), and an aggregator (to produce CSV
  summaries and simple heatmaps).  These are implemented as separate scripts
  to ease testing and future enhancements.

The following assumptions have been made due to limited visibility into the
full spec during this prototype:

* The manifest schema requires only the fields exposed here
  (``job_id``, ``campaign_id``, ``campaign_seed``, ``commit``, ``period``,
  ``columns`` and ``order``).  Should additional fields be mandated (for
  example a ``profile`` or replicate index) they can be added easily by
  modifying the ``generate_jobs`` function in ``generate_manifest.py``.
* The result schema contains keys for basic meta data plus ``status``,
  ``stop_reason``, ``best_match_ratio``, ``total_seconds`` and
  ``num_evaluations``.  It also mandates that ``status`` be one of
  ``solved``, ``unsolved``, ``stalled`` or ``error``, and that ``stop_reason``
  be one of the enumerated reasons defined in the spec.  If additional fields
  appear in the official schema they can be appended to the result row in
  ``run_shard.py``.
* A simple deterministic tie‑break procedure is used in ``combine_results``
  consistent with the spec: when multiple result rows exist for a job, the
  row with the lexicographically highest status, highest ``best_match_ratio``
  and lowest ``total_seconds`` is chosen.  Should the spec require a
  different priority order this function can be updated.

Organisation
------------

All new scripts live under ``phase3/tools/benchmarks/community/`` to avoid
conflicts with the existing code base.  Once these prototypes stabilise they
should be moved to ``tools/benchmarks/community/`` in the real repository.
Tests live under ``phase3/tests/community/``.  A ``pytest.ini`` entry would
normally be added to discover them; this prototype relies on the test paths
being included by default.
