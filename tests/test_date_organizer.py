import os
from datetime import datetime
from pathlib import Path

from organizer.date_organizer import date_category_for_file, is_date_destination_dir


def _set_mtime(path, year, month, day, hour=12):
    timestamp = datetime(year, month, day, hour).timestamp()
    os.utime(path, (timestamp, timestamp))


def test_january_file_maps_to_01_january(tmp_path):
    file = tmp_path / "report.pdf"
    file.write_text("data")
    _set_mtime(file, 2026, 1, 15)

    assert date_category_for_file(file) == "2026/01-January"


def test_august_file_maps_to_08_august(tmp_path):
    file = tmp_path / "photo.jpg"
    file.write_text("data")
    _set_mtime(file, 2026, 8, 18)

    assert date_category_for_file(file) == "2026/08-August"


def test_december_file_maps_to_12_december(tmp_path):
    file = tmp_path / "data.csv"
    file.write_text("data")
    _set_mtime(file, 2025, 12, 1)

    assert date_category_for_file(file) == "2025/12-December"


def test_different_years_produce_different_categories(tmp_path):
    old_file = tmp_path / "old_notes.txt"
    new_file = tmp_path / "new_notes.txt"
    old_file.write_text("data")
    new_file.write_text("data")
    _set_mtime(old_file, 2025, 12, 1)
    _set_mtime(new_file, 2026, 1, 1)

    assert date_category_for_file(old_file) == "2025/12-December"
    assert date_category_for_file(new_file) == "2026/01-January"


def test_uses_mtime_not_current_wall_clock_date(tmp_path):
    # The mtime is set to a date far from "today" to prove the
    # function reads the file's own timestamp rather than datetime.now().
    file = tmp_path / "time_capsule.txt"
    file.write_text("data")
    _set_mtime(file, 1999, 3, 5)

    assert date_category_for_file(file) == "1999/03-March"


def test_does_not_touch_filesystem(tmp_path):
    file = tmp_path / "report.pdf"
    file.write_text("data")
    _set_mtime(file, 2026, 8, 18)
    before_mtime = file.stat().st_mtime

    date_category_for_file(file)

    assert file.stat().st_mtime == before_mtime
    assert file.read_text() == "data"


# --- Milestone 11: recognizing date destination trees ---


def test_is_date_destination_dir_recognizes_valid_year_month_shape():
    assert is_date_destination_dir(Path("2026/08-August")) is True
    assert is_date_destination_dir(Path("1999/03-March")) is True
    assert is_date_destination_dir(Path("2025/12-December")) is True


def test_is_date_destination_dir_rejects_year_only():
    assert is_date_destination_dir(Path("2026")) is False


def test_is_date_destination_dir_rejects_non_four_digit_year():
    assert is_date_destination_dir(Path("26/08-August")) is False


def test_is_date_destination_dir_rejects_mismatched_month_string():
    assert is_date_destination_dir(Path("2026/08-NotAMonth")) is False
    assert is_date_destination_dir(Path("2026/August")) is False
    assert is_date_destination_dir(Path("2026/8-August")) is False


def test_is_date_destination_dir_rejects_deeper_nesting():
    assert is_date_destination_dir(Path("2026/08-August/extra")) is False


def test_is_date_destination_dir_rejects_unrelated_folder_named_like_a_year():
    # A plain "2020" folder with no month subdirectory below it is not
    # mistaken for an organizer-created date tree.
    assert is_date_destination_dir(Path("2020/personal_notes")) is False
