from __future__ import annotations

from pathlib import Path

from cipher_development.shared.synthesis import MilestoneSpec, write_milestone

CAMPAIGN_ID = "two_period_overlay"
MILESTONE_ID = "wp5_initial_replay"
MILESTONE_TITLE = "Initial replay discipline"
AS_OF = "2026-07-22"
SELECTED_RUN_IDS: tuple[str, ...] = ()
INCLUDE_REFERENCE_EVALUATION = False
CANDIDATE_LESSON_PROPOSALS: tuple[dict[str, object], ...] = ()


def main() -> int:
    if not SELECTED_RUN_IDS:
        raise ValueError("configure SELECTED_RUN_IDS before running milestone synthesis")
    repo_root = Path(__file__).resolve().parents[1]
    spec = MilestoneSpec(
        milestone_id=MILESTONE_ID,
        campaign_id=CAMPAIGN_ID,
        title=MILESTONE_TITLE,
        as_of=AS_OF,
        selected_run_ids=SELECTED_RUN_IDS,
        include_reference_evaluation=INCLUDE_REFERENCE_EVALUATION,
        candidate_lesson_proposals=CANDIDATE_LESSON_PROPOSALS,
    )
    write_milestone(repo_root, spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
