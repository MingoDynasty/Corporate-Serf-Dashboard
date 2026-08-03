"""Startup seeding of leaderboard IDs from the bundled corpus.

Two halves: the asserted-set collection in data_service (scan the corpus, drop
conflicts, report a partial load) and the atomic merge in api_service (add /
refresh / remove-absent, never touch learned).
"""

import json
import logging
from pathlib import Path

import pytest

from source.kovaaks import api_service, data_service
from source.kovaaks.data_models import PlaylistData, Scenario


def _mapping_path(cache_dir: Path) -> Path:
    return cache_dir / "scenario_leaderboards" / "scenario_name_to_leaderboard_id.json"


def _read_mapping(cache_dir: Path) -> dict:
    return json.loads(_mapping_path(cache_dir).read_text(encoding="utf-8"))


def _write_mapping(cache_dir: Path, mappings: dict) -> None:
    path = _mapping_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mappings), encoding="utf-8")


@pytest.fixture
def cache_dir(monkeypatch, tmp_path):
    cache_root = tmp_path / "cache"
    monkeypatch.setattr(api_service, "CACHE_DIR", cache_root)
    return cache_root


# --- merge_seed_leaderboard_ids -------------------------------------------------


def test_merge_adds_missing_asserted_name(cache_dir):
    api_service.merge_seed_leaderboard_ids({"Alpha": 111}, allow_removals=True)

    entry = _read_mapping(cache_dir)["Alpha"]
    assert entry["leaderboard_id"] == 111
    assert entry["source"] == "seed"


def test_merge_never_touches_learned_entry(cache_dir):
    _write_mapping(
        cache_dir,
        {"Alpha": {"leaderboard_id": 999, "source": "total-play", "fetched_at": "t"}},
    )

    api_service.merge_seed_leaderboard_ids({"Alpha": 111}, allow_removals=True)

    # A name with a live-learned value keeps it and never gains a seed-owned row.
    assert _read_mapping(cache_dir) == {
        "Alpha": {"leaderboard_id": 999, "source": "total-play", "fetched_at": "t"}
    }


def test_merge_refreshes_changed_seed_entry(cache_dir):
    _write_mapping(
        cache_dir,
        {"Alpha": {"leaderboard_id": 100, "source": "seed", "fetched_at": "old"}},
    )

    api_service.merge_seed_leaderboard_ids({"Alpha": 111}, allow_removals=True)

    entry = _read_mapping(cache_dir)["Alpha"]
    assert entry["leaderboard_id"] == 111
    assert entry["source"] == "seed"
    assert entry["fetched_at"] != "old"


def test_merge_removes_seed_entry_absent_from_asserted(cache_dir):
    _write_mapping(
        cache_dir,
        {
            "Gone": {"leaderboard_id": 5, "source": "seed", "fetched_at": "t"},
            "Keep": {"leaderboard_id": 7, "source": "seed", "fetched_at": "t"},
        },
    )

    api_service.merge_seed_leaderboard_ids({"Keep": 7}, allow_removals=True)

    mappings = _read_mapping(cache_dir)
    assert "Gone" not in mappings
    assert mappings["Keep"]["leaderboard_id"] == 7


def test_merge_does_not_remove_learned_entry_absent_from_asserted(cache_dir):
    _write_mapping(
        cache_dir,
        {
            "Learned": {
                "leaderboard_id": 9,
                "source": "scenario-search",
                "fetched_at": "t",
            }
        },
    )

    api_service.merge_seed_leaderboard_ids({}, allow_removals=True)

    assert _read_mapping(cache_dir) == {
        "Learned": {"leaderboard_id": 9, "source": "scenario-search", "fetched_at": "t"}
    }


def test_merge_suppresses_removals_but_still_adds_on_partial_load(cache_dir):
    _write_mapping(
        cache_dir,
        {
            "Gone": {"leaderboard_id": 5, "source": "seed", "fetched_at": "t"},
            "Learned": {"leaderboard_id": 9, "source": "total-play", "fetched_at": "t"},
        },
    )

    api_service.merge_seed_leaderboard_ids({"New": 3}, allow_removals=False)

    mappings = _read_mapping(cache_dir)
    # Removal suppressed, learned untouched, add still applied.
    assert mappings["Gone"]["leaderboard_id"] == 5
    assert mappings["Learned"]["source"] == "total-play"
    assert mappings["New"] == {
        "leaderboard_id": 3,
        "source": "seed",
        "fetched_at": mappings["New"]["fetched_at"],
    }


def test_merge_leaves_unchanged_seed_entry_untouched(cache_dir):
    _write_mapping(
        cache_dir,
        {"Alpha": {"leaderboard_id": 111, "source": "seed", "fetched_at": "fixed"}},
    )

    api_service.merge_seed_leaderboard_ids({"Alpha": 111}, allow_removals=True)

    # No refresh for an unchanged seed value: the timestamp is not rewritten.
    assert _read_mapping(cache_dir)["Alpha"]["fetched_at"] == "fixed"


# --- data_service collection ----------------------------------------------------


def _configure_bundled_root(monkeypatch, tmp_path) -> Path:
    bundled_root = tmp_path / "resources" / "benchmarks"
    user_root = tmp_path / "data" / "playlists"
    bundled_root.mkdir(parents=True)
    monkeypatch.setattr(
        data_service, "BUNDLED_PLAYLIST_DIRECTORY_PATH", bundled_root.resolve()
    )
    monkeypatch.setattr(
        data_service, "USER_PLAYLIST_DIRECTORY_PATH", user_root.resolve()
    )
    monkeypatch.setattr(data_service, "playlist_database", {})
    return bundled_root


def _write_playlist(path: Path, code: str, scenarios: list[Scenario]) -> None:
    playlist = PlaylistData(name=path.stem, code=code, scenarios=scenarios)
    path.write_text(
        playlist.model_dump_json(indent=2, exclude_none=True) + "\n", encoding="utf-8"
    )


def test_get_bundled_leaderboard_seed_collects_and_excludes_conflicts(
    monkeypatch, tmp_path, caplog
):
    bundled_root = _configure_bundled_root(monkeypatch, tmp_path)
    _write_playlist(
        bundled_root / "one.json",
        "CodeOne",
        [
            Scenario(name="Alpha", leaderboard_id=1),
            Scenario(name="Beta", leaderboard_id=2),
            Scenario(name="Dup", leaderboard_id=9),
            Scenario(name="NoId"),  # leaderboard_id is None -> ignored
        ],
    )
    _write_playlist(
        bundled_root / "two.json",
        "CodeTwo",
        [
            Scenario(name="Alpha", leaderboard_id=1),  # agrees -> asserted
            Scenario(name="Gamma", leaderboard_id=3),
            Scenario(name="Dup", leaderboard_id=8),  # disagrees -> excluded
        ],
    )

    with caplog.at_level(logging.WARNING, logger=data_service.__name__):
        data_service.load_playlists()
        asserted, load_complete = data_service.get_bundled_leaderboard_seed()

    assert asserted == {"Alpha": 1, "Beta": 2, "Gamma": 3}
    assert load_complete is True
    assert any("disagrees on leaderboard id" in m for m in caplog.messages)


def test_bundled_load_failure_marks_corpus_incomplete(monkeypatch, tmp_path):
    bundled_root = _configure_bundled_root(monkeypatch, tmp_path)
    _write_playlist(
        bundled_root / "good.json",
        "GoodCode",
        [Scenario(name="Alpha", leaderboard_id=1)],
    )
    (bundled_root / "broken.json").write_text("{not json", encoding="utf-8")

    data_service.load_playlists()
    asserted, load_complete = data_service.get_bundled_leaderboard_seed()

    assert asserted == {"Alpha": 1}
    assert load_complete is False


def test_empty_bundled_dir_suppresses_removals(monkeypatch, tmp_path, cache_dir):
    # A present-but-empty bundled root parses zero files and never trips the
    # per-file failure handlers, yet it is the maximal partial view — the merge
    # must suppress removals, not wipe every seed row.
    _configure_bundled_root(monkeypatch, tmp_path)  # creates an empty bundled dir
    _write_mapping(
        cache_dir,
        {"SeedRow": {"leaderboard_id": 5, "source": "seed", "fetched_at": "t"}},
    )

    data_service.load_playlists()
    asserted, load_complete = data_service.get_bundled_leaderboard_seed()
    assert asserted == {}
    assert load_complete is False

    data_service.seed_leaderboard_ids_from_bundled_corpus()
    assert "SeedRow" in _read_mapping(cache_dir)


def test_missing_bundled_dir_suppresses_removals(monkeypatch, tmp_path, cache_dir):
    # A missing bundled root (broken install) must not compound the breakage by
    # retracting every seeded mapping; learned rows stay untouched regardless.
    missing = tmp_path / "does-not-exist" / "benchmarks"
    monkeypatch.setattr(
        data_service, "BUNDLED_PLAYLIST_DIRECTORY_PATH", missing.resolve()
    )
    monkeypatch.setattr(
        data_service,
        "USER_PLAYLIST_DIRECTORY_PATH",
        (tmp_path / "data" / "playlists").resolve(),
    )
    monkeypatch.setattr(data_service, "playlist_database", {})
    _write_mapping(
        cache_dir,
        {
            "SeedRow": {"leaderboard_id": 5, "source": "seed", "fetched_at": "t"},
            "Learned": {"leaderboard_id": 2, "source": "total-play", "fetched_at": "t"},
        },
    )

    data_service.load_playlists()
    asserted, load_complete = data_service.get_bundled_leaderboard_seed()
    assert asserted == {}
    assert load_complete is False

    data_service.seed_leaderboard_ids_from_bundled_corpus()
    mappings = _read_mapping(cache_dir)
    assert mappings["SeedRow"]["leaderboard_id"] == 5  # not retracted
    assert mappings["Learned"]["source"] == "total-play"


# --- end-to-end orchestrator ----------------------------------------------------


def test_seed_from_corpus_adds_ids_and_drops_conflicted_seed_row(
    monkeypatch, tmp_path, cache_dir
):
    # An existing seed-owned row whose name two bundled files now disagree on is
    # removed; a fresh asserted name is added.
    _write_mapping(
        cache_dir,
        {"Dup": {"leaderboard_id": 4, "source": "seed", "fetched_at": "t"}},
    )
    bundled_root = _configure_bundled_root(monkeypatch, tmp_path)
    _write_playlist(
        bundled_root / "one.json",
        "CodeOne",
        [
            Scenario(name="Alpha", leaderboard_id=1),
            Scenario(name="Dup", leaderboard_id=4),
        ],
    )
    _write_playlist(
        bundled_root / "two.json",
        "CodeTwo",
        [Scenario(name="Dup", leaderboard_id=5)],  # disagrees -> Dup excluded
    )

    data_service.load_playlists()
    data_service.seed_leaderboard_ids_from_bundled_corpus()

    mappings = _read_mapping(cache_dir)
    assert mappings["Alpha"]["leaderboard_id"] == 1
    assert mappings["Alpha"]["source"] == "seed"
    # Dup left the asserted set (conflict), so its seed-owned row is retracted.
    assert "Dup" not in mappings
