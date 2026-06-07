from __future__ import annotations

"""Runtime projection helpers for strict O3 known-damage calibration staging."""

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class RuntimeProjection:
    stage_name: str
    clean_chunks: int
    samples_per_chunk: int
    total_samples: int
    seconds_per_sample: float
    projected_seconds: float
    projected_hours: float
    projected_days: float

    def row(self) -> dict[str, object]:
        return asdict(self)


def project_runtime(
    *,
    stage_name: str,
    clean_chunks: int,
    samples_per_chunk: int,
    observed_elapsed_seconds: float,
    observed_samples: int,
) -> RuntimeProjection:
    if clean_chunks < 0 or samples_per_chunk < 0:
        raise ValueError("clean_chunks and samples_per_chunk must be non-negative")
    if observed_elapsed_seconds <= 0.0:
        raise ValueError("observed_elapsed_seconds must be positive")
    if observed_samples <= 0:
        raise ValueError("observed_samples must be positive")
    seconds_per_sample = observed_elapsed_seconds / float(observed_samples)
    total_samples = int(clean_chunks) * int(samples_per_chunk)
    projected_seconds = seconds_per_sample * float(total_samples)
    return RuntimeProjection(
        stage_name=stage_name,
        clean_chunks=int(clean_chunks),
        samples_per_chunk=int(samples_per_chunk),
        total_samples=total_samples,
        seconds_per_sample=seconds_per_sample,
        projected_seconds=projected_seconds,
        projected_hours=projected_seconds / 3600.0,
        projected_days=projected_seconds / 86400.0,
    )


def default_stage_projection_rows(*, observed_elapsed_seconds: float, observed_samples: int) -> list[dict[str, object]]:
    stages = (
        ("stage0_tiny_canary", 2, 19),
        ("stageA_10_chunks_current_profile", 10, 19),
        ("stageB_25_chunks_current_profile", 25, 19),
        ("stageC_50_chunks_current_profile", 50, 19),
        ("wide_50_chunks_109_samples_per_chunk", 50, 109),
        ("wide_500_chunks_109_samples_per_chunk", 500, 109),
    )
    return [
        project_runtime(
            stage_name=name,
            clean_chunks=chunks,
            samples_per_chunk=samples_per_chunk,
            observed_elapsed_seconds=observed_elapsed_seconds,
            observed_samples=observed_samples,
        ).row()
        for name, chunks, samples_per_chunk in stages
    ]
