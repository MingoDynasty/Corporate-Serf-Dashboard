import json
from datetime import UTC, datetime

import pytest

from source.kovaaks import data_service
from source.kovaaks import scenario_notes_service as notes
from source.kovaaks.data_models import Scenario
from source.utilities import store_schema
from source.utilities.store_schema import StoreState

SCENARIO = "SmoothBot Perfected"


@pytest.fixture
def notes_dir(monkeypatch, tmp_path):
    """Point the store at a folder that doesn't exist yet."""
    directory = tmp_path / "data" / "scenario_notes"
    monkeypatch.setattr(notes, "SCENARIO_NOTES_DIR", directory)
    return directory


def _write_note(scenario, payload):
    """Write a stamped note file holding the given payload at its path."""
    return _write_raw_note(scenario, json.dumps({"schema_version": 1, **payload}))


def _write_raw_note(scenario, text):
    """Write whatever text the test wants at the scenario's note path."""
    path = notes.scenario_note_path(scenario)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _valid_payload(**overrides):
    return {
        "scenario": SCENARIO,
        "text": "try to use more wrist/fingers here",
        "edited_at": "2026-10-18T20:25:00Z",
        **overrides,
    }


def _message(predicate):
    return (
        f"The scenario note file {predicate} File: {notes.scenario_note_path(SCENARIO)}"
    )


@pytest.mark.parametrize(
    ("scenario", "file_name"),
    [
        ("SmoothBot Perfected", "SmoothBot_Perfected-98173bc5.json"),
        (
            "psalmTS angelic click 30% Larger",
            "psalmTS_angelic_click_30__Larger-e7ca36d5.json",
        ),
        (
            "psalmTS angelic click 30% larger",
            "psalmTS_angelic_click_30__larger-0f416bac.json",
        ),
        ("Pasu Voltaic Silver", "Pasu_Voltaic_Silver-424d7edd.json"),
    ],
)
def test_a_note_file_is_named_from_the_scenario_name(notes_dir, scenario, file_name):
    assert notes.scenario_note_path(scenario) == notes_dir / file_name


def test_names_that_differ_only_by_case_get_a_file_each(notes_dir):
    """Windows file names ignore case, so the digest is what keeps them apart."""
    upper = "psalmTS angelic click 30% Larger"
    lower = "psalmTS angelic click 30% larger"

    notes.save_scenario_note(upper, "upper note")
    notes.save_scenario_note(lower, "lower note")

    assert len(list(notes_dir.iterdir())) == 2
    assert notes.read_scenario_note(upper).value.text == "upper note"
    assert notes.read_scenario_note(lower).value.text == "lower note"


def test_a_trailing_space_in_the_stats_file_keys_the_stripped_name(notes_dir, tmp_path):
    """The run import, a playlist's name and the store agree on one file."""
    stats_name = "Pasu Voltaic Silver - Challenge - 2026.10.18-20.25.00 Stats.csv"
    stats_file = tmp_path / stats_name
    stats_file.write_text(
        "\n".join(
            [
                "Weapon,Shots,Hits,Damage Done,Damage Possible,,Sens Scale,"
                "Horiz Sens,Vert Sens,FOV,Hide Gun,Crosshair,Crosshair Scale,"
                "Crosshair Color,ADS Sens,ADS Zoom Scale,Avg Target Scale,"
                "Avg Time Dilation",
                "Rifle,100,50,75,100,,cm/360,40,40,0,0,0,0,0,0,0,0,0",
                "Score:,123.45",
                "Sens Scale:,cm/360",
                "Horiz Sens:,40",
                "Scenario:,Pasu Voltaic Silver ",
                "",
            ]
        ),
        encoding="utf-8",
    )

    run = data_service.extract_data_from_file(str(stats_file))
    playlist_scenario = Scenario(name="Pasu Voltaic Silver ")

    assert run is not None
    assert run.scenario == playlist_scenario.name == "Pasu Voltaic Silver"
    expected = notes_dir / "Pasu_Voltaic_Silver-424d7edd.json"
    assert notes.scenario_note_path(run.scenario) == expected
    assert notes.scenario_note_path(playlist_scenario.name) == expected

    notes.save_scenario_note(run.scenario, "from the run")

    assert notes.read_scenario_note(playlist_scenario.name).value.text == (
        "from the run"
    )


def test_no_file_reads_as_no_note_without_making_the_folder(notes_dir):
    document = notes.read_scenario_note(SCENARIO)

    assert document.state is StoreState.MISSING
    assert document.value is None
    assert document.message == ""
    assert not notes_dir.exists()


def test_a_valid_file_reads_as_its_note_and_edit_time(notes_dir):
    _write_note(SCENARIO, _valid_payload())

    document = notes.read_scenario_note(SCENARIO)

    assert document.state is StoreState.SUPPORTED
    assert document.value == notes.ScenarioNote(
        text="try to use more wrist/fingers here",
        edited_at=datetime(2026, 10, 18, 20, 25, tzinfo=UTC),
    )
    assert document.message == ""


def test_a_note_at_the_limit_reads(notes_dir):
    text = "x" * notes.MAX_NOTE_CHARACTERS
    _write_note(SCENARIO, _valid_payload(text=text))

    assert notes.read_scenario_note(SCENARIO).value.text == text


def test_an_offset_of_zero_reads_as_utc(notes_dir):
    _write_note(SCENARIO, _valid_payload(edited_at="2026-10-18T20:25:00+00:00"))

    edited_at = notes.read_scenario_note(SCENARIO).value.edited_at

    assert edited_at == datetime(2026, 10, 18, 20, 25, tzinfo=UTC)
    assert edited_at.tzinfo is UTC


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("not json", "The scenario note file isn't valid JSON. File: {path}"),
        ("[]", "The scenario note file must hold a JSON object. File: {path}"),
        (
            json.dumps(_valid_payload()),
            'The scenario note file has no "schema_version" line. Add '
            '"schema_version": 1 to it, or delete the file to start over. '
            "File: {path}",
        ),
        (
            json.dumps({"schema_version": "1", **_valid_payload()}),
            'The scenario note file\'s "schema_version" is "1". It must be the '
            "whole number 1. File: {path}",
        ),
        (
            json.dumps({"schema_version": 0, **_valid_payload()}),
            'The scenario note file\'s "schema_version" is 0. It must be the '
            "whole number 1. File: {path}",
        ),
        (
            json.dumps({"schema_version": True, **_valid_payload()}),
            'The scenario note file\'s "schema_version" is true. It must be the '
            "whole number 1. File: {path}",
        ),
    ],
)
def test_a_file_the_machine_cannot_classify_is_in_the_error_state(
    notes_dir, text, message
):
    path = _write_raw_note(SCENARIO, text)

    document = notes.read_scenario_note(SCENARIO)

    assert document.state is StoreState.ERROR
    assert document.value is None
    assert document.message == message.format(path=path)


@pytest.mark.parametrize(
    ("payload", "predicate"),
    [
        (_valid_payload(note="extra"), 'has an unknown key "note".'),
        (
            {
                key: value
                for key, value in _valid_payload().items()
                if key != "scenario"
            },
            'is missing "scenario".',
        ),
        (
            {key: value for key, value in _valid_payload().items() if key != "text"},
            'is missing "text".',
        ),
        (
            {
                key: value
                for key, value in _valid_payload().items()
                if key != "edited_at"
            },
            'is missing "edited_at".',
        ),
        (_valid_payload(scenario=None), 'must hold "scenario" as text.'),
        (_valid_payload(text=["a", "list"]), 'must hold "text" as text.'),
        (_valid_payload(scenario="Smoothbot Perfected"), "is for another scenario."),
        (_valid_payload(scenario="SmoothBot Perfected "), "is for another scenario."),
        (_valid_payload(text=""), "holds an empty note."),
        (_valid_payload(text=" \n\t　"), "holds an empty note."),
        (
            _valid_payload(text="x" * (notes.MAX_NOTE_CHARACTERS + 1)),
            "holds more than 2,000 characters.",
        ),
        (_valid_payload(edited_at=1760819100), 'must hold "edited_at" as a UTC time.'),
        (_valid_payload(edited_at="yesterday"), 'must hold "edited_at" as a UTC time.'),
        (
            _valid_payload(edited_at="2026-10-18T20:25:00"),
            'must hold "edited_at" as a UTC time.',
        ),
        (
            _valid_payload(edited_at="2026-10-18T20:25:00+02:00"),
            'must hold "edited_at" as a UTC time.',
        ),
    ],
)
def test_a_file_breaking_a_v1_rule_is_in_the_error_state(notes_dir, payload, predicate):
    _write_note(SCENARIO, payload)

    document = notes.read_scenario_note(SCENARIO)

    assert document.state is StoreState.ERROR
    assert document.value is None
    assert document.message == _message(predicate)


def test_a_file_from_a_newer_build_is_in_the_future_state(notes_dir):
    path = _write_raw_note(
        SCENARIO, json.dumps({"schema_version": 2, "scenario": SCENARIO})
    )

    document = notes.read_scenario_note(SCENARIO)

    assert document.state is StoreState.FUTURE
    assert document.value is None
    assert document.message == (
        "The scenario note file was written by a newer version of this app "
        f"(schema_version 2). It is intact. Update the app to use it. File: {path}"
    )


def test_reading_a_broken_file_never_touches_it(notes_dir):
    path = _write_raw_note(SCENARIO, "not json")

    notes.read_scenario_note(SCENARIO)

    assert path.read_text(encoding="utf-8") == "not json"
    assert [entry.name for entry in notes_dir.iterdir()] == [path.name]


def test_a_save_makes_the_folder_and_writes_a_stamped_note(notes_dir):
    note = notes.save_scenario_note(SCENARIO, "line one\nline two")

    path = notes_dir / "SmoothBot_Perfected-98173bc5.json"
    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)
    assert list(payload) == ["schema_version", "scenario", "text", "edited_at"]
    assert payload["schema_version"] == 1
    assert payload["scenario"] == SCENARIO
    assert payload["text"] == "line one\nline two"
    assert raw.endswith("\n")
    assert note == notes.ScenarioNote(
        text="line one\nline two",
        edited_at=datetime.fromisoformat(payload["edited_at"]),
    )
    assert notes.read_scenario_note(SCENARIO).value == note
    assert [entry.name for entry in notes_dir.iterdir()] == [path.name]


def test_a_save_stamps_the_edit_time_in_utc(notes_dir):
    before = datetime.now(UTC).replace(microsecond=0)

    notes.save_scenario_note(SCENARIO, "a note")

    after = datetime.now(UTC)
    path = notes.scenario_note_path(SCENARIO)
    edited_at = json.loads(path.read_text(encoding="utf-8"))["edited_at"]
    assert edited_at.endswith("Z")
    assert len(edited_at) == len("2026-10-18T20:25:00Z")
    assert before <= datetime.fromisoformat(edited_at) <= after


def test_a_save_of_changed_text_replaces_the_note_and_its_edit_time(notes_dir):
    _write_note(SCENARIO, _valid_payload(text="old", edited_at="2026-01-01T00:00:00Z"))

    note = notes.save_scenario_note(SCENARIO, "new")

    assert note.text == "new"
    assert note.edited_at > datetime(2026, 1, 1, tzinfo=UTC)
    assert notes.read_scenario_note(SCENARIO).value == note
    assert not list(notes_dir.glob("*.bak"))


def test_a_save_of_the_same_text_writes_nothing(notes_dir):
    path = _write_note(
        SCENARIO, _valid_payload(text="same", edited_at="2026-01-01T00:00:00Z")
    )
    raw = path.read_bytes()

    note = notes.save_scenario_note(SCENARIO, "same")

    assert note == notes.ScenarioNote(
        text="same", edited_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    assert path.read_bytes() == raw


def test_a_save_keeps_the_text_exactly_as_given(notes_dir):
    text = "  leading and trailing  \n\n"

    notes.save_scenario_note(SCENARIO, text)

    assert notes.read_scenario_note(SCENARIO).value.text == text


def test_a_lone_surrogate_round_trips(notes_dir):
    text = "cut mid-pair \ud83d"

    notes.save_scenario_note(SCENARIO, text)

    assert notes.read_scenario_note(SCENARIO).value.text == text


def test_a_save_over_the_limit_writes_nothing(notes_dir):
    with pytest.raises(store_schema.SchemaPayloadError):
        notes.save_scenario_note(SCENARIO, "x" * (notes.MAX_NOTE_CHARACTERS + 1))

    assert not notes_dir.exists()


@pytest.mark.parametrize("text", ["", "   ", " \n\t "])
def test_a_save_of_empty_text_deletes_the_note(notes_dir, text):
    notes.save_scenario_note(SCENARIO, "a note")

    assert notes.save_scenario_note(SCENARIO, text) is None

    assert notes.read_scenario_note(SCENARIO).state is StoreState.MISSING
    assert list(notes_dir.iterdir()) == []


def test_a_save_of_empty_text_with_no_note_does_nothing(notes_dir):
    assert notes.save_scenario_note(SCENARIO, "") is None

    assert not notes_dir.exists()


def test_a_save_over_a_broken_file_copies_it_aside_first(notes_dir):
    path = _write_raw_note(SCENARIO, "not json")

    notes.save_scenario_note(SCENARIO, "a fresh note")

    backup = path.with_name(f"{path.name}.corrupt-1.bak")
    assert backup.read_text(encoding="utf-8") == "not json"
    assert notes.read_scenario_note(SCENARIO).value.text == "a fresh note"


def test_a_save_of_empty_text_over_a_broken_file_copies_it_aside_and_deletes_it(
    notes_dir,
):
    path = _write_raw_note(SCENARIO, "not json")

    assert notes.save_scenario_note(SCENARIO, "") is None

    backup = path.with_name(f"{path.name}.corrupt-1.bak")
    assert backup.read_text(encoding="utf-8") == "not json"
    assert not path.exists()
    assert [entry.name for entry in notes_dir.iterdir()] == [backup.name]


def test_another_scenarios_note_is_copied_aside_before_a_save_replaces_it(
    notes_dir,
):
    """A file at this path holding another name's note is never lost.

    Two names collide only when they differ where the prefix folds characters
    and share the digest, so the file is written by hand here.
    """
    other = _valid_payload(scenario="SmoothBot_Perfected", text="the other note")
    path = _write_note(SCENARIO, other)
    raw = path.read_text(encoding="utf-8")

    assert notes.read_scenario_note(SCENARIO).message == _message(
        "is for another scenario."
    )

    notes.save_scenario_note(SCENARIO, "this scenario's note")

    backup = path.with_name(f"{path.name}.corrupt-1.bak")
    assert backup.read_text(encoding="utf-8") == raw
    assert notes.read_scenario_note(SCENARIO).value.text == "this scenario's note"


@pytest.mark.parametrize("text", ["a newer note", ""])
def test_a_save_and_a_delete_are_refused_by_a_file_from_a_newer_build(notes_dir, text):
    future = json.dumps({"schema_version": 2, "scenario": SCENARIO, "body": "x"})
    path = _write_raw_note(SCENARIO, future)

    with pytest.raises(store_schema.UnsupportedSchemaError) as refusal:
        notes.save_scenario_note(SCENARIO, text)

    assert str(refusal.value) == notes.read_scenario_note(SCENARIO).message
    assert path.read_text(encoding="utf-8") == future
    assert [entry.name for entry in notes_dir.iterdir()] == [path.name]


def test_a_backup_that_cannot_be_made_refuses_the_save(notes_dir, monkeypatch):
    path = _write_raw_note(SCENARIO, "not json")

    def refuse(_path):
        msg = "disk full"
        raise OSError(msg)

    monkeypatch.setattr(notes, "back_up_unusable_store", refuse)

    with pytest.raises(OSError, match="disk full"):
        notes.save_scenario_note(SCENARIO, "a fresh note")
    with pytest.raises(OSError, match="disk full"):
        notes.save_scenario_note(SCENARIO, "")

    assert path.read_text(encoding="utf-8") == "not json"
    assert [entry.name for entry in notes_dir.iterdir()] == [path.name]
