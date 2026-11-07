"""The excluded-runs store: one stamped file the player's presses write."""

import json

import pytest

from source.kovaaks import excluded_runs_service as excluded
from source.utilities.store_schema import StoreState, UnsupportedSchemaError

RUN = "Ground Plaza Sparky V3 - Challenge - 2020.07.29-20.15.03 Stats.csv"
OTHER = "Ground Plaza Sparky V3 - Challenge - 2026.10.29-23.57.57 Stats.csv"


@pytest.fixture
def store_path(monkeypatch, tmp_path):
    """Point the store at a file whose folder doesn't exist yet."""
    path = tmp_path / "data" / "excluded_runs.json"
    monkeypatch.setattr(excluded, "EXCLUDED_RUNS_PATH", path)
    return path


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_no_file_excludes_nothing(store_path) -> None:
    assert excluded.read_excluded_runs().state is StoreState.MISSING
    assert excluded.excluded_run_ids() == frozenset()


def test_excluding_a_run_writes_a_stamped_file(store_path) -> None:
    assert excluded.set_run_excluded(RUN, excluded=True) == frozenset({RUN})

    payload = json.loads(store_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert [entry["run"] for entry in payload["excluded_runs"]] == [RUN]
    assert payload["excluded_runs"][0]["excluded_at"].endswith("Z")
    assert excluded.excluded_run_ids() == frozenset({RUN})


def test_including_a_run_again_removes_only_that_run(store_path) -> None:
    excluded.set_run_excluded(RUN, excluded=True)
    excluded.set_run_excluded(OTHER, excluded=True)

    assert excluded.set_run_excluded(RUN, excluded=False) == frozenset({OTHER})
    assert excluded.excluded_run_ids() == frozenset({OTHER})


def test_excluding_a_run_twice_keeps_its_first_time(store_path) -> None:
    excluded.set_run_excluded(RUN, excluded=True)
    first = store_path.read_text(encoding="utf-8")

    excluded.set_run_excluded(RUN, excluded=True)

    assert store_path.read_text(encoding="utf-8") == first


def test_a_broken_file_counts_every_run_and_is_copied_aside_on_a_write(
    store_path,
) -> None:
    _write(store_path, "{not json")

    document = excluded.read_excluded_runs()
    assert document.state is StoreState.ERROR
    assert "excluded runs file" in document.message
    assert excluded.excluded_run_ids() == frozenset()

    excluded.set_run_excluded(RUN, excluded=True)

    assert excluded.excluded_run_ids() == frozenset({RUN})
    backups = list(store_path.parent.glob("excluded_runs.json.corrupt-*.bak"))
    assert [backup.read_text(encoding="utf-8") for backup in backups] == ["{not json"]


@pytest.mark.parametrize(
    "payload",
    [
        {"excluded_runs": "all"},
        {"excluded_runs": [{"run": RUN}]},
        {"excluded_runs": [{"run": "", "excluded_at": "2026-11-07T10:00:00Z"}]},
        {"excluded_runs": [{"run": RUN, "excluded_at": "2026-11-07T10:00:00"}]},
        {
            "excluded_runs": [
                {"run": RUN, "excluded_at": "2026-11-07T10:00:00Z"},
                {"run": RUN, "excluded_at": "2026-11-07T10:00:01Z"},
            ]
        },
        {"excluded_runs": [], "reason": "unknown key"},
        {
            "excluded_runs": [
                {"run": RUN, "excluded_at": "2026-11-07T10:00:00Z", "x": 1}
            ]
        },
    ],
)
def test_a_payload_outside_v1_is_an_error(store_path, payload) -> None:
    _write(store_path, json.dumps({"schema_version": 1, **payload}))

    assert excluded.read_excluded_runs().state is StoreState.ERROR
    assert excluded.excluded_run_ids() == frozenset()


def test_a_file_from_a_newer_build_refuses_every_write(store_path) -> None:
    text = json.dumps({"schema_version": 99, "excluded_runs": []})
    _write(store_path, text)

    assert excluded.read_excluded_runs().state is StoreState.FUTURE
    assert excluded.excluded_run_ids() == frozenset()
    with pytest.raises(UnsupportedSchemaError):
        excluded.set_run_excluded(RUN, excluded=True)
    assert store_path.read_text(encoding="utf-8") == text
