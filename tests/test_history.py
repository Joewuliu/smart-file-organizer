import json

from organizer.history import (
    HistoryMove,
    HistoryOperation,
    build_undo_plan,
    clear_history,
    load_last_operation,
    record_operation,
    save_remaining_operation,
)
from organizer.mover import MoveResult
from organizer.planner import PlannedMove


def _history_path(tmp_path):
    return tmp_path / "history.json"


def test_record_operation_creates_history_file(tmp_path):
    path = _history_path(tmp_path)
    move = PlannedMove(tmp_path / "report.pdf", tmp_path / "Documents" / "report.pdf", "Documents")

    record_operation([MoveResult(move, True)], tmp_path, path)

    assert path.exists()


def test_record_operation_only_includes_successful_moves(tmp_path):
    path = _history_path(tmp_path)
    good = PlannedMove(tmp_path / "a.pdf", tmp_path / "Documents" / "a.pdf", "Documents")
    bad = PlannedMove(tmp_path / "b.pdf", tmp_path / "Documents" / "b.pdf", "Documents")

    record_operation([MoveResult(good, True), MoveResult(bad, False, "boom")], tmp_path, path)
    operation = load_last_operation(path)

    assert operation.moves == [HistoryMove(source=good.source, destination=good.destination)]


def test_record_operation_with_no_successes_leaves_existing_history_untouched(tmp_path):
    path = _history_path(tmp_path)
    existing = PlannedMove(tmp_path / "old.pdf", tmp_path / "Documents" / "old.pdf", "Documents")
    record_operation([MoveResult(existing, True)], tmp_path, path)
    before = path.read_text()

    failing = PlannedMove(tmp_path / "new.pdf", tmp_path / "Documents" / "new.pdf", "Documents")
    record_operation([MoveResult(failing, False, "boom")], tmp_path, path)

    assert path.read_text() == before


def test_load_last_operation_returns_none_when_missing(tmp_path):
    assert load_last_operation(_history_path(tmp_path)) is None


def test_load_last_operation_preserves_exact_source_and_destination_paths(tmp_path):
    path = _history_path(tmp_path)
    source = tmp_path / "report.pdf"
    destination = tmp_path / "Documents" / "report.pdf"
    move = PlannedMove(source, destination, "Documents")
    record_operation([MoveResult(move, True)], tmp_path, path)

    operation = load_last_operation(path)

    assert operation.moves == [HistoryMove(source=source, destination=destination)]


def test_build_undo_plan_reverses_source_and_destination(tmp_path):
    source = tmp_path / "report.pdf"
    destination = tmp_path / "Documents" / "report.pdf"
    operation = HistoryOperation(
        timestamp="2026-08-18T00:00:00+00:00",
        root=tmp_path,
        moves=[HistoryMove(source=source, destination=destination)],
    )

    [undo_move] = build_undo_plan(operation)

    assert undo_move.source == destination
    assert undo_move.destination == source


def test_save_remaining_operation_overwrites_history(tmp_path):
    path = _history_path(tmp_path)
    move = PlannedMove(tmp_path / "a.pdf", tmp_path / "Documents" / "a.pdf", "Documents")
    record_operation([MoveResult(move, True)], tmp_path, path)

    remaining = [
        HistoryMove(source=tmp_path / "b.pdf", destination=tmp_path / "Documents" / "b.pdf")
    ]
    save_remaining_operation(remaining, tmp_path, path)

    assert load_last_operation(path).moves == remaining


def test_clear_history_removes_file(tmp_path):
    path = _history_path(tmp_path)
    move = PlannedMove(tmp_path / "a.pdf", tmp_path / "Documents" / "a.pdf", "Documents")
    record_operation([MoveResult(move, True)], tmp_path, path)

    clear_history(path)

    assert not path.exists()


def test_clear_history_is_safe_when_no_file_exists(tmp_path):
    clear_history(_history_path(tmp_path))


def test_history_file_stores_no_extra_data(tmp_path):
    path = _history_path(tmp_path)
    move = PlannedMove(tmp_path / "a.pdf", tmp_path / "Documents" / "a.pdf", "Documents")

    record_operation([MoveResult(move, True)], tmp_path, path)

    data = json.loads(path.read_text())
    assert set(data.keys()) == {"timestamp", "root", "moves"}
    assert set(data["moves"][0].keys()) == {"source", "destination"}


def test_functions_do_not_touch_the_real_default_history_path(tmp_path, monkeypatch):
    # Belt-and-suspenders: even if DEFAULT_HISTORY_PATH were somehow
    # the real home directory, passing an explicit path must always
    # win and the default must never be touched.
    poisoned_default = tmp_path / "should_never_be_written" / "history.json"
    monkeypatch.setattr("organizer.history.DEFAULT_HISTORY_PATH", poisoned_default)

    explicit_path = tmp_path / "actual" / "history.json"
    move = PlannedMove(tmp_path / "a.pdf", tmp_path / "Documents" / "a.pdf", "Documents")
    record_operation([MoveResult(move, True)], tmp_path, explicit_path)

    assert explicit_path.exists()
    assert not poisoned_default.exists()
