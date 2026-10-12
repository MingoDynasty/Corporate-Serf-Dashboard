"""Build the toast a page shows for a run that just landed on its scenario.

A page that charts one scenario calls ``build_run_event_notification`` from
its chart callback, with the summary its batch consumer forwarded and the
page's own notification settings. The page sends the result on the channel
named here.
"""

from source.app_shell import RunEventData
from source.components.local_icon import local_icon
from source.components.run_delivery import RunEventsPayload
from source.components.score_threshold import (
    ThresholdVerdict,
    shown_percentage,
    threshold_verdict,
)
from source.utilities.notifications import toast
from source.utilities.utilities import ordinal

# One run, one toast: every run verdict shares this channel key, so the newest
# one replaces whatever is on screen instead of stacking. The celebration toast
# is deliberately not in this lane -- it has its own id and stays until
# dismissed.
RUN_VERDICT_CHANNEL = "run-verdict"


def _placement_phrase(nth_score: int) -> str:
    """Name a top-N placement: first place is "best", the rest are "Nth-best"."""
    return "best" if nth_score == 1 else f"{ordinal(nth_score)}-best"


def build_live_run_notification(
    latest: RunEventData,
    selected_scenario: str,
    top_n_scores: int,
    verdict: ThresholdVerdict | None,
) -> dict[str, object] | None:
    """Build the one toast a just-played run earned, if it earned one.

    The threshold verdict is the headline whenever there is one; a top-N
    placement is the trailing detail. A run that is neither judged nor placed
    says nothing worth interrupting for -- its new point on the plot is the
    confirmation that it landed.
    """
    placed = latest["nth_score"] <= top_n_scores
    placement = (
        f"your {_placement_phrase(latest['nth_score'])} at {latest['sensitivity']}"
    )
    score = f"{selected_scenario}: {latest['score']:.2f}"

    if verdict is None:
        if not placed:
            return None
        return toast(
            RUN_VERDICT_CHANNEL,
            f"New {_placement_phrase(latest['nth_score'])} score",
            f"{score} at {latest['sensitivity']}.",
            color="green",
            icon=local_icon("fontisto:line-chart"),
        )

    shown = shown_percentage(verdict)
    # The one word that tells the player which measure judged the run.
    measure = "PB pace" if verdict.by_pace else "PB"
    if verdict.passed:
        # A pass ends at the fact: a line saying what to do next would be
        # advice, and the app states verdicts only.
        message = f"{score}, {shown:.1f}% of {measure}."
        if placed:
            message += f" Also {placement}."
        return toast(
            RUN_VERDICT_CHANNEL,
            "Threshold passed",
            message,
            color="green",
            icon=local_icon("material-symbols:check"),
        )

    shortfall = f"{score}, {shown:.1f}% of {measure} "
    shortfall += f"(need {verdict.goal_percentage:.1f}%)."
    if placed:
        shortfall += f" Still {placement}."
    return toast(
        RUN_VERDICT_CHANNEL,
        "Below threshold",
        shortfall,
        color="yellow",
        icon=local_icon("material-symbols:warning-outline"),
    )


def build_run_event_notification(  # noqa: PLR0913
    run_events: RunEventsPayload | None,
    selected_scenario: str,
    top_n_scores: int,
    score_threshold_percentage: float | str | None,
    score_threshold_notification_switch: bool,
    run_notification_switch: bool,
) -> dict[str, object] | None:
    """Build the at-most-one toast the page's latest matching run earned.

    Nothing here predicts or re-derives: the drain stamped the celebration and
    each run's liveness, and this reads the stamps. The master switch is
    checked first, so it gates the whole page-built family, and the yield to
    the celebration comes second -- with celebrations reporting a run, that
    run's one notification is the celebration toast.

    A batch's other runs earn nothing: the plot is their record, which is what
    retires the "While you were away" digest.
    """
    if not run_notification_switch:
        return None
    if run_events is None or run_events["latest"]["scenario_name"] != selected_scenario:
        return None

    latest = run_events["latest"]
    if run_events["celebrated_run_id"] == latest["run_id"]:
        return None
    if not latest["is_live"]:
        return None

    verdict = threshold_verdict(
        latest,
        score_threshold_percentage,
        score_threshold_notification_switch,
    )
    return build_live_run_notification(
        latest,
        selected_scenario,
        top_n_scores,
        verdict,
    )
