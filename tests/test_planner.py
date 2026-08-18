import pytest

from organizer.planner import PlannedMove, plan_moves


def test_pdf_plans_to_documents(tmp_path):
    file = tmp_path / "report.pdf"
    file.write_text("data")

    [move] = plan_moves([file], tmp_path)

    assert move.source == file
    assert move.category == "Documents"
    assert move.destination == tmp_path / "Documents" / "report.pdf"


def test_filename_rule_flows_through_to_planner(tmp_path):
    # planner.py performs no filename/extension logic itself; it only
    # calls classify_file(). This proves the classifier's filename-rule
    # precedence (added for Milestone 6) is picked up automatically.
    file = tmp_path / "bank_statement.pdf"
    file.write_text("data")

    [move] = plan_moves([file], tmp_path)

    assert move.category == "Finance"
    assert move.destination == tmp_path / "Finance" / "bank_statement.pdf"


def test_jpg_plans_to_images(tmp_path):
    file = tmp_path / "photo.jpg"
    file.write_text("data")

    [move] = plan_moves([file], tmp_path)

    assert move.category == "Images"
    assert move.destination == tmp_path / "Images" / "photo.jpg"


def test_unknown_extension_plans_to_other(tmp_path):
    file = tmp_path / "mystery.xyz"
    file.write_text("data")

    [move] = plan_moves([file], tmp_path)

    assert move.category == "Other"
    assert move.destination == tmp_path / "Other" / "mystery.xyz"


def test_several_files_across_categories(tmp_path):
    pdf = tmp_path / "report.pdf"
    jpg = tmp_path / "photo.jpg"
    zip_file = tmp_path / "backup.zip"
    for f in (pdf, jpg, zip_file):
        f.write_text("data")

    plan = plan_moves([pdf, jpg, zip_file], tmp_path)

    assert [m.source for m in plan] == [pdf, jpg, zip_file]
    assert plan[0].destination == tmp_path / "Documents" / "report.pdf"
    assert plan[1].destination == tmp_path / "Images" / "photo.jpg"
    assert plan[2].destination == tmp_path / "Archives" / "backup.zip"


def test_uppercase_extension(tmp_path):
    file = tmp_path / "PHOTO.JPG"
    file.write_text("data")

    [move] = plan_moves([file], tmp_path)

    assert move.category == "Images"
    assert move.destination == tmp_path / "Images" / "PHOTO.JPG"


def test_existing_destination_collision(tmp_path):
    existing_dir = tmp_path / "Documents"
    existing_dir.mkdir()
    (existing_dir / "report.pdf").write_text("existing")

    source = tmp_path / "report.pdf"
    source.write_text("new")

    [move] = plan_moves([source], tmp_path)

    assert move.destination == tmp_path / "Documents" / "report (1).pdf"


def test_multiple_numbered_collisions(tmp_path):
    existing_dir = tmp_path / "Documents"
    existing_dir.mkdir()
    (existing_dir / "report.pdf").write_text("existing")
    (existing_dir / "report (1).pdf").write_text("existing")
    (existing_dir / "report (2).pdf").write_text("existing")

    source = tmp_path / "report.pdf"
    source.write_text("new")

    [move] = plan_moves([source], tmp_path)

    assert move.destination == tmp_path / "Documents" / "report (3).pdf"


def test_collision_with_destination_reserved_in_same_plan(tmp_path):
    first = tmp_path / "report.pdf"
    first.write_text("first")

    subdir = tmp_path / "sub"
    subdir.mkdir()
    second = subdir / "report.pdf"
    second.write_text("second")

    # Both files classify to Documents/report.pdf; only one input dir is
    # scanned in practice, but plan_moves itself must still de-duplicate
    # two sources that would otherwise collide on the same destination.
    plan = plan_moves([first, second], tmp_path)

    assert plan[0].destination == tmp_path / "Documents" / "report.pdf"
    assert plan[1].destination == tmp_path / "Documents" / "report (1).pdf"


def test_existing_destination_file_remains_unchanged(tmp_path):
    existing_dir = tmp_path / "Documents"
    existing_dir.mkdir()
    existing_file = existing_dir / "report.pdf"
    existing_file.write_text("original content")

    source = tmp_path / "report.pdf"
    source.write_text("new content")

    plan_moves([source], tmp_path)

    assert existing_file.read_text() == "original content"


def test_category_directories_are_not_created(tmp_path):
    source = tmp_path / "report.pdf"
    source.write_text("data")

    plan_moves([source], tmp_path)

    assert not (tmp_path / "Documents").exists()


def test_source_files_remain_untouched(tmp_path):
    source = tmp_path / "report.pdf"
    source.write_text("data")

    plan_moves([source], tmp_path)

    assert source.exists()
    assert source.read_text() == "data"


def test_category_path_exists_as_file_raises_error(tmp_path):
    (tmp_path / "Documents").write_text("not a directory")

    source = tmp_path / "report.pdf"
    source.write_text("data")

    with pytest.raises(NotADirectoryError):
        plan_moves([source], tmp_path)


def test_empty_file_list_returns_empty_plan(tmp_path):
    assert plan_moves([], tmp_path) == []


def test_planned_move_is_simple_dataclass(tmp_path):
    source = tmp_path / "report.pdf"
    source.write_text("data")

    [move] = plan_moves([source], tmp_path)

    assert isinstance(move, PlannedMove)
    assert move.source == source
    assert move.category == "Documents"
