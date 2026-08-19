import os
from datetime import datetime

import pytest

from organizer.classifier import ClassificationRules
from organizer.planner import (
    PlannedMove,
    plan_moves,
    plan_moves_by_category_and_date,
    plan_moves_by_date,
)


def _set_mtime(path, year, month, day, hour=12):
    timestamp = datetime(year, month, day, hour).timestamp()
    os.utime(path, (timestamp, timestamp))


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


def test_custom_rules_flow_through_planner(tmp_path):
    file = tmp_path / "march_paystub.pdf"
    file.write_text("data")
    custom_rules = ClassificationRules(
        filename_rules=(("*paystub*", "Payroll"),),
        extensions={},
    )

    [move] = plan_moves([file], tmp_path, custom_rules)

    assert move.category == "Payroll"
    assert move.destination == tmp_path / "Payroll" / "march_paystub.pdf"


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


def test_plan_moves_by_date_uses_year_month_destination(tmp_path):
    source = tmp_path / "report.pdf"
    source.write_text("data")
    _set_mtime(source, 2026, 8, 18)

    [move] = plan_moves_by_date([source], tmp_path)

    assert move.category == "2026/08-August"
    assert move.destination == tmp_path / "2026" / "08-August" / "report.pdf"


def test_plan_moves_by_date_multiple_files_same_month(tmp_path):
    report = tmp_path / "report.pdf"
    photo = tmp_path / "photo.jpg"
    report.write_text("data")
    photo.write_text("data")
    _set_mtime(report, 2026, 8, 18)
    _set_mtime(photo, 2026, 8, 3)

    plan = plan_moves_by_date([report, photo], tmp_path)

    assert plan[0].destination == tmp_path / "2026" / "08-August" / "report.pdf"
    assert plan[1].destination == tmp_path / "2026" / "08-August" / "photo.jpg"


def test_plan_moves_by_date_ignores_filename_classification(tmp_path):
    # bank_statement.pdf would classify as Finance under plan_moves(),
    # but date mode must not consult filename rules at all.
    source = tmp_path / "bank_statement.pdf"
    source.write_text("data")
    _set_mtime(source, 2026, 8, 18)

    [move] = plan_moves_by_date([source], tmp_path)

    assert move.destination == tmp_path / "2026" / "08-August" / "bank_statement.pdf"
    assert not (tmp_path / "Finance").exists()


def test_plan_moves_by_date_ignores_extension_classification(tmp_path):
    # photo.jpg would classify as Images under plan_moves(), but date
    # mode must not consult extension rules at all.
    source = tmp_path / "photo.jpg"
    source.write_text("data")
    _set_mtime(source, 2026, 8, 18)

    [move] = plan_moves_by_date([source], tmp_path)

    assert move.destination == tmp_path / "2026" / "08-August" / "photo.jpg"
    assert not (tmp_path / "Images").exists()


def test_plan_moves_by_date_existing_destination_collision(tmp_path):
    dest_dir = tmp_path / "2026" / "08-August"
    dest_dir.mkdir(parents=True)
    (dest_dir / "report.pdf").write_text("existing")

    source = tmp_path / "report.pdf"
    source.write_text("new")
    _set_mtime(source, 2026, 8, 18)

    [move] = plan_moves_by_date([source], tmp_path)

    assert move.destination == dest_dir / "report (1).pdf"


def test_plan_moves_by_date_multiple_collisions_increment(tmp_path):
    dest_dir = tmp_path / "2026" / "08-August"
    dest_dir.mkdir(parents=True)
    (dest_dir / "report.pdf").write_text("existing")
    (dest_dir / "report (1).pdf").write_text("existing")

    source = tmp_path / "report.pdf"
    source.write_text("new")
    _set_mtime(source, 2026, 8, 18)

    [move] = plan_moves_by_date([source], tmp_path)

    assert move.destination == dest_dir / "report (2).pdf"


def test_plan_moves_by_date_does_not_modify_filesystem(tmp_path):
    source = tmp_path / "report.pdf"
    source.write_text("data")
    _set_mtime(source, 2026, 8, 18)

    plan_moves_by_date([source], tmp_path)

    assert not (tmp_path / "2026").exists()
    assert source.exists()
    assert source.read_text() == "data"


# --- Milestone 12: combined category + date organization ---


def test_category_date_pdf_with_no_filename_rule(tmp_path):
    source = tmp_path / "file.pdf"
    source.write_text("data")
    _set_mtime(source, 2026, 8, 18)

    [move] = plan_moves_by_category_and_date([source], tmp_path)

    assert move.category == "Documents/2026/08-August"
    assert move.destination == tmp_path / "Documents" / "2026" / "08-August" / "file.pdf"


def test_category_date_jpg(tmp_path):
    source = tmp_path / "photo.jpg"
    source.write_text("data")
    _set_mtime(source, 2026, 8, 18)

    [move] = plan_moves_by_category_and_date([source], tmp_path)

    assert move.destination == tmp_path / "Images" / "2026" / "08-August" / "photo.jpg"


def test_category_date_finance_filename_rule(tmp_path):
    source = tmp_path / "bank_statement.pdf"
    source.write_text("data")
    _set_mtime(source, 2026, 8, 18)

    [move] = plan_moves_by_category_and_date([source], tmp_path)

    assert move.destination == tmp_path / "Finance" / "2026" / "08-August" / "bank_statement.pdf"


def test_category_date_resumes_filename_rule(tmp_path):
    source = tmp_path / "resume_joseph.pdf"
    source.write_text("data")
    _set_mtime(source, 2026, 8, 18)

    [move] = plan_moves_by_category_and_date([source], tmp_path)

    assert move.destination == tmp_path / "Resumes" / "2026" / "08-August" / "resume_joseph.pdf"


def test_category_date_other_fallback(tmp_path):
    source = tmp_path / "mystery.xyz"
    source.write_text("data")
    _set_mtime(source, 2026, 8, 18)

    [move] = plan_moves_by_category_and_date([source], tmp_path)

    assert move.destination == tmp_path / "Other" / "2026" / "08-August" / "mystery.xyz"


def test_category_date_custom_config_category(tmp_path):
    source = tmp_path / "march_paystub.pdf"
    source.write_text("data")
    _set_mtime(source, 2026, 8, 18)
    custom_rules = ClassificationRules(
        filename_rules=(("*paystub*", "Payroll"),),
        extensions={},
    )

    [move] = plan_moves_by_category_and_date([source], tmp_path, custom_rules)

    assert move.destination == tmp_path / "Payroll" / "2026" / "08-August" / "march_paystub.pdf"


def test_category_date_filename_rule_overrides_extension(tmp_path):
    # vacation_invoice_photo.jpg would classify as Images by extension,
    # but the "*invoice*" filename rule takes precedence, same as
    # plain category mode.
    source = tmp_path / "vacation_invoice_photo.jpg"
    source.write_text("data")
    _set_mtime(source, 2026, 8, 18)

    [move] = plan_moves_by_category_and_date([source], tmp_path)

    expected = tmp_path / "Finance" / "2026" / "08-August" / "vacation_invoice_photo.jpg"
    assert move.destination == expected


def test_category_date_january_formatting(tmp_path):
    source = tmp_path / "report.pdf"
    source.write_text("data")
    _set_mtime(source, 2026, 1, 15)

    [move] = plan_moves_by_category_and_date([source], tmp_path)

    assert move.destination == tmp_path / "Documents" / "2026" / "01-January" / "report.pdf"


def test_category_date_august_formatting(tmp_path):
    source = tmp_path / "report.pdf"
    source.write_text("data")
    _set_mtime(source, 2026, 8, 18)

    [move] = plan_moves_by_category_and_date([source], tmp_path)

    assert move.destination == tmp_path / "Documents" / "2026" / "08-August" / "report.pdf"


def test_category_date_december_formatting(tmp_path):
    source = tmp_path / "report.pdf"
    source.write_text("data")
    _set_mtime(source, 2025, 12, 1)

    [move] = plan_moves_by_category_and_date([source], tmp_path)

    assert move.destination == tmp_path / "Documents" / "2025" / "12-December" / "report.pdf"


def test_category_date_different_years(tmp_path):
    old_file = tmp_path / "old.pdf"
    new_file = tmp_path / "new.pdf"
    old_file.write_text("data")
    new_file.write_text("data")
    _set_mtime(old_file, 2025, 12, 1)
    _set_mtime(new_file, 2026, 1, 1)

    plan = plan_moves_by_category_and_date([old_file, new_file], tmp_path)

    assert plan[0].destination == tmp_path / "Documents" / "2025" / "12-December" / "old.pdf"
    assert plan[1].destination == tmp_path / "Documents" / "2026" / "01-January" / "new.pdf"


def test_category_date_collision_gets_numbered_suffix(tmp_path):
    dest_dir = tmp_path / "Documents" / "2026" / "08-August"
    dest_dir.mkdir(parents=True)
    (dest_dir / "report.pdf").write_text("existing")

    source = tmp_path / "report.pdf"
    source.write_text("new")
    _set_mtime(source, 2026, 8, 18)

    [move] = plan_moves_by_category_and_date([source], tmp_path)

    assert move.destination == dest_dir / "report (1).pdf"


def test_category_date_multiple_collisions_increment(tmp_path):
    dest_dir = tmp_path / "Documents" / "2026" / "08-August"
    dest_dir.mkdir(parents=True)
    (dest_dir / "report.pdf").write_text("existing")
    (dest_dir / "report (1).pdf").write_text("existing")

    source = tmp_path / "report.pdf"
    source.write_text("new")
    _set_mtime(source, 2026, 8, 18)

    [move] = plan_moves_by_category_and_date([source], tmp_path)

    assert move.destination == dest_dir / "report (2).pdf"


def test_category_date_planning_does_not_modify_filesystem(tmp_path):
    source = tmp_path / "report.pdf"
    source.write_text("data")
    _set_mtime(source, 2026, 8, 18)

    plan_moves_by_category_and_date([source], tmp_path)

    assert not (tmp_path / "Documents").exists()
    assert source.exists()
    assert source.read_text() == "data"
