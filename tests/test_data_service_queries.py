import logging
from datetime import date, datetime, timedelta

import pytest
from sortedcontainers import SortedList

from source.kovaaks import data_service
from source.kovaaks.data_models import PlaylistData, Rank, RunData, Scenario

SCENARIO_NAME = "1w4ts"
START = datetime(2026, 7, 1, 12, 0, 0)


def _run(
    score: float,
    when: datetime,
    *,
    scenario: str = SCENARIO_NAME,
    horizontal_sens: float = 40.0,
) -> RunData:
    return RunData(
        datetime_object=when,
        score=score,
        sens_scale="cm/360",
        horizontal_sens=horizontal_sens,
        scenario=scenario,
        accuracy=0.5,
    )


def _playlist(code: str, *scenarios: Scenario) -> PlaylistData:
    return PlaylistData(name=f"{code} playlist", code=code, scenarios=list(scenarios))


def _scores(grouped: dict) -> dict:
    return {key: [run.score for run in runs] for key, runs in grouped.items()}


@pytest.fixture
def load_runs(monkeypatch):
    """Load runs through the real CSV loader, so every store has its real shape."""
    monkeypatch.setattr(data_service, "kovaaks_database", {})
    monkeypatch.setattr(
        data_service,
        "run_database",
        SortedList(key=lambda run: run.datetime_object),
    )

    def load(*runs: RunData) -> None:
        pending = iter(runs)
        monkeypatch.setattr(
            data_service, "extract_data_from_file", lambda _file: next(pending)
        )
        for index in range(len(runs)):
            assert data_service.load_csv_file_into_database(f"run-{index}.csv")

    return load


@pytest.fixture
def playlists(monkeypatch):
    """Replace the playlist store with the given playlists, keyed by code."""

    def install(*items: PlaylistData) -> None:
        monkeypatch.setattr(
            data_service,
            "playlist_database",
            {playlist.code: playlist for playlist in items},
        )

    return install


def test_time_vs_runs_keeps_each_days_highest_scores_ascending(load_runs):
    load_runs(
        _run(5.0, START),
        _run(9.0, START + timedelta(hours=1)),
        _run(7.0, START + timedelta(hours=2)),
        _run(3.0, START + timedelta(days=1)),
    )

    result = data_service.get_time_vs_runs(SCENARIO_NAME, 2, datetime(2026, 1, 1))

    assert _scores(result) == {
        date(2026, 7, 1): [7.0, 9.0],
        date(2026, 7, 2): [3.0],
    }


def test_time_vs_runs_keeps_every_run_when_top_n_exceeds_the_day(load_runs):
    load_runs(_run(5.0, START), _run(9.0, START + timedelta(hours=1)))

    result = data_service.get_time_vs_runs(SCENARIO_NAME, 10, datetime(2026, 1, 1))

    assert _scores(result) == {date(2026, 7, 1): [5.0, 9.0]}


def test_time_vs_runs_oldest_date_is_inclusive(load_runs):
    load_runs(
        _run(9.0, START - timedelta(seconds=1)),
        _run(5.0, START),
        _run(7.0, START + timedelta(hours=1)),
    )

    result = data_service.get_time_vs_runs(SCENARIO_NAME, 10, START)

    assert _scores(result) == {date(2026, 7, 1): [5.0, 7.0]}


def test_sensitivities_filtered_keeps_each_keys_highest_scores_highest_first(
    load_runs,
):
    load_runs(
        _run(5.0, START, horizontal_sens=40.0),
        _run(9.0, START + timedelta(hours=1), horizontal_sens=40.0),
        _run(7.0, START + timedelta(hours=2), horizontal_sens=40.0),
        _run(4.0, START + timedelta(hours=3), horizontal_sens=35.0),
        _run(6.0, START + timedelta(hours=4), horizontal_sens=35.0),
        _run(2.0, START + timedelta(hours=5), horizontal_sens=35.0),
    )

    result = data_service.get_sensitivities_vs_runs_filtered(
        SCENARIO_NAME, 2, datetime(2026, 1, 1)
    )

    assert _scores(result) == {
        "40.0 cm/360": [9.0, 7.0],
        "35.0 cm/360": [6.0, 4.0],
    }


def test_sensitivities_filtered_drops_a_key_with_no_runs_in_range(load_runs):
    load_runs(
        _run(8.0, START - timedelta(days=1), horizontal_sens=30.0),
        _run(5.0, START + timedelta(hours=1), horizontal_sens=40.0),
    )

    result = data_service.get_sensitivities_vs_runs_filtered(SCENARIO_NAME, 5, START)

    assert _scores(result) == {"40.0 cm/360": [5.0]}


def test_sensitivities_filtered_oldest_date_is_inclusive(load_runs):
    load_runs(
        _run(9.0, START - timedelta(seconds=1)),
        _run(5.0, START),
        _run(7.0, START + timedelta(hours=1)),
    )

    result = data_service.get_sensitivities_vs_runs_filtered(SCENARIO_NAME, 5, START)

    assert _scores(result) == {"40.0 cm/360": [7.0, 5.0]}


@pytest.mark.parametrize(
    ("checkpoint_threshold", "expected_indices"),
    [(1, [0, 60, 120]), (2, [0, 120])],
)
def test_aim_training_checkpoints_count_every_run_as_one_minute(
    load_runs,
    checkpoint_threshold,
    expected_indices,
):
    """Pins today's behavior: each run counts as one minute, whatever its length."""
    runs = [_run(1.0, START + timedelta(hours=index)) for index in range(121)]
    load_runs(*runs)

    result = data_service.get_aim_training_checkpoints(checkpoint_threshold)

    assert result == {
        runs[index].datetime_object: checkpoint_threshold * position
        for position, index in enumerate(expected_indices)
    }


def test_journey_emits_a_point_per_personal_best_once_every_scenario_scored(
    load_runs,
    playlists,
):
    playlists(_playlist("P1", Scenario(name="S1"), Scenario(name="S2")))
    t1, t2, t3, t4, t5 = (START + timedelta(hours=hour) for hour in range(5))
    load_runs(
        _run(100.0, t1, scenario="S1"),
        _run(50.0, t2, scenario="S2"),
        _run(999.0, t2 + timedelta(minutes=30), scenario="Unrelated"),
        _run(200.0, t3, scenario="S1"),
        _run(40.0, t4, scenario="S2"),
        _run(200.0, t5, scenario="S1"),
    )

    # No point at t1 (S2 unscored); t2 is mean(100/200, 50/50); t4 is not a
    # personal best and t5 only equals one.
    assert data_service.get_aim_training_journey_for_playlist("P1") == {
        t2: 0.75,
        t3: 1.0,
    }


def test_journey_for_an_unknown_playlist_is_empty(load_runs, playlists):
    playlists(_playlist("P1", Scenario(name="S1")))
    load_runs(_run(100.0, START, scenario="S1"))

    assert data_service.get_aim_training_journey_for_playlist("Unknown") == {}


def test_journey_never_starts_while_a_scenario_has_only_zero_scores(
    load_runs,
    playlists,
):
    """Pins today's behavior: an all-zero scenario blocks its playlist forever."""
    playlists(_playlist("P1", Scenario(name="S1"), Scenario(name="S2")))
    load_runs(
        _run(100.0, START, scenario="S1"),
        _run(0.0, START + timedelta(hours=1), scenario="S2"),
        _run(200.0, START + timedelta(hours=2), scenario="S1"),
    )

    assert data_service.get_aim_training_journey_for_playlist("P1") == {}


def test_journeys_for_playlists_drop_unknown_codes_and_keep_order(
    load_runs,
    playlists,
):
    playlists(
        _playlist("P1", Scenario(name="S1"), Scenario(name="S2")),
        _playlist("P2", Scenario(name="S1")),
    )
    t1, t2, t3 = (START + timedelta(hours=hour) for hour in range(3))
    load_runs(
        _run(100.0, t1, scenario="S1"),
        _run(50.0, t2, scenario="S2"),
        _run(200.0, t3, scenario="S1"),
    )

    result = data_service.get_aim_training_journey_for_playlists(
        ["P2", "Unknown", "P1"]
    )

    assert list(result) == ["P2", "P1"]
    assert result == {
        "P2": {t1: 0.5, t3: 1.0},
        "P1": {t2: 0.75, t3: 1.0},
    }


def test_filter_known_playlist_codes_drops_unknown_and_keeps_order(playlists):
    playlists(_playlist("A"), _playlist("B"))

    assert data_service.filter_known_playlist_codes(["B", "Stale", "A"]) == ["B", "A"]


def test_rank_data_for_a_known_scenario(playlists, caplog):
    ranks = [
        Rank(name="Bronze", color="#aaaaaa", threshold=80.0),
        Rank(name="Silver", color="#bbbbbb", threshold=110.0),
    ]
    playlists(
        _playlist(
            "P1",
            Scenario(name="Ranked", ranks=ranks),
            Scenario(name="Unranked"),
        )
    )

    with caplog.at_level(logging.WARNING, logger=data_service.logger.name):
        assert data_service.get_rank_data_from_playlist_code("P1", "Ranked") == ranks
        assert data_service.get_rank_data_from_playlist_code("P1", "Unranked") == []

    assert not caplog.records


@pytest.mark.parametrize(
    ("playlist_code", "scenario_name"),
    [("P1", "Missing"), ("Unknown", "Ranked")],
    ids=["scenario-not-in-playlist", "unknown-playlist"],
)
def test_rank_data_lookup_miss_is_empty_and_warns(
    playlists,
    caplog,
    playlist_code,
    scenario_name,
):
    playlists(
        _playlist(
            "P1",
            Scenario(
                name="Ranked",
                ranks=[Rank(name="Bronze", color="#aaaaaa", threshold=80.0)],
            ),
        )
    )

    with caplog.at_level(logging.WARNING, logger=data_service.logger.name):
        result = data_service.get_rank_data_from_playlist_code(
            playlist_code, scenario_name
        )

    assert result == []
    assert caplog.messages == [
        f"Failed to get rank data for playlist code ({playlist_code}), "
        f"scenario ({scenario_name})"
    ]
