#!/usr/bin/env python3
"""
Generate a deterministic benchmark manifest for the RDP Community Benchmark v1.1.

The v1.1 specification defines a campaign over a grid of periodic columnar
ciphers.  A campaign is identified by a ``campaign_seed`` and commit hash.  This
script enumerates all valid combinations of period (7‒13 inclusive), columns
(1‒13 inclusive) and cipher order (``col_then_sub`` and ``sub_then_col``),
and produces a JSON lines manifest of jobs.  Each job includes:

* ``job_id`` – a 64‑character hexadecimal string computed as the SHA‑256
  digest of the canonical JSON representation of the job spec.  This value is
  stable across platforms and Python versions.
* ``campaign_id`` – a short identifier derived from the campaign seed by
  taking the first 16 characters of its SHA‑256 digest.  This provides a
  convenient namespace for distinguishing campaigns without exposing the
  entire seed.
* ``campaign_seed`` – the seed string provided by the caller.  This seed is
  used when deriving the ``job_id`` to ensure that two different campaigns
  produce distinct job identifiers.
* ``commit`` – the Git commit hash used when generating the manifest.  This
  allows reproducibility by pinning the exact code version.
* ``period`` – an integer in the range [7, 13].
* ``columns`` – an integer in the range [1, 13].
* ``order`` – either ``col_then_sub`` or ``sub_then_col``.

The order of jobs in the output manifest is deterministic.  Jobs are
constructed in lexicographic order by (period, columns, order), then sorted
by ``job_id`` to remove any dependence on the enumeration order.  Users may
optionally shuffle the jobs downstream; however, keeping a stable ordering
helps with debugging and diffing.

Usage::

    python generate_manifest.py \
        --campaign-seed "my‑seed" \
        --commit "abcdef123" \
        --output manifest.jsonl

"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Dict, Iterable, List


def canonical_json(obj: Dict) -> str:
    """Return a canonical JSON representation with sorted keys and no
    insignificant whitespace.

    Using ``json.dumps`` with ``sort_keys=True`` and compact separators
    guarantees that the same data structure produces the same string in all
    environments.  This is essential for deterministic hashing.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def derive_campaign_id(seed: str) -> str:
    """Derive a stable short campaign ID from the seed.

    The SHA‑256 digest of the UTF‑8 encoded seed is computed and truncated to
    the first 16 hexadecimal characters.  This yields an 8‑byte prefix which
    is human‑friendly yet statistically unlikely to collide.
    """
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def generate_jobs(campaign_seed: str, commit: str) -> Iterable[Dict]:
    """Generate the list of job specifications for the campaign.

    Args:
        campaign_seed: A string used to derive job identifiers and the
            campaign_id.
        commit: The Git commit hash associated with the code version.

    Yields:
        Dictionary objects representing individual jobs.  Each job includes
        ``job_id``, ``campaign_id``, ``campaign_seed``, ``commit``, ``period``,
        ``columns`` and ``order``.
    """
    campaign_id = derive_campaign_id(campaign_seed)
    jobs: List[Dict] = []
    for period in range(7, 14):  # inclusive upper bound since range stops before 14
        for columns in range(1, 14):
            for order in ("col_then_sub", "sub_then_col"):
                job_spec = {
                    "campaign_id": campaign_id,
                    "campaign_seed": campaign_seed,
                    "commit": commit,
                    "period": period,
                    "columns": columns,
                    "order": order,
                }
                # Compute the job_id by hashing the canonical JSON representation of
                # the spec.  We exclude ``job_id`` itself from the hash input.
                job_id_input = canonical_json(job_spec)
                job_id = hashlib.sha256(job_id_input.encode("utf-8")).hexdigest()
                job_spec["job_id"] = job_id
                jobs.append(job_spec)
    # Sort deterministically by job_id to stabilise the ordering across
    # different enumeration strategies or Python implementations.
    jobs.sort(key=lambda j: j["job_id"])
    for job in jobs:
        yield job


def write_manifest(jobs: Iterable[Dict], fh) -> None:
    """Write jobs to the provided file handle as JSON lines.

    Each job is serialised using compact separators to minimise file size and
    ensure consistent formatting.
    """
    for job in jobs:
        fh.write(json.dumps(job, separators=(",", ":")))
        fh.write("\n")


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a v1.1 benchmark manifest for the RDP community campaign."
        )
    )
    parser.add_argument(
        "--campaign-seed",
        required=True,
        help="Seed string used to derive job identifiers and the campaign ID.",
    )
    parser.add_argument(
        "--commit",
        required=True,
        help="Git commit hash associated with the code version.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="-",
        help="Path to write the manifest file (JSON lines).  Use '-' for stdout.",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    jobs = generate_jobs(args.campaign_seed, args.commit)
    if args.output == "-":
        write_manifest(jobs, sys.stdout)
    else:
        with open(args.output, "w", encoding="utf-8") as fh:
            write_manifest(jobs, fh)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())