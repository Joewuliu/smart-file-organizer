from organizer.mover import execute_moves
from organizer.planner import PlannedMove


def test_successfully_moves_one_file(tmp_path):
    source = tmp_path / "report.pdf"
    source.write_text("data")
    destination = tmp_path / "Documents" / "report.pdf"
    move = PlannedMove(source=source, destination=destination, category="Documents")

    [result] = execute_moves([move])

    assert result.success is True
    assert result.error is None
    assert destination.exists()


def test_source_disappears_from_original_location_after_move(tmp_path):
    source = tmp_path / "report.pdf"
    source.write_text("data")
    destination = tmp_path / "Documents" / "report.pdf"
    move = PlannedMove(source=source, destination=destination, category="Documents")

    execute_moves([move])

    assert not source.exists()


def test_destination_contains_exact_source_content(tmp_path):
    source = tmp_path / "report.pdf"
    source.write_text("exact original content")
    destination = tmp_path / "Documents" / "report.pdf"
    move = PlannedMove(source=source, destination=destination, category="Documents")

    execute_moves([move])

    assert destination.read_text() == "exact original content"


def test_destination_category_directory_is_created(tmp_path):
    source = tmp_path / "report.pdf"
    source.write_text("data")
    destination = tmp_path / "Documents" / "report.pdf"
    move = PlannedMove(source=source, destination=destination, category="Documents")

    assert not (tmp_path / "Documents").exists()

    execute_moves([move])

    assert (tmp_path / "Documents").is_dir()


def test_multiple_files_move_successfully(tmp_path):
    pdf = tmp_path / "report.pdf"
    jpg = tmp_path / "photo.jpg"
    pdf.write_text("pdf data")
    jpg.write_text("jpg data")
    moves = [
        PlannedMove(pdf, tmp_path / "Documents" / "report.pdf", "Documents"),
        PlannedMove(jpg, tmp_path / "Images" / "photo.jpg", "Images"),
    ]

    results = execute_moves(moves)

    assert all(r.success for r in results)
    assert (tmp_path / "Documents" / "report.pdf").exists()
    assert (tmp_path / "Images" / "photo.jpg").exists()


def test_result_ordering_matches_plan_ordering(tmp_path):
    files = [tmp_path / f"file{i}.txt" for i in range(3)]
    for f in files:
        f.write_text("data")
    moves = [PlannedMove(f, tmp_path / "Documents" / f.name, "Documents") for f in files]

    results = execute_moves(moves)

    assert [r.move.source for r in results] == files


def test_destination_unexpectedly_exists_at_execution_time(tmp_path):
    source = tmp_path / "report.pdf"
    source.write_text("new content")
    dest_dir = tmp_path / "Documents"
    dest_dir.mkdir()
    existing = dest_dir / "report.pdf"
    existing.write_text("original content")
    move = PlannedMove(source, existing, "Documents")

    [result] = execute_moves([move])

    assert result.success is False
    assert result.error is not None
    assert existing.read_text() == "original content"
    assert source.exists()
    assert source.read_text() == "new content"


def test_source_disappears_between_planning_and_execution(tmp_path):
    source = tmp_path / "report.pdf"
    # Never created on disk - simulates it vanishing after planning.
    destination = tmp_path / "Documents" / "report.pdf"
    move = PlannedMove(source, destination, "Documents")

    [result] = execute_moves([move])

    assert result.success is False
    assert result.error is not None
    assert not destination.exists()


def test_batch_continues_after_source_disappears(tmp_path):
    missing_source = tmp_path / "missing.pdf"
    present_source = tmp_path / "present.pdf"
    present_source.write_text("data")
    moves = [
        PlannedMove(missing_source, tmp_path / "Documents" / "missing.pdf", "Documents"),
        PlannedMove(present_source, tmp_path / "Documents" / "present.pdf", "Documents"),
    ]

    results = execute_moves(moves)

    assert results[0].success is False
    assert results[1].success is True
    assert (tmp_path / "Documents" / "present.pdf").exists()


def test_destination_parent_is_a_file(tmp_path):
    (tmp_path / "Documents").write_text("i am a file, not a directory")
    source = tmp_path / "report.pdf"
    source.write_text("data")
    destination = tmp_path / "Documents" / "report.pdf"
    move = PlannedMove(source, destination, "Documents")

    [result] = execute_moves([move])

    assert result.success is False
    assert result.error is not None
    assert (tmp_path / "Documents").read_text() == "i am a file, not a directory"
    assert source.exists()


def test_one_failure_does_not_block_later_success(tmp_path):
    dest_dir = tmp_path / "Documents"
    dest_dir.mkdir()
    (dest_dir / "report.pdf").write_text("existing")

    failing_source = tmp_path / "report.pdf"
    failing_source.write_text("blocked")
    succeeding_source = tmp_path / "notes.txt"
    succeeding_source.write_text("ok")

    moves = [
        PlannedMove(failing_source, dest_dir / "report.pdf", "Documents"),
        PlannedMove(succeeding_source, dest_dir / "notes.txt", "Documents"),
    ]

    results = execute_moves(moves)

    assert results[0].success is False
    assert results[1].success is True
    assert (dest_dir / "notes.txt").exists()


def test_never_overwrites_existing_destination_content(tmp_path):
    dest_dir = tmp_path / "Documents"
    dest_dir.mkdir()
    existing = dest_dir / "report.pdf"
    existing.write_text("must not change")

    source = tmp_path / "report.pdf"
    source.write_text("attempted overwrite")
    move = PlannedMove(source, existing, "Documents")

    execute_moves([move])

    assert existing.read_text() == "must not change"


def test_empty_plan_returns_empty_results_and_changes_nothing(tmp_path):
    before = sorted(tmp_path.iterdir())

    results = execute_moves([])

    assert results == []
    assert sorted(tmp_path.iterdir()) == before


def test_execute_moves_uses_planned_destination_without_reclassifying(tmp_path):
    # report.pdf would normally classify as Documents, but the plan
    # deliberately points it somewhere else; the mover must obey the
    # plan rather than re-deriving the destination itself.
    source = tmp_path / "report.pdf"
    source.write_text("data")
    destination = tmp_path / "CustomCategory" / "report.pdf"
    move = PlannedMove(source, destination, category="CustomCategory")

    [result] = execute_moves([move])

    assert result.success is True
    assert destination.exists()
    assert not (tmp_path / "Documents").exists()
