import json
from pathlib import Path

import pytest

from organizer.mover import MoveResult
from organizer.planner import PlannedMove
from organizer.state import StateError, managed_directories, record_managed_destinations


def _state_path(tmp_path):
    return tmp_path / "state.json"


def _move(source, destination):
    return PlannedMove(source=source, destination=destination, category="")


def test_record_managed_destinations_creates_state_file(tmp_path):
    path = _state_path(tmp_path)
    move = _move(tmp_path / "report.pdf", tmp_path / "Documents" / "report.pdf")

    record_managed_destinations([MoveResult(move, True)], tmp_path, path)

    assert path.exists()


def test_managed_directories_returns_empty_set_when_no_state_file(tmp_path):
    assert managed_directories(tmp_path, _state_path(tmp_path)) == set()


def test_managed_directories_returns_empty_set_when_root_has_no_entry(tmp_path):
    path = _state_path(tmp_path)
    other_root = tmp_path / "other"
    other_root.mkdir()
    move = _move(other_root / "report.pdf", other_root / "Documents" / "report.pdf")
    record_managed_destinations([MoveResult(move, True)], other_root, path)

    assert managed_directories(tmp_path, path) == set()


def test_record_managed_destinations_only_includes_successful_moves(tmp_path):
    path = _state_path(tmp_path)
    good = _move(tmp_path / "a.pdf", tmp_path / "Documents" / "a.pdf")
    bad = _move(tmp_path / "b.jpg", tmp_path / "Images" / "b.jpg")

    record_managed_destinations(
        [MoveResult(good, True), MoveResult(bad, False, "boom")], tmp_path, path
    )

    assert managed_directories(tmp_path, path) == {Path("Documents")}


def test_record_managed_destinations_with_no_successes_leaves_state_untouched(tmp_path):
    path = _state_path(tmp_path)
    ok = _move(tmp_path / "a.pdf", tmp_path / "Documents" / "a.pdf")
    record_managed_destinations([MoveResult(ok, True)], tmp_path, path)
    before = path.read_text()

    failing = _move(tmp_path / "b.pdf", tmp_path / "Images" / "b.pdf")
    record_managed_destinations([MoveResult(failing, False, "boom")], tmp_path, path)

    assert path.read_text() == before


def test_record_managed_destinations_merges_with_existing_entries(tmp_path):
    path = _state_path(tmp_path)
    first = _move(tmp_path / "a.pdf", tmp_path / "Documents" / "a.pdf")
    record_managed_destinations([MoveResult(first, True)], tmp_path, path)

    second = _move(tmp_path / "b.jpg", tmp_path / "Images" / "b.jpg")
    record_managed_destinations([MoveResult(second, True)], tmp_path, path)

    assert managed_directories(tmp_path, path) == {Path("Documents"), Path("Images")}


def test_record_managed_destinations_tracks_date_shaped_paths(tmp_path):
    path = _state_path(tmp_path)
    move = _move(tmp_path / "report.pdf", tmp_path / "2026" / "08-August" / "report.pdf")

    record_managed_destinations([MoveResult(move, True)], tmp_path, path)

    assert managed_directories(tmp_path, path) == {Path("2026") / "08-August"}


def test_record_managed_destinations_tracks_category_date_shaped_paths(tmp_path):
    path = _state_path(tmp_path)
    move = _move(
        tmp_path / "statement.pdf",
        tmp_path / "Finance" / "2026" / "08-August" / "statement.pdf",
    )

    record_managed_destinations([MoveResult(move, True)], tmp_path, path)

    assert managed_directories(tmp_path, path) == {Path("Finance") / "2026" / "08-August"}


def test_state_is_separate_per_root(tmp_path):
    path = _state_path(tmp_path)
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()

    move_a = _move(root_a / "x.pdf", root_a / "Documents" / "x.pdf")
    move_b = _move(root_b / "y.jpg", root_b / "Images" / "y.jpg")
    record_managed_destinations([MoveResult(move_a, True)], root_a, path)
    record_managed_destinations([MoveResult(move_b, True)], root_b, path)

    assert managed_directories(root_a, path) == {Path("Documents")}
    assert managed_directories(root_b, path) == {Path("Images")}


def test_malformed_json_raises_state_error(tmp_path):
    path = _state_path(tmp_path)
    path.write_text("this is not [ valid json")

    with pytest.raises(StateError):
        managed_directories(tmp_path, path)


def test_non_dict_top_level_raises_state_error(tmp_path):
    path = _state_path(tmp_path)
    path.write_text(json.dumps(["not", "a", "dict"]))

    with pytest.raises(StateError):
        managed_directories(tmp_path, path)


def test_missing_roots_key_raises_state_error(tmp_path):
    path = _state_path(tmp_path)
    path.write_text(json.dumps({"something_else": {}}))

    with pytest.raises(StateError):
        managed_directories(tmp_path, path)


def test_malformed_root_entry_raises_state_error(tmp_path):
    path = _state_path(tmp_path)
    key = str(tmp_path.resolve())
    path.write_text(json.dumps({"roots": {key: {"managed_directories": "not-a-list"}}}))

    with pytest.raises(StateError):
        managed_directories(tmp_path, path)


def test_write_leaves_no_temp_file_behind(tmp_path):
    path = _state_path(tmp_path)
    move = _move(tmp_path / "a.pdf", tmp_path / "Documents" / "a.pdf")

    record_managed_destinations([MoveResult(move, True)], tmp_path, path)

    assert not path.with_name(path.name + ".tmp").exists()
    assert path.exists()


def test_state_file_stores_no_extra_data(tmp_path):
    path = _state_path(tmp_path)
    move = _move(tmp_path / "a.pdf", tmp_path / "Documents" / "a.pdf")

    record_managed_destinations([MoveResult(move, True)], tmp_path, path)

    data = json.loads(path.read_text())
    assert set(data.keys()) == {"roots"}
    key = str(tmp_path.resolve())
    entry = data["roots"][key]
    assert set(entry.keys()) == {"managed_directories"}
    assert entry["managed_directories"] == ["Documents"]
