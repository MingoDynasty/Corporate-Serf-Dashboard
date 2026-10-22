"""Exercise screenshot sample data through the production run parser."""

from collections import Counter

from scripts import capture_screenshots
from source.kovaaks.data_service import extract_data_from_file
from source.kovaaks.play_sessions import split_into_play_sessions
from source.kovaaks.typical_score import build_typical_scores


def _sample_runs(monkeypatch, tmp_path):
    monkeypatch.setattr(
        capture_screenshots, "PLAYLIST_NAMES", ("Viscose Benchmark S2 - Medium",)
    )
    samples = capture_screenshots.write_sample_state(tmp_path, 12345)
    runs = [
        extract_data_from_file(str(path)) for path in (tmp_path / "stats").glob("*.csv")
    ]
    assert runs and all(run is not None for run in runs)
    return samples, runs


def test_sample_history_uses_valid_runs_and_matching_leaderboard_scores(
    monkeypatch, tmp_path
):
    samples, runs = _sample_runs(monkeypatch, tmp_path)
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


def test_sample_sessions_have_no_overlapping_runs(monkeypatch, tmp_path):
    _, runs = _sample_runs(monkeypatch, tmp_path)
    chronological = sorted(runs, key=lambda run: run.datetime_object)
    assert all(
        previous.datetime_object <= following.run_start
        for previous, following in zip(chronological, chronological[1:])
    )
    assert max(run.datetime_object for run in runs) < capture_screenshots.NOW
    assert Counter(run.scenario for run in runs)[capture_screenshots.SCENARIO] == 96
