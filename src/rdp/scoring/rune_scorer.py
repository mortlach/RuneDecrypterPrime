# ============================================================
# rdp/scoring/rune_scorer.py   (strict V1 wrapper)
# ============================================================
from __future__ import annotations

import warnings

from rdp.core.capability_gates import issue_from_exception
from rdp.core.component_contracts import (
    CapabilityIssue,
    CapabilityStatus,
    RequestedLaneUnavailableError,
    ScoringLane,
)
from rdp.core.config.cipher import CipherConfig
from rdp.core.config.scoring import ScoringConfig, SpanHammingMode, ensure_span_hamming_mode
from rdp.scoring import rune_scorer_impl as _impl
from rdp.scoring.rune_scorer_impl import *  # noqa: F401,F403
from rdp.scoring.scorer_lane_report import build_scorer_lane_report


WORD_NGRAM_JUDGE_UNAVAILABLE_MESSAGE = (
    "word_ngram_judge_enabled=True, but the experimental word-ngram "
    "judge module is not present in this V1 release build. "
    "Disable word_ngram_judge_enabled or install the experimental "
    "ngram tooling branch."
)

_LegacyRuneScorer = _impl.RuneScorer


def _requested_lanes(scorer_cfg: ScoringConfig) -> set[ScoringLane]:
    return set(scorer_cfg.requested_scorer_lanes())


def _issue_from_warning(*, code: str, warning: warnings.WarningMessage, source: str) -> CapabilityIssue:
    return CapabilityIssue(
        code=code,
        message=str(warning.message),
        status=CapabilityStatus.UNAVAILABLE,
        source=source,
        exception_type=warning.category.__name__,
    )


def _generic_issue(*, code: str, message: str, source: str) -> CapabilityIssue:
    return CapabilityIssue(
        code=code,
        message=message,
        status=CapabilityStatus.UNAVAILABLE,
        source=source,
        exception_type=None,
    )


def _sync_patchable_impl_globals() -> None:
    # Tests and downstream integrations historically monkeypatch symbols on
    # rune_scorer.py.  Keep those patches effective after the implementation
    # split by mirroring known patchable globals into the implementation module.
    for name in ("LmPrimeRuntime", "ECDFCache"):
        if name in globals():
            setattr(_impl, name, globals()[name])


class RuneScorer(_LegacyRuneScorer):
    """Strict V1 contract wrapper around the NumPy scorer implementation."""

    def __init__(self, cfg_cipher: CipherConfig, scorer_cfg: ScoringConfig) -> None:
        requested = _requested_lanes(scorer_cfg) if isinstance(scorer_cfg, ScoringConfig) else set()
        _sync_patchable_impl_globals()

        caught_warnings: list[warnings.WarningMessage]
        try:
            with warnings.catch_warnings(record=True) as caught_warnings:
                warnings.simplefilter("always")
                super().__init__(cfg_cipher, scorer_cfg)
        except RequestedLaneUnavailableError:
            raise
        except ValueError:
            # Calibrated span-Hamming uses ValueError for deterministic config
            # validation, e.g. unsupported objective family or invalid char
            # channel setup. Preserve those API-visible validation errors.
            raise
        except Exception as exc:
            if ScoringLane.SPAN_HAMMING_CALIBRATED in requested:
                issue = issue_from_exception(
                    code="calibrated_span_hamming_unavailable",
                    status=CapabilityStatus.UNAVAILABLE,
                    exc=exc,
                    source="span_hamming_calibrated",
                )
                self._capability_report = build_scorer_lane_report(
                    scorer_cfg,
                    calibrated_issue=issue,
                )
                self._capability_report.raise_if_blocked()
            raise

        hamming_issue = None
        span_hamming_issue = None
        for warning in caught_warnings:
            message = str(warning.message).lower()
            if "hamming backend unavailable" in message:
                hamming_issue = _issue_from_warning(
                    code="hamming_backend_unavailable",
                    warning=warning,
                    source="hamming",
                )
            elif "span-hamming backend unavailable" in message:
                span_hamming_issue = _issue_from_warning(
                    code="span_hamming_backend_unavailable",
                    warning=warning,
                    source="span_hamming_raw",
                )
            else:
                warnings.warn(warning.message, warning.category, stacklevel=2)

        if (
            ScoringLane.HAMMING in requested
            and getattr(self, "_hamming_backend", None) is None
            and hamming_issue is None
        ):
            hamming_issue = _generic_issue(
                code="hamming_backend_unavailable",
                message="requested hamming backend was unavailable",
                source="hamming",
            )

        if (
            ScoringLane.SPAN_HAMMING_RAW in requested
            and getattr(self, "_span_hamming_backend", None) is None
            and span_hamming_issue is None
        ):
            span_hamming_issue = _generic_issue(
                code="span_hamming_backend_unavailable",
                message="requested raw span-hamming backend was unavailable",
                source="span_hamming_raw",
            )

        self._capability_report = build_scorer_lane_report(
            scorer_cfg,
            hamming_backend=getattr(self, "_hamming_backend", None),
            hamming_issue=hamming_issue,
            span_hamming_backend=(
                getattr(self, "_span_hamming_backend", None)
                if ensure_span_hamming_mode(
                    getattr(self, "_span_hamming_mode", SpanHammingMode.OFF)
                ) is SpanHammingMode.RAW_BONUS
                else None
            ),
            span_hamming_issue=span_hamming_issue,
            calibrated_assets=getattr(self, "_span_hamming_assets", None),
            word_ngram_judge=getattr(self, "_word_ngram_judge", None),
        )
        self._capability_report.raise_if_blocked()

    def capability_report(self):
        return self._capability_report
