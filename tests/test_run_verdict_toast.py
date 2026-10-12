"""The toast a page builds for a run that just landed on its scenario.

These hold what ``build_run_event_notification`` says for each kind of run:
the threshold verdict by score and by pace, a top-N placement, the runs that
earn nothing, and the two switches that gate the family. The last section
follows a real stats file from the watchdog to the toast.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

from sortedcontainers import SortedList

from source.app_shell import RunEventBatch, RunEventData, _run_event_data
from source.components import run_delivery, run_verdict_toast
from source.components.run_delivery import RunEventsPayload
from source.kovaaks import data_service
from source.kovaaks.data_models import RunData
from source.my_watchdog import file_watchdog


def _run(
    scenario_name: str = "Scenario A",
    *,
    run_id: str = "run-1.csv",
    nth_score: int = 2,
    score: float = 812.4,
    scenario_previous_best: float | None = 800.0,
    pace_constant: float | None = None,
    is_new_sensitivity: bool = False,
    is_live: bool = True,
) -> RunEventData:
    """One run as the shell stamped it: facts plus the drain's liveness."""
    return {
        "run_id": run_id,
        "scenario_name": scenario_name,
        "sensitivity": "34.64 cm/360",
        "nth_score": nth_score,
        "score": score,
        "scenario_previous_best": scenario_previous_best,
        "pace_constant": pace_constant,
        "is_new_sensitivity": is_new_sensitivity,
        "is_live": is_live,
    }


def _batch(
    *runs: RunEventData,
    celebrated_run_id: str | None = None,
) -> RunEventBatch:
    return {
        "runs": list(runs),
        "celebrated_run_id": celebrated_run_id,
        "animation_sequence": 1 if celebrated_run_id else 0,
    }


def _payload(
    scenario_name: str = "Scenario A",
    *,
    celebrated_run_id: str | None = None,
    **run_fields,
) -> RunEventsPayload:
    return {
        "latest": _run(scenario_name, **run_fields),
        "celebrated_run_id": celebrated_run_id,
    }


def _notification(
    payload: RunEventsPayload,
    *,
    top_n_scores: int = 5,
    score_threshold_percentage: float | str | None = 100.0,
    score_threshold_notification_switch: bool = True,
    run_notification_switch: bool = True,
) -> dict[str, object] | None:
    return run_verdict_toast.build_run_event_notification(
        payload,
        "Scenario A",
        top_n_scores,
        score_threshold_percentage,
        score_threshold_notification_switch,
        run_notification_switch,
    )


def test_every_run_verdict_shares_one_replaceable_id():
    # One run, one toast: the placement toast and both threshold verdicts land
    # under the same id, so the newest one replaces whatever is on screen
    # instead of stacking beside it.
    ids = {
        _notification(_payload(is_new_sensitivity=True))["id"],
        _notification(_payload(score=830.0))["id"],
        _notification(_payload(score=780.0))["id"],
    }

    assert ids == {"run-verdict"}


def test_top_n_placement_alone_leads_with_the_scenario():
    # No previous high score means no threshold verdict; the placement is the
    # whole story and the title carries it.
    notification = _notification(_payload(is_new_sensitivity=True))

    assert notification["title"] == "New 2nd-best score"
    assert notification["message"] == "Scenario A: 812.40 at 34.64 cm/360."
    assert notification["color"] == "green"


def test_a_first_place_run_is_titled_new_best_score():
    # Deliberately not "New personal best!": the recorded decision is that a PB
    # gets no toast of its own, and a retitle would create one by the back door.
    notification = _notification(_payload(nth_score=1, is_new_sensitivity=True))

    assert notification["title"] == "New best score"
    assert notification["message"] == "Scenario A: 812.40 at 34.64 cm/360."


def test_threshold_pass_headlines_over_the_placement_it_also_earned():
    notification = _notification(
        _payload(score=830.0, scenario_previous_best=800.0),
        score_threshold_percentage=102.5,
    )

    assert notification["title"] == "Threshold passed"
    assert notification["color"] == "green"
    assert notification["message"] == (
        "Scenario A: 830.00, 103.8% of PB. Also your 2nd-best at 34.64 cm/360."
    )


def test_threshold_pass_without_a_placement_ends_at_the_fact():
    # Verdicts, not advice: nothing after the percentage tells the player what
    # to do next.
    notification = _notification(
        _payload(score=830.0, scenario_previous_best=800.0, nth_score=9),
        score_threshold_percentage=102.5,
    )

    assert notification["title"] == "Threshold passed"
    assert notification["message"] == "Scenario A: 830.00, 103.8% of PB."


def test_threshold_passes_at_exactly_the_goal():
    notification = _notification(
        _payload(score=820.0, scenario_previous_best=800.0),
        score_threshold_percentage=102.5,
    )

    assert notification["title"] == "Threshold passed"
    assert notification["message"].startswith("Scenario A: 820.00, 102.5% of PB.")


def test_threshold_passes_exactly_at_a_goal_float_math_overshoots():
    # 19.57 is exactly 95% of 20.60, but in floats 20.6 * 95 / 100 is
    # 19.570000000000004, which would fail the run and cap it to 94.9%.
    notification = _notification(
        _payload(score=19.57, scenario_previous_best=20.60),
        score_threshold_percentage=95,
    )

    assert notification["title"] == "Threshold passed"
    assert notification["message"].startswith("Scenario A: 19.57, 95.0% of PB.")


def test_threshold_pass_short_of_the_pb_never_reads_as_matching_it():
    # 11523 / 11526 is 99.97% of PB: a pass at a 95% goal, but one-decimal
    # rounding alone would print "100.0% of PB" for a run that fell short.
    notification = _notification(
        _payload(score=11523.0, scenario_previous_best=11526.0),
        score_threshold_percentage=95,
    )

    assert notification["title"] == "Threshold passed"
    assert notification["message"] == (
        "Scenario A: 11523.00, 99.9% of PB. Also your 2nd-best at 34.64 cm/360."
    )


def test_a_run_matching_the_pb_reads_as_all_of_it():
    # The cap is for a run below the PB only: a tie is 100.0% and says so.
    notification = _notification(
        _payload(score=11526.0, scenario_previous_best=11526.0),
        score_threshold_percentage=95,
    )

    assert notification["message"].startswith("Scenario A: 11526.00, 100.0% of PB.")


def test_threshold_fail_names_the_target_it_missed():
    notification = _notification(
        _payload(score=780.0, scenario_previous_best=800.0),
        score_threshold_percentage=98.75,
    )

    assert notification["title"] == "Below threshold"
    assert notification["color"] == "yellow"
    assert notification["message"] == (
        "Scenario A: 780.00, 97.5% of PB (need 98.8%). "
        "Still your 2nd-best at 34.64 cm/360."
    )


def test_threshold_fail_never_reads_as_meeting_the_goal():
    # 10848 / 11421 is 94.98% of PB: short of 95%, but one-decimal rounding
    # alone would print "95.0% of PB (need 95.0%)".
    notification = _notification(
        _payload(score=10848.0, scenario_previous_best=11421.0, nth_score=9),
        score_threshold_percentage=95,
    )

    assert notification["title"] == "Below threshold"
    assert notification["message"] == (
        "Scenario A: 10848.00, 94.9% of PB (need 95.0%)."
    )


def test_threshold_fail_stays_below_a_goal_that_displays_rounded_down():
    # A 98.74% goal prints as 98.7%, so a 98.73% run must print lower still.
    notification = _notification(
        _payload(score=9873.0, scenario_previous_best=10000.0, nth_score=9),
        score_threshold_percentage=98.74,
    )

    assert notification["message"] == ("Scenario A: 9873.00, 98.6% of PB (need 98.7%).")


def test_a_new_pb_short_of_a_stretch_goal_still_reads_as_below_threshold():
    # Reachable whenever the goal exceeds 100%: the run beat the old PB and
    # still missed the bar. The verdict is the title, so it stays "Below
    # threshold" rather than being retitled for the PB.
    notification = _notification(
        _payload(score=820.0, scenario_previous_best=800.0, nth_score=1),
        score_threshold_percentage=105.0,
    )

    assert notification["title"] == "Below threshold"
    assert notification["message"] == (
        "Scenario A: 820.00, 102.5% of PB (need 105.0%). "
        "Still your best at 34.64 cm/360."
    )


def test_a_stretch_goal_miss_short_of_the_pb_never_reads_as_matching_it():
    # A goal above 100% puts the failing cap above the PB too, so a run 0.03%
    # short of the PB would still print "100.0% of PB (need 105.0%)".
    notification = _notification(
        _payload(score=11523.0, scenario_previous_best=11526.0, nth_score=9),
        score_threshold_percentage=105.0,
    )

    assert notification["title"] == "Below threshold"
    assert notification["message"] == (
        "Scenario A: 11523.00, 99.9% of PB (need 105.0%)."
    )


def test_threshold_fail_without_a_placement_drops_the_placement_clause():
    notification = _notification(
        _payload(score=780.0, scenario_previous_best=800.0, nth_score=9),
        score_threshold_percentage=98.75,
    )

    assert notification["message"] == ("Scenario A: 780.00, 97.5% of PB (need 98.8%).")


def test_a_time_scored_pass_reads_as_a_percentage_of_pb_pace():
    # 905 took 95 s and 902 took 98 s: 96.9% of the pace, where the score's
    # own ratio would read 99.7%.
    notification = _notification(
        _payload(score=902.0, scenario_previous_best=905.0, pace_constant=1000.0),
        score_threshold_percentage=95,
    )

    assert notification["title"] == "Threshold passed"
    assert notification["color"] == "green"
    assert notification["message"] == (
        "Scenario A: 902.00, 96.9% of PB pace. Also your 2nd-best at 34.64 cm/360."
    )


def test_a_time_scored_pass_without_a_placement_ends_at_the_fact():
    notification = _notification(
        _payload(
            score=902.0,
            scenario_previous_best=905.0,
            pace_constant=1000.0,
            nth_score=9,
        ),
        score_threshold_percentage=95,
    )

    assert notification["message"] == "Scenario A: 902.00, 96.9% of PB pace."


def test_a_time_scored_fail_names_the_pace_it_missed():
    # The proposal's worked run: 883.02 against a PB of 896.17 passes at 98.5%
    # of the score, and is 88.8% of the pace.
    notification = _notification(
        _payload(score=883.02, scenario_previous_best=896.17, pace_constant=1000.0),
        score_threshold_percentage=95,
    )

    assert notification["title"] == "Below threshold"
    assert notification["color"] == "yellow"
    assert notification["message"] == (
        "Scenario A: 883.02, 88.8% of PB pace (need 95.0%). "
        "Still your 2nd-best at 34.64 cm/360."
    )


def test_a_time_scored_fail_without_a_placement_drops_the_placement_clause():
    notification = _notification(
        _payload(
            score=883.02,
            scenario_previous_best=896.17,
            pace_constant=1000.0,
            nth_score=9,
        ),
        score_threshold_percentage=95,
    )

    assert notification["message"] == (
        "Scenario A: 883.02, 88.8% of PB pace (need 95.0%)."
    )


def test_a_time_scored_run_passes_at_exactly_the_goal():
    # 95 s against 100 s is exactly 95% of the pace.
    notification = _notification(
        _payload(score=900.0, scenario_previous_best=905.0, pace_constant=1000.0),
        score_threshold_percentage=95,
    )

    assert notification["title"] == "Threshold passed"
    assert notification["message"].startswith("Scenario A: 900.00, 95.0% of PB pace.")


def test_a_time_scored_run_passes_exactly_at_a_goal_float_math_undershoots():
    # 198.74 s against 209.2 s is exactly 95%, and in floats both the ratio
    # and the cross-multiplied form come out a hair under it.
    notification = _notification(
        _payload(score=790.8, scenario_previous_best=801.26, pace_constant=1000.0),
        score_threshold_percentage=95,
    )

    assert notification["title"] == "Threshold passed"
    assert notification["message"].startswith("Scenario A: 790.80, 95.0% of PB pace.")


def test_a_time_scored_run_just_short_of_the_pb_never_reads_as_matching_it():
    # 103.83 s against 103.86 s is 99.97% of the pace: a pass at a 95% goal,
    # but one-decimal rounding alone would print "100.0% of PB pace".
    notification = _notification(
        _payload(score=896.14, scenario_previous_best=896.17, pace_constant=1000.0),
        score_threshold_percentage=95,
    )

    assert notification["title"] == "Threshold passed"
    assert notification["message"].startswith("Scenario A: 896.14, 99.9% of PB pace.")


def test_a_time_scored_fail_never_reads_as_meeting_the_goal():
    # 95 s against 100.02 s is 94.98% of the pace: short of 95%, but
    # one-decimal rounding alone would print "95.0% of PB pace (need 95.0%)".
    notification = _notification(
        _payload(
            score=899.98,
            scenario_previous_best=905.0,
            pace_constant=1000.0,
            nth_score=9,
        ),
        score_threshold_percentage=95,
    )

    assert notification["title"] == "Below threshold"
    assert notification["message"] == (
        "Scenario A: 899.98, 94.9% of PB pace (need 95.0%)."
    )


def test_a_run_with_no_constant_reads_as_a_percentage_of_pb():
    # The same two scores as the time-scored pass, judged by score.
    notification = _notification(
        _payload(score=902.0, scenario_previous_best=905.0, pace_constant=None),
        score_threshold_percentage=95,
    )

    assert notification["title"] == "Threshold passed"
    assert notification["message"].startswith("Scenario A: 902.00, 99.7% of PB.")


def test_a_time_scored_previous_best_of_zero_or_less_is_still_judged():
    # Pace needs positive times, not a positive previous best: 1,005 s against
    # 1,020 s is 98.5% of the pace. By score this run has no verdict at all.
    by_pace = _notification(
        _payload(score=-20.0, scenario_previous_best=-5.0, pace_constant=1000.0),
        score_threshold_percentage=95,
    )
    by_score = _notification(
        _payload(score=-20.0, scenario_previous_best=-5.0, pace_constant=None),
        score_threshold_percentage=95,
    )

    assert by_pace["title"] == "Threshold passed"
    assert by_pace["message"].startswith("Scenario A: -20.00, 98.5% of PB pace.")
    assert by_score["title"] == "New 2nd-best score"


def test_an_undefined_pace_falls_back_to_the_score_verdict():
    # A score at the constant took no time at all, so pace is undefined and the
    # run is judged as any other scenario's would be.
    notification = _notification(
        _payload(score=1000.0, scenario_previous_best=905.0, pace_constant=1000.0),
        score_threshold_percentage=95,
    )

    assert notification["title"] == "Threshold passed"
    assert notification["message"].startswith("Scenario A: 1000.00, 110.5% of PB.")


def test_an_undefined_pace_keeps_the_unjudged_rule_for_a_nonpositive_best():
    notification = _notification(
        _payload(score=1000.0, scenario_previous_best=0.0, pace_constant=1000.0),
        score_threshold_percentage=95,
    )

    assert notification["title"] == "New 2nd-best score"


def test_a_time_scored_first_run_at_a_sensitivity_is_still_unjudged():
    notification = _notification(
        _payload(
            score=902.0,
            scenario_previous_best=905.0,
            pace_constant=1000.0,
            is_new_sensitivity=True,
        ),
        score_threshold_percentage=95,
    )

    assert notification["title"] == "New 2nd-best score"


def test_an_empty_threshold_percentage_leaves_the_run_unjudged():
    for empty_percentage in (None, ""):
        notification = _notification(
            _payload(score=780.0, scenario_previous_best=800.0),
            score_threshold_percentage=empty_percentage,
        )

        assert notification["title"] == "New 2nd-best score"


def test_a_run_qualifying_for_neither_verdict_says_nothing():
    assert _notification(_payload(nth_score=9, is_new_sensitivity=True)) is None


def test_a_multi_run_batch_narrates_only_its_latest_matching_run():
    """No digest: the plot is every other run's record.

    A batch of several runs rebuilds the graph once, auto-switches once, and
    toasts about the latest matching run exactly as a single run would.
    """
    _target, payload = run_delivery.summarize_run_events(
        _batch(
            _run(run_id="a.csv", score=700.0),
            _run(run_id="b.csv", score=760.0),
            _run(run_id="c.csv", score=780.0),
        ),
        "Scenario A",
        False,
    )
    notification = _notification(payload, score_threshold_percentage=98.75)

    assert notification["title"] == "Below threshold"
    assert "runs" not in notification["message"]
    assert not hasattr(run_verdict_toast, "_build_backlog_notification")


def test_an_older_qualifying_personal_best_in_the_batch_is_plot_only():
    # Two personal bests in one batch. The drain names the newer one, the page
    # narrates the newer one and yields it to the celebration, and the older
    # one earns nothing -- exactly as such coalesced runs already do today.
    _target, payload = run_delivery.summarize_run_events(
        _batch(
            _run(run_id="older-pb.csv", score=810.0),
            _run(run_id="newer-pb.csv", score=830.0),
            celebrated_run_id="newer-pb.csv",
        ),
        "Scenario A",
        False,
    )

    assert payload["latest"]["run_id"] == "newer-pb.csv"
    assert _notification(payload) is None


def test_a_celebrated_run_yields_its_toast_to_the_celebration():
    # The celebration toast is that run's one notification, whatever verdict
    # the run would otherwise have earned -- including a stretch goal it
    # missed, which would have read "Below threshold" under the confetti.
    for goal in (95.0, 105.0):
        assert (
            _notification(
                _payload(score=830.0, celebrated_run_id="run-1.csv"),
                score_threshold_percentage=goal,
            )
            is None
        )


def test_a_celebrated_first_run_at_a_new_sensitivity_yields_too():
    # Case 2: unjudged, first at its sensitivity, and still the scenario's
    # best. The old schema could not tell this run from one with no history.
    assert (
        _notification(
            _payload(
                nth_score=1,
                score=900.0,
                is_new_sensitivity=True,
                celebrated_run_id="run-1.csv",
            )
        )
        is None
    )


def test_the_page_reads_the_stamp_and_never_re_derives_the_celebration():
    """Facts travel; only the drain decides.

    A run whose raw fields beat its previous best still narrates when the
    decision does not name it, and a run whose fields did not still yields when
    it does. Re-deriving here is what the single-drain design removed.
    """
    beat_its_best = _payload(score=830.0, celebrated_run_id=None)
    did_not = _payload(score=780.0, celebrated_run_id="run-1.csv")

    assert _notification(beat_its_best) is not None
    assert _notification(did_not) is None


def test_a_stale_run_narrates_nothing():
    # Past the freshness cap the run still reaches the plot; only the
    # interruption is withheld.
    assert _notification(_payload(score=830.0, is_live=False)) is None
    assert _notification(_payload(score=830.0, is_live=True)) is not None


def test_notifications_ignore_payload_for_another_scenario():
    assert (
        run_verdict_toast.build_run_event_notification(
            _payload("Scenario B"),
            "Scenario A",
            5,
            100.0,
            True,
            True,
        )
        is None
    )


def test_the_master_switch_silences_the_whole_run_toast_family():
    # One guard, both shapes. Each payload earns a toast with the switch on,
    # so the off assertions cannot pass vacuously.
    shapes = (
        _payload(score=830.0),  # threshold verdict
        _payload(is_new_sensitivity=True),  # top-N placement
    )

    for payload in shapes:
        assert _notification(payload) is not None
        assert _notification(payload, run_notification_switch=False) is None


def test_the_master_switch_guard_precedes_the_celebration_yield():
    # The two settings are independent families, and the order says which one
    # answers first: with run notifications off the page is silent whether or
    # not the drain celebrated the run.
    celebrated = _payload(score=830.0, celebrated_run_id="run-1.csv")
    ordinary = _payload(score=830.0)

    assert _notification(celebrated, run_notification_switch=False) is None
    assert _notification(ordinary, run_notification_switch=False) is None


# --- Normalized sensitivity groups, watchdog to toast ------------------------

NORMALIZED_SCENARIO = "Normalized Scenario"
NORMALIZED_KEY = "40.8 cm/360"


def _stats_file(tmp_path, name, *, sens_scale, horizontal_sens, score):
    """Write one real stats file the parser will read, and return its path."""
    file_path = tmp_path / f"{name} - Challenge - 2025.03.04-21.30.00 Stats.csv"
    file_path.write_text(
        "\n".join(
            [
                f"Score:,{score}",
                f"Sens Scale:,{sens_scale}",
                # 0.2 Valorant and 40.8 cm/360 are the same physical
                # sensitivity at 1600 DPI, so both files record this increment.
                "Sens Increment:,0.199886",
                f"Horiz Sens:,{horizontal_sens}",
                f"Vert Sens:,{horizontal_sens}",
                "DPI:,1600",
                f"Scenario:,{NORMALIZED_SCENARIO}",
                data_service.POSSIBLE_SUB_CSV_HEADERS[0],
                "Rifle,100,50,75,100,,Valorant,0.2,0.2,103,0,0,0,0,0,0,0,0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return file_path


def _existing_runs(*scores):
    """The score-ascending SortedKeyList the production stores hold."""
    return SortedList(
        [
            RunData(
                datetime_object=datetime(2025, 3, 1, 12) + timedelta(minutes=index),
                score=score,
                sens_scale="cm/360",
                horizontal_sens=40.8,
                scenario=NORMALIZED_SCENARIO,
                accuracy=0.5,
            )
            for index, score in enumerate(scores)
        ],
        key=lambda item: item.score,
    )


def _import_through_watchdog(monkeypatch, file_path, *, group_scores, high_score):
    """Import one real file and return the run event Home would receive."""
    messages = []
    monkeypatch.setattr(file_watchdog.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        file_watchdog, "message_queue", SimpleNamespace(append=messages.append)
    )
    monkeypatch.setattr(
        file_watchdog, "load_csv_file_into_database", lambda _file: True
    )
    monkeypatch.setattr(
        file_watchdog, "schedule_rank_freshness_refresh", lambda *_args: None
    )
    monkeypatch.setattr(file_watchdog, "is_scenario_in_database", lambda _name: True)
    monkeypatch.setattr(file_watchdog, "get_high_score", lambda _name: high_score)
    monkeypatch.setattr(
        file_watchdog,
        "get_sensitivities_vs_runs",
        lambda _name: {NORMALIZED_KEY: _existing_runs(*group_scores)},
    )

    file_watchdog.NewFileHandler().on_created(
        SimpleNamespace(is_directory=False, src_path=str(file_path))
    )

    assert len(messages) == 1
    return messages[0]


def _payload_from_message(message) -> RunEventsPayload:
    """Project the queued message the way the app shell's drain does."""
    return {
        "latest": _run_event_data(message, message.datetime_created, 120.0),
        "celebrated_run_id": None,
    }


def test_a_converted_run_is_placed_against_the_group_it_normalizes_into(
    monkeypatch,
    tmp_path,
):
    # The converted run joins a group that already holds five native runs, so
    # its place is counted against the merged history. Against the converted
    # runs alone it would have been the best; here it is sixth, which is
    # outside Top N, and with the threshold verdict off that means no toast.
    message = _import_through_watchdog(
        monkeypatch,
        _stats_file(
            tmp_path,
            "converted-into-native-group",
            sens_scale="Valorant",
            horizontal_sens="0.2",
            score=95,
        ),
        group_scores=(90, 100, 101, 102, 103, 104),
        high_score=104,
    )

    assert message.sensitivity == NORMALIZED_KEY
    assert message.is_new_sensitivity is False
    assert message.nth_score == 6

    assert (
        run_verdict_toast.build_run_event_notification(
            _payload_from_message(message),
            NORMALIZED_SCENARIO,
            5,
            100.0,
            False,
            True,
        )
        is None
    )


def test_a_native_run_at_a_converted_groups_value_is_not_a_new_sensitivity(
    monkeypatch,
    tmp_path,
):
    # The group exists only because converted runs landed on it, so this native
    # run is not the scenario's first at 40.8 cm/360. It therefore gets a
    # threshold verdict instead of the placement-only first-run toast.
    message = _import_through_watchdog(
        monkeypatch,
        _stats_file(
            tmp_path,
            "native-into-converted-group",
            sens_scale="cm/360",
            horizontal_sens="40.8",
            score=85,
        ),
        group_scores=(80, 85, 90),
        high_score=90,
    )

    assert message.sensitivity == NORMALIZED_KEY
    assert message.is_new_sensitivity is False
    assert message.scenario_previous_best == 90

    notification = run_verdict_toast.build_run_event_notification(
        _payload_from_message(message),
        NORMALIZED_SCENARIO,
        5,
        95.0,
        True,
        True,
    )

    assert notification["title"] == "Below threshold"
    assert notification["message"] == (
        f"{NORMALIZED_SCENARIO}: 85.00, 94.4% of PB (need 95.0%). "
        f"Still your 2nd-best at {NORMALIZED_KEY}."
    )
