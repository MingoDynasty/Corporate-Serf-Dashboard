"""Exercise screenshot sample data through the production run parser."""

from collections import Counter
from datetime import timedelta

from scripts import capture_screenshots
from source.kovaaks.data_service import extract_data_from_file
from source.kovaaks.play_sessions import split_into_play_sessions
from source.kovaaks.typical_score import (
    build_typical_scores,
    typical_score_fade_time,
    typical_score_recency,
)


def _sample_runs(tmp_path):
    samples = capture_screenshots.write_sample_state(tmp_path, 12345)
    runs = [
        extract_data_from_file(str(path)) for path in (tmp_path / "stats").glob("*.csv")
    ]
    assert runs and all(run is not None for run in runs)
    return samples, runs


def test_sample_history_uses_valid_runs_and_matching_leaderboard_scores(tmp_path):
    samples, runs = _sample_runs(tmp_path)
    assert {run.scenario for run in runs} == {sample["name"] for sample in samples}
    for sample in samples:
        local_runs = [run for run in runs if run.scenario == sample["name"]]
        assert max(run.score for run in local_runs) == sample["score"]
        assert 0 < sample["rank"] <= sample["total"]
        assert all(run.run_length.total_seconds() == 60 for run in local_runs)
    featured = sorted(
        [run for run in runs if run.scenario == capture_screenshots.SCENARIO],
        key=lambda run: run.datetime_object,
    )
    assert len(featured) == 96
    assert len(split_into_play_sessions(featured)) == 8
    assert (
        build_typical_scores(featured, split_into_play_sessions(runs))[-1].median
        is not None
    )


def test_sample_sessions_have_no_overlapping_runs(tmp_path):
    _, runs = _sample_runs(tmp_path)
    chronological = sorted(runs, key=lambda run: run.datetime_object)
    assert all(
        previous.datetime_object <= following.run_start
        for previous, following in zip(chronological, chronological[1:])
    )
    assert max(run.datetime_object for run in runs) < capture_screenshots.NOW
    assert Counter(run.scenario for run in runs)[capture_screenshots.SCENARIO] == 96


def test_sample_chart_contains_gaps_with_faded_and_full_strength_support(tmp_path):
    _, runs = _sample_runs(tmp_path)
    featured = sorted(
        (run for run in runs if run.scenario == capture_screenshots.SCENARIO),
        key=lambda run: run.datetime_object,
    )
    values = build_typical_scores(featured, split_into_play_sessions(runs))
    latest = typical_score_recency(values[-1], capture_screenshots.NOW)
    assert latest.recent and latest.run_count == 20
    recency = {
        typical_score_recency(value, run.datetime_object).recent
        for run, value in zip(featured, values)
        if value.known
    }
    assert recency == {False, True}
    fading_holds = [
        (run, following, typical_score_fade_time(value))
        for run, following, value in zip(featured, featured[1:], values)
        if value.known
        and following.datetime_object - run.datetime_object > timedelta(days=30)
    ]
    assert len(fading_holds) >= 2
    assert all(
        run.datetime_object < fade_time < following.datetime_object
        for run, following, fade_time in fading_holds
    )
