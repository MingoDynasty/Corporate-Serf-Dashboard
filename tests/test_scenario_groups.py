import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from source.kovaaks import evxl_snapshot, scenario_groups
from source.kovaaks.evxl_links import evxl_benchmark_url
from source.kovaaks.evxl_snapshot import EvxlCategory
from source.kovaaks.scenario_groups import (
    ScenarioGroup,
    assign_scenario_groups,
    join_scenario_groups,
)

Subcategories = list[tuple[str, str, int]]


def _category(name: str, color: str, subcategories: Subcategories) -> dict:
    return {
        "categoryName": name,
        "color": color,
        "subcategories": [
            {"subcategoryName": sub_name, "color": sub_color, "scenarioCount": count}
            for sub_name, sub_color, count in subcategories
        ],
    }


def _layout(*categories: dict) -> list[EvxlCategory]:
    return [EvxlCategory.model_validate(category) for category in categories]


TWO_LEVEL = (
    _category(
        "Clicking",
        "#111111",
        [("Static", "#aaaaaa", 2), ("Dynamic", "#bbbbbb", 1)],
    ),
    _category("Tracking", "#222222", [("Precise", "#cccccc", 2)]),
)


def _names(groups: tuple[ScenarioGroup, ...] | None) -> list[tuple[str, str]]:
    assert groups is not None
    return [(group.category, group.subcategory) for group in groups]


def _runs(groups: tuple[ScenarioGroup, ...] | None) -> list[tuple[int, int]]:
    assert groups is not None
    return [(group.category_run, group.subcategory_run) for group in groups]


def test_a_two_level_layout_gives_each_scenario_both_groups():
    groups = assign_scenario_groups(_layout(*TWO_LEVEL), 5)

    assert groups == (
        ScenarioGroup("Clicking", "#111111", 0, "Static", "#aaaaaa", 0),
        ScenarioGroup("Clicking", "#111111", 0, "Static", "#aaaaaa", 0),
        ScenarioGroup("Clicking", "#111111", 0, "Dynamic", "#bbbbbb", 1),
        ScenarioGroup("Tracking", "#222222", 1, "Precise", "#cccccc", 2),
        ScenarioGroup("Tracking", "#222222", 1, "Precise", "#cccccc", 2),
    )


def test_one_level_stored_as_categories_has_no_subcategories():
    layout = _layout(
        _category("Clicking", "#111111", [("", "#000000", 2)]),
        _category("Tracking", "#222222", [("", "#000000", 1)]),
    )

    groups = assign_scenario_groups(layout, 3)

    assert _names(groups) == [("Clicking", ""), ("Clicking", ""), ("Tracking", "")]
    assert _runs(groups) == [(0, 0), (0, 0), (1, 1)]


def test_one_level_stored_as_subcategories_is_promoted_to_categories():
    layout = _layout(
        _category("", "#000000", [("Arm", "#aaaaaa", 1), ("Wrist", "#bbbbbb", 2)])
    )

    groups = assign_scenario_groups(layout, 3)

    assert groups == (
        ScenarioGroup("Arm", "#aaaaaa", 0, "", None, 0),
        ScenarioGroup("Wrist", "#bbbbbb", 1, "", None, 1),
        ScenarioGroup("Wrist", "#bbbbbb", 1, "", None, 1),
    )


def test_a_blank_category_name_counts_as_unnamed():
    layout = _layout(_category("  ", "#000000", [("Arm", "#aaaaaa", 1)]))

    assert _names(assign_scenario_groups(layout, 1)) == [("Arm", "")]


def test_a_layout_that_names_nothing_gives_no_groups():
    layout = _layout(_category("", "#111111", [(" ", "#aaaaaa", 3)]))

    assert assign_scenario_groups(layout, 3) is None


@pytest.mark.parametrize("scenario_count", [4, 6])
def test_counts_that_dont_add_up_give_no_groups(scenario_count):
    assert assign_scenario_groups(_layout(*TWO_LEVEL), scenario_count) is None


def test_a_negative_count_gives_no_groups():
    # The total still adds up, and a walk that took it would mislabel rows.
    layout = _layout(
        _category(
            "Clicking", "#111111", [("Static", "#a00", 3), ("Dynamic", "#b00", -1)]
        )
    )

    assert assign_scenario_groups(layout, 2) is None


def test_a_boundary_moved_by_one_changes_the_neighbors_group():
    # Same total as ``TWO_LEVEL``: only a comparison with a second source can
    # tell which of the two is right, which is why the importer runs one.
    moved = (
        _category(
            "Clicking",
            "#111111",
            [("Static", "#aaaaaa", 1), ("Dynamic", "#bbbbbb", 2)],
        ),
        TWO_LEVEL[1],
    )

    assert _names(assign_scenario_groups(_layout(*TWO_LEVEL), 5))[1] == (
        "Clicking",
        "Static",
    )
    assert _names(assign_scenario_groups(_layout(*moved), 5))[1] == (
        "Clicking",
        "Dynamic",
    )


def test_names_are_trimmed():
    layout = _layout(_category(" Clicking ", "#111111", [("Static  ", "#aaaaaa", 1)]))

    assert _names(assign_scenario_groups(layout, 1)) == [("Clicking", "Static")]


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ("#FFF", "#FFFFFF"),
        ("#a1b", "#aa11bb"),
        ("#A1B2C3", "#A1B2C3"),
        (" #a1b2c3 ", "#a1b2c3"),
        ("red", None),
        ("#12", None),
        ("#12345", None),
        ("rgb(1, 2, 3)", None),
        ("", None),
    ],
)
def test_a_color_is_six_digit_hex_or_nothing(stored, expected):
    layout = _layout(_category("Clicking", stored, [("Static", stored, 1)]))

    groups = assign_scenario_groups(layout, 1)

    assert groups is not None
    assert groups[0].category_color == expected
    assert groups[0].subcategory_color == expected


def test_two_neighboring_groups_with_one_name_get_different_runs():
    # As on CONTINIUM TacFPS Benchmarks E1: MICRO ends one category and
    # begins the next. With the name as the cell value the two would merge.
    layout = _layout(
        _category("Flicking", "#111111", [("Micro", "#aaaaaa", 1)]),
        _category("Dynamic", "#222222", [("Micro", "#aaaaaa", 1)]),
    )

    groups = assign_scenario_groups(layout, 2)

    assert _names(groups) == [("Flicking", "Micro"), ("Dynamic", "Micro")]
    assert _runs(groups) == [(0, 0), (1, 1)]


def test_same_named_neighbors_in_one_category_are_one_run():
    layout = _layout(
        _category(
            "Clicking",
            "#111111",
            [
                ("Static", "#aaaaaa", 1),
                ("Static", "#bbbbbb", 1),
                ("Dynamic", "#c00", 1),
            ],
        ),
    )

    assert _runs(assign_scenario_groups(layout, 3)) == [(0, 0), (0, 0), (0, 1)]


# --- the join against a snapshot file ---


def _entry(sharecode: str, categories: object, name: str = "Easy") -> dict:
    return {"difficultyName": name, "sharecode": sharecode, "categories": categories}


SNAPSHOT = [
    {
        "benchmarkName": "Two Level",
        "difficulties": [
            _entry("KovaaKsTwoLevel", list(TWO_LEVEL)),
            _entry("KovaaKsCasedCode", list(TWO_LEVEL), "Medium"),
            # A scenario count that is not a number.
            _entry(
                "KovaaKsBadLayout",
                [
                    {
                        "categoryName": "Clicking",
                        "color": "#111111",
                        "subcategories": [
                            {
                                "subcategoryName": "Static",
                                "color": "#aaaaaa",
                                "scenarioCount": "many",
                            }
                        ],
                    }
                ],
                "Hard",
            ),
            _entry("KovaaKsExcluded", list(TWO_LEVEL), "Excluded"),
        ],
    },
    {
        "benchmarkName": "Listed Again",
        "difficulties": [
            _entry(
                "KovaaKsTwoLevel",
                [_category("Later", "#333333", [("Listing", "#dddddd", 5)])],
            )
        ],
    },
]


@pytest.fixture(autouse=True)
def fresh_snapshot_memo() -> Iterator[None]:
    """Keep one test's snapshot from answering for the next."""
    evxl_snapshot.evxl_entries_by_code.cache_clear()
    yield
    evxl_snapshot.evxl_entries_by_code.cache_clear()


@pytest.fixture
def snapshot_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point the read at a snapshot file holding ``SNAPSHOT``."""
    path = tmp_path / "benchmarks.json"
    path.write_text(json.dumps(SNAPSHOT), encoding="utf-8")
    monkeypatch.setattr(evxl_snapshot, "EVXL_BENCHMARKS_SNAPSHOT_PATH", path)
    return path


def test_a_code_joins_its_snapshot_layout(snapshot_path):
    assert join_scenario_groups("KovaaKsTwoLevel", 5) == assign_scenario_groups(
        _layout(*TWO_LEVEL), 5
    )


def test_a_code_joins_whatever_its_letter_case(snapshot_path):
    # The bundled file's code and the snapshot's have differed by case.
    assert join_scenario_groups("KovaaKscasedcode", 5) is not None


def test_a_code_listed_twice_joins_its_first_listing(snapshot_path):
    assert ("Later", "Listing") not in _names(
        join_scenario_groups("KovaaKsTwoLevel", 5)
    )


def test_a_code_the_snapshot_does_not_list_gets_no_groups(snapshot_path):
    assert join_scenario_groups("KovaaKsNotABenchmark", 5) is None


def test_counts_that_dont_add_up_get_no_groups_through_the_join(snapshot_path):
    assert join_scenario_groups("KovaaKsTwoLevel", 6) is None


def test_an_unusable_layout_gets_no_groups_and_keeps_its_link(snapshot_path, caplog):
    with caplog.at_level(logging.WARNING, logger=evxl_snapshot.__name__):
        assert join_scenario_groups("KovaaKsBadLayout", 1) is None

    assert evxl_benchmark_url("KovaaKsBadLayout", None) == (
        "https://evxl.app/benchmarks/Two%20Level"
    )
    assert "categories for KovaaKsBadLayout are not in the expected format" in (
        caplog.text
    )
    # Its neighbors in the same file are untouched.
    assert join_scenario_groups("KovaaKsTwoLevel", 5) is not None


def test_a_code_on_the_exclusion_list_gets_no_groups(snapshot_path, monkeypatch):
    assert join_scenario_groups("KovaaKsExcluded", 5) is not None

    monkeypatch.setattr(
        scenario_groups, "GROUP_EXCLUDED_PLAYLIST_CODES", frozenset({"KovaaKsExcluded"})
    )

    assert join_scenario_groups("KovaaKsExcluded", 5) is None
    assert evxl_benchmark_url("KovaaKsExcluded", None) is not None


@pytest.mark.parametrize(
    "content",
    [
        None,
        "{ not json",
        json.dumps({"benchmarkName": "Not a list"}),
        json.dumps([{"benchmarkName": "No difficulties"}]),
    ],
    ids=["missing", "not JSON", "not a list", "no difficulties"],
)
def test_an_unreadable_snapshot_leaves_every_benchmark_without_groups_or_a_link(
    snapshot_path, caplog, content
):
    if content is None:
        snapshot_path.unlink()
    else:
        snapshot_path.write_text(content, encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger=evxl_snapshot.__name__):
        assert join_scenario_groups("KovaaKsTwoLevel", 5) is None
        assert evxl_benchmark_url("KovaaKsTwoLevel", None) is None

    # One warning for the whole file, and it names both losses.
    (record,) = caplog.records
    assert "no Evxl link and no categories" in record.message
