"""Summarize the shell's run-event batch for the one scenario a page shows.

The app shell drains new runs and publishes one batch per poll for every
page. A page that charts one scenario forwards that batch to its own store as
a summary: the latest run on the scenario it should show, and the shell's
decision about which run it celebrated. The page registers its own callback
for that. This module holds what such a callback works out.
"""

from typing import TypedDict

from source.app_shell import RunEventBatch, RunEventData


class RunEventsPayload(TypedDict):
    """Summary passed from a page's batch consumer to its other callbacks."""

    latest: RunEventData
    celebrated_run_id: str | None


def summarize_run_events(
    batch: RunEventBatch,
    selected_scenario: str | None,
    automatically_change_scenario: bool,
) -> tuple[str | None, RunEventsPayload | None]:
    """Summarize one shell batch for the scenario the page should show."""
    runs = batch["runs"]
    if not runs:
        return selected_scenario, None

    target_scenario = (
        runs[-1]["scenario_name"]
        if automatically_change_scenario
        else selected_scenario
    )
    if target_scenario is None:
        return None, None

    matching_runs = [run for run in runs if run["scenario_name"] == target_scenario]
    if not matching_runs:
        return target_scenario, None

    # Coalescing, as before: several runs rebuild the plot once and only the
    # latest matching one is narrated. The drain's decision travels with it,
    # because the celebrated run may belong to another scenario entirely.
    return target_scenario, {
        "latest": matching_runs[-1],
        "celebrated_run_id": batch["celebrated_run_id"],
    }
