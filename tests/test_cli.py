import json
import os
from datetime import datetime

import pytest

from organizer.cli import main
from organizer.mover import MoveResult


def _make_files(tmp_path, names):
    for name in names:
        (tmp_path / name).write_text(name)


def _write_config(tmp_path, content, name="rules.toml"):
    path = tmp_path / name
    path.write_text(content)
    return path


def _set_mtime(path, year, month, day, hour=12):
    timestamp = datetime(year, month, day, hour).timestamp()
    os.utime(path, (timestamp, timestamp))


def _history_path(tmp_path):
    # Matches the location the autouse `_isolated_history` fixture in
    # conftest.py redirects organizer.history.DEFAULT_HISTORY_PATH to.
    return tmp_path / "_test_history" / "history.json"


def test_help_usage_shows_installed_command_name(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    out = capsys.readouterr().out
    assert exc_info.value.code == 0
    assert "usage: smart-organizer" in out


def test_dry_run_is_default_and_makes_no_changes(tmp_path, capsys):
    _make_files(tmp_path, ["report.pdf", "photo.jpg"])

    exit_code = main([str(tmp_path)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Dry run only. No files were modified." in out
    assert not (tmp_path / "Documents").exists()
    assert not (tmp_path / "Images").exists()
    assert (tmp_path / "report.pdf").exists()
    assert (tmp_path / "photo.jpg").exists()


def test_preview_lists_correct_categories_and_destinations(tmp_path, capsys):
    _make_files(tmp_path, ["report.pdf", "photo.jpg", "budget.xlsx", "mystery.xyz"])

    main([str(tmp_path)])

    out = capsys.readouterr().out
    assert "report.pdf" in out
    assert "-> Documents\\report.pdf" in out or "-> Documents/report.pdf" in out
    assert "photo.jpg" in out
    assert "-> Images\\photo.jpg" in out or "-> Images/photo.jpg" in out
    assert "budget.xlsx" in out
    assert "-> Spreadsheets\\budget.xlsx" in out or "-> Spreadsheets/budget.xlsx" in out
    assert "mystery.xyz" in out
    assert "-> Other\\mystery.xyz" in out or "-> Other/mystery.xyz" in out
    assert "4 files would be moved." in out


def test_apply_with_lowercase_y_executes_moves(tmp_path, monkeypatch):
    _make_files(tmp_path, ["report.pdf"])
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    exit_code = main([str(tmp_path), "--apply"])

    assert exit_code == 0
    assert (tmp_path / "Documents" / "report.pdf").exists()
    assert not (tmp_path / "report.pdf").exists()


def test_apply_with_yes_executes_moves(tmp_path, monkeypatch):
    _make_files(tmp_path, ["report.pdf"])
    monkeypatch.setattr("builtins.input", lambda prompt: "yes")

    exit_code = main([str(tmp_path), "--apply"])

    assert exit_code == 0
    assert (tmp_path / "Documents" / "report.pdf").exists()


def test_apply_with_enter_cancels(tmp_path, monkeypatch, capsys):
    _make_files(tmp_path, ["report.pdf"])
    monkeypatch.setattr("builtins.input", lambda prompt: "")

    exit_code = main([str(tmp_path), "--apply"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Operation cancelled. No files were modified." in out
    assert (tmp_path / "report.pdf").exists()
    assert not (tmp_path / "Documents").exists()


def test_apply_with_n_cancels(tmp_path, monkeypatch, capsys):
    _make_files(tmp_path, ["report.pdf"])
    monkeypatch.setattr("builtins.input", lambda prompt: "n")

    exit_code = main([str(tmp_path), "--apply"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Operation cancelled. No files were modified." in out
    assert (tmp_path / "report.pdf").exists()


@pytest.mark.parametrize("answer", ["Y", "YES", "yEs", "y", "yes"])
def test_confirmation_is_case_insensitive(tmp_path, monkeypatch, answer):
    _make_files(tmp_path, ["report.pdf"])
    monkeypatch.setattr("builtins.input", lambda prompt: answer)

    exit_code = main([str(tmp_path), "--apply"])

    assert exit_code == 0
    assert (tmp_path / "Documents" / "report.pdf").exists()


def test_cancelled_operation_leaves_files_untouched(tmp_path, monkeypatch):
    _make_files(tmp_path, ["report.pdf", "photo.jpg"])
    monkeypatch.setattr("builtins.input", lambda prompt: "no")

    main([str(tmp_path), "--apply"])

    assert (tmp_path / "report.pdf").exists()
    assert (tmp_path / "photo.jpg").exists()
    assert not (tmp_path / "Documents").exists()
    assert not (tmp_path / "Images").exists()


def test_nonexistent_directory_returns_nonzero(tmp_path, capsys):
    missing = tmp_path / "does_not_exist"

    exit_code = main([str(missing)])

    out = capsys.readouterr().out
    assert exit_code != 0
    assert "Traceback" not in out


def test_path_is_a_file_returns_nonzero(tmp_path, capsys):
    file_path = tmp_path / "not_a_dir.txt"
    file_path.write_text("data")

    exit_code = main([str(file_path)])

    out = capsys.readouterr().out
    assert exit_code != 0
    assert "Traceback" not in out


def test_empty_directory_reports_no_files_message(tmp_path, capsys):
    exit_code = main([str(tmp_path)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "No files to organize." in out


def test_successful_apply_reports_moved_count(tmp_path, monkeypatch, capsys):
    _make_files(tmp_path, ["report.pdf", "photo.jpg", "budget.xlsx"])
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    exit_code = main([str(tmp_path), "--apply"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Moved: 3" in out
    assert "Failed: 0" in out


def test_partial_failure_reports_failed_count_and_returns_nonzero(tmp_path, monkeypatch, capsys):
    _make_files(tmp_path, ["report.pdf", "photo.jpg"])
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    def fake_execute_moves(plan):
        results = []
        for i, move in enumerate(plan):
            if i == 0:
                results.append(MoveResult(move, False, "Destination already exists"))
            else:
                results.append(MoveResult(move, True))
        return results

    monkeypatch.setattr("organizer.cli.execute_moves", fake_execute_moves)

    exit_code = main([str(tmp_path), "--apply"])

    out = capsys.readouterr().out
    assert exit_code == 1
    assert "Moved: 1" in out
    assert "Failed: 1" in out
    assert "Destination already exists" in out


def test_preview_appears_before_confirmation_prompt(tmp_path, monkeypatch, capsys):
    _make_files(tmp_path, ["report.pdf"])
    captured = {}

    def fake_input(prompt):
        captured["out_so_far"] = capsys.readouterr().out
        return "n"

    monkeypatch.setattr("builtins.input", fake_input)

    main([str(tmp_path), "--apply"])

    assert "Proposed moves:" in captured["out_so_far"]
    assert "report.pdf" in captured["out_so_far"]


def test_execute_moves_not_called_during_dry_run(tmp_path, monkeypatch):
    _make_files(tmp_path, ["report.pdf"])

    def fail_if_called(plan):
        raise AssertionError("execute_moves should not be called during dry run")

    monkeypatch.setattr("organizer.cli.execute_moves", fail_if_called)

    exit_code = main([str(tmp_path)])

    assert exit_code == 0


def test_execute_moves_not_called_when_declined(tmp_path, monkeypatch):
    _make_files(tmp_path, ["report.pdf"])
    monkeypatch.setattr("builtins.input", lambda prompt: "n")

    def fail_if_called(plan):
        raise AssertionError("execute_moves should not be called when declined")

    monkeypatch.setattr("organizer.cli.execute_moves", fail_if_called)

    exit_code = main([str(tmp_path), "--apply"])

    assert exit_code == 0


def test_config_dry_run_uses_custom_rules(tmp_path, capsys):
    _make_files(tmp_path, ["march_paystub.pdf"])
    config = _write_config(
        tmp_path,
        """
[[filename_rules]]
pattern = "*paystub*"
category = "Payroll"
""",
    )

    exit_code = main([str(tmp_path), "--config", str(config)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "-> Payroll\\march_paystub.pdf" in out or "-> Payroll/march_paystub.pdf" in out
    assert not (tmp_path / "Payroll").exists()


def test_config_apply_uses_custom_rules_only_after_confirmation(tmp_path, monkeypatch):
    _make_files(tmp_path, ["march_paystub.pdf"])
    config = _write_config(
        tmp_path,
        """
[[filename_rules]]
pattern = "*paystub*"
category = "Payroll"
""",
    )
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    exit_code = main([str(tmp_path), "--config", str(config), "--apply"])

    assert exit_code == 0
    assert (tmp_path / "Payroll" / "march_paystub.pdf").exists()


def test_config_apply_without_confirmation_does_not_move_files(tmp_path, monkeypatch):
    _make_files(tmp_path, ["march_paystub.pdf"])
    config = _write_config(
        tmp_path,
        """
[[filename_rules]]
pattern = "*paystub*"
category = "Payroll"
""",
    )
    monkeypatch.setattr("builtins.input", lambda prompt: "n")

    exit_code = main([str(tmp_path), "--config", str(config), "--apply"])

    assert exit_code == 0
    assert not (tmp_path / "Payroll").exists()
    assert (tmp_path / "march_paystub.pdf").exists()


def test_missing_config_file_returns_nonzero_and_touches_nothing(tmp_path, capsys):
    _make_files(tmp_path, ["report.pdf"])
    missing_config = tmp_path / "does_not_exist.toml"

    exit_code = main([str(tmp_path), "--config", str(missing_config), "--apply"])

    out = capsys.readouterr().out
    assert exit_code != 0
    assert "Traceback" not in out
    assert (tmp_path / "report.pdf").exists()
    assert not (tmp_path / "Documents").exists()


def test_invalid_config_cannot_modify_filesystem(tmp_path, monkeypatch):
    _make_files(tmp_path, ["report.pdf"])
    config = _write_config(
        tmp_path,
        """
[extensions]
".pdf" = ".."
""",
    )
    # Even if the user would have confirmed, invalid config must be
    # rejected before the confirmation prompt is ever reached.
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    exit_code = main([str(tmp_path), "--config", str(config), "--apply"])

    assert exit_code != 0
    assert (tmp_path / "report.pdf").exists()
    assert not (tmp_path / "Documents").exists()


def test_invalid_config_never_calls_execute_moves(tmp_path, monkeypatch):
    config = _write_config(tmp_path, "this is not [ valid toml")

    def fail_if_called(plan):
        raise AssertionError("execute_moves should not be called for invalid config")

    monkeypatch.setattr("organizer.cli.execute_moves", fail_if_called)

    exit_code = main([str(tmp_path), "--config", str(config), "--apply"])

    assert exit_code != 0


def test_no_config_flag_behaves_exactly_as_before(tmp_path, capsys):
    _make_files(tmp_path, ["bank_statement.pdf", "photo.jpg"])

    exit_code = main([str(tmp_path)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "-> Finance\\bank_statement.pdf" in out or "-> Finance/bank_statement.pdf" in out
    assert "-> Images\\photo.jpg" in out or "-> Images/photo.jpg" in out


def test_default_by_is_category_mode(tmp_path, capsys):
    _make_files(tmp_path, ["bank_statement.pdf"])

    exit_code = main([str(tmp_path)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "-> Finance\\bank_statement.pdf" in out or "-> Finance/bank_statement.pdf" in out


def test_explicit_by_category_matches_default(tmp_path, capsys):
    _make_files(tmp_path, ["bank_statement.pdf"])

    exit_code = main([str(tmp_path), "--by", "category"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "-> Finance\\bank_statement.pdf" in out or "-> Finance/bank_statement.pdf" in out


def test_by_date_produces_date_preview(tmp_path, capsys):
    file = tmp_path / "report.pdf"
    file.write_text("data")
    _set_mtime(file, 2026, 8, 18)

    exit_code = main([str(tmp_path), "--by", "date"])

    out = capsys.readouterr().out
    assert exit_code == 0
    joined_dest = os.path.join("2026", "08-August", "report.pdf")
    assert f"-> {joined_dest}" in out


def test_by_date_dry_run_moves_nothing(tmp_path):
    file = tmp_path / "report.pdf"
    file.write_text("data")
    _set_mtime(file, 2026, 8, 18)

    exit_code = main([str(tmp_path), "--by", "date"])

    assert exit_code == 0
    assert file.exists()
    assert not (tmp_path / "2026").exists()


def test_by_date_apply_with_confirmation_moves_files(tmp_path, monkeypatch):
    file = tmp_path / "report.pdf"
    file.write_text("data")
    _set_mtime(file, 2026, 8, 18)
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    exit_code = main([str(tmp_path), "--by", "date", "--apply"])

    assert exit_code == 0
    assert (tmp_path / "2026" / "08-August" / "report.pdf").exists()
    assert not file.exists()


def test_by_date_apply_declined_moves_nothing(tmp_path, monkeypatch):
    file = tmp_path / "report.pdf"
    file.write_text("data")
    _set_mtime(file, 2026, 8, 18)
    monkeypatch.setattr("builtins.input", lambda prompt: "n")

    exit_code = main([str(tmp_path), "--by", "date", "--apply"])

    assert exit_code == 0
    assert file.exists()
    assert not (tmp_path / "2026").exists()


def test_by_date_with_config_returns_clear_error_and_moves_nothing(tmp_path, capsys):
    file = tmp_path / "report.pdf"
    file.write_text("data")
    _set_mtime(file, 2026, 8, 18)
    config = _write_config(
        tmp_path,
        """
[extensions]
".pdf" = "Documents"
""",
    )

    exit_code = main([str(tmp_path), "--by", "date", "--config", str(config), "--apply"])

    out = capsys.readouterr().out
    assert exit_code != 0
    assert "Traceback" not in out
    assert file.exists()
    assert not (tmp_path / "2026").exists()
    assert not (tmp_path / "Documents").exists()


def test_invalid_by_value_rejected_by_argparse(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc_info:
        main([str(tmp_path), "--by", "bogus"])

    assert exc_info.value.code != 0


# --- Milestone 9: history and undo ---


def test_successful_apply_creates_history(tmp_path, monkeypatch):
    _make_files(tmp_path, ["report.pdf"])
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    exit_code = main([str(tmp_path), "--apply"])

    assert exit_code == 0
    assert _history_path(tmp_path).exists()


def test_dry_run_creates_no_history(tmp_path):
    _make_files(tmp_path, ["report.pdf"])

    main([str(tmp_path)])

    assert not _history_path(tmp_path).exists()


def test_cancelled_apply_creates_no_history(tmp_path, monkeypatch):
    _make_files(tmp_path, ["report.pdf"])
    monkeypatch.setattr("builtins.input", lambda prompt: "n")

    main([str(tmp_path), "--apply"])

    assert not _history_path(tmp_path).exists()


def test_failed_moves_are_not_included_in_history(tmp_path, monkeypatch):
    # planner.py already avoids destination collisions by numbering
    # around them, so a real mover-level failure only happens from a
    # race between planning and execution (already covered in
    # test_mover.py). Here we stub execute_moves to return a
    # partial failure directly, so this test can focus purely on
    # verifying the CLI only records the successful move in history.
    _make_files(tmp_path, ["report.pdf", "notes.txt"])

    def fake_execute_moves(plan):
        results = []
        for move in plan:
            success = move.source.name == "notes.txt"
            results.append(MoveResult(move, success, None if success else "boom"))
        return results

    monkeypatch.setattr("organizer.cli.execute_moves", fake_execute_moves)
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    exit_code = main([str(tmp_path), "--apply"])

    assert exit_code == 1
    data = json.loads(_history_path(tmp_path).read_text())
    assert len(data["moves"]) == 1
    assert data["moves"][0]["source"].endswith("notes.txt")


def test_undo_with_no_history_is_safe(tmp_path, capsys):
    exit_code = main(["--undo"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "No operation available to undo." in out
    assert not _history_path(tmp_path).exists()


def test_undo_shows_preview_before_confirmation(tmp_path, monkeypatch, capsys):
    _make_files(tmp_path, ["report.pdf"])
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    main([str(tmp_path), "--apply"])
    capsys.readouterr()

    captured = {}

    def fake_input(prompt):
        captured["out_so_far"] = capsys.readouterr().out
        return "n"

    monkeypatch.setattr("builtins.input", fake_input)

    main(["--undo"])

    assert "Undo last operation:" in captured["out_so_far"]
    assert "report.pdf" in captured["out_so_far"]


def test_undo_with_lowercase_y_restores_files(tmp_path, monkeypatch):
    _make_files(tmp_path, ["report.pdf"])
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    main([str(tmp_path), "--apply"])
    assert (tmp_path / "Documents" / "report.pdf").exists()

    exit_code = main(["--undo"])

    assert exit_code == 0
    assert (tmp_path / "report.pdf").exists()
    assert not (tmp_path / "Documents" / "report.pdf").exists()


def test_undo_with_yes_restores_files(tmp_path, monkeypatch):
    _make_files(tmp_path, ["report.pdf"])
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    main([str(tmp_path), "--apply"])

    monkeypatch.setattr("builtins.input", lambda prompt: "yes")
    exit_code = main(["--undo"])

    assert exit_code == 0
    assert (tmp_path / "report.pdf").exists()


def test_undo_with_enter_cancels(tmp_path, monkeypatch):
    _make_files(tmp_path, ["report.pdf"])
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    main([str(tmp_path), "--apply"])

    monkeypatch.setattr("builtins.input", lambda prompt: "")
    exit_code = main(["--undo"])

    assert exit_code == 0
    assert (tmp_path / "Documents" / "report.pdf").exists()
    assert not (tmp_path / "report.pdf").exists()
    assert _history_path(tmp_path).exists()


def test_undo_with_n_cancels(tmp_path, monkeypatch):
    _make_files(tmp_path, ["report.pdf"])
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    main([str(tmp_path), "--apply"])

    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    exit_code = main(["--undo"])

    assert exit_code == 0
    assert (tmp_path / "Documents" / "report.pdf").exists()
    assert not (tmp_path / "report.pdf").exists()


def test_cancelled_undo_changes_nothing(tmp_path, monkeypatch):
    _make_files(tmp_path, ["report.pdf", "photo.jpg"])
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    main([str(tmp_path), "--apply"])
    history_before = _history_path(tmp_path).read_text()

    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    main(["--undo"])

    assert (tmp_path / "Documents" / "report.pdf").exists()
    assert (tmp_path / "Images" / "photo.jpg").exists()
    assert _history_path(tmp_path).read_text() == history_before


def test_undo_never_overwrites_occupied_original_path(tmp_path, monkeypatch):
    _make_files(tmp_path, ["report.pdf"])
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    main([str(tmp_path), "--apply"])
    assert (tmp_path / "Documents" / "report.pdf").exists()

    # Something else now occupies the original location before undo runs.
    (tmp_path / "report.pdf").write_text("new unrelated file")

    exit_code = main(["--undo"])

    assert exit_code == 1
    assert (tmp_path / "report.pdf").read_text() == "new unrelated file"
    assert (tmp_path / "Documents" / "report.pdf").read_text() == "report.pdf"


def test_one_undo_failure_does_not_block_later_moves(tmp_path, monkeypatch):
    _make_files(tmp_path, ["report.pdf", "notes.txt"])
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    main([str(tmp_path), "--apply"])

    # Block report.pdf's undo by occupying its original location.
    (tmp_path / "report.pdf").write_text("blocker")

    exit_code = main(["--undo"])

    assert exit_code == 1
    assert (tmp_path / "notes.txt").exists()
    assert not (tmp_path / "Documents" / "notes.txt").exists()
    assert (tmp_path / "Documents" / "report.pdf").exists()


def test_successful_undo_makes_operation_unavailable_for_another_undo(
    tmp_path, monkeypatch, capsys
):
    _make_files(tmp_path, ["report.pdf"])
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    main([str(tmp_path), "--apply"])

    main(["--undo"])
    assert not _history_path(tmp_path).exists()

    exit_code = main(["--undo"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "No operation available to undo." in out


def test_partial_undo_retains_only_unrestored_moves(tmp_path, monkeypatch):
    _make_files(tmp_path, ["report.pdf", "notes.txt"])
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    main([str(tmp_path), "--apply"])

    # Occupy report.pdf's original spot so its undo fails while
    # notes.txt's undo succeeds.
    (tmp_path / "report.pdf").write_text("blocker")

    main(["--undo"])

    data = json.loads(_history_path(tmp_path).read_text())
    assert len(data["moves"]) == 1
    assert data["moves"][0]["source"].endswith("report.pdf")

    # Fix the collision and retry: only the remaining file should move.
    (tmp_path / "report.pdf").unlink()
    exit_code = main(["--undo"])

    assert exit_code == 0
    assert (tmp_path / "report.pdf").exists()
    assert not _history_path(tmp_path).exists()


def test_undo_with_directory_argument_is_rejected(tmp_path, capsys):
    _make_files(tmp_path, ["report.pdf"])

    exit_code = main([str(tmp_path), "--undo"])

    out = capsys.readouterr().out
    assert exit_code != 0
    assert "Traceback" not in out
    assert (tmp_path / "report.pdf").exists()


def test_undo_with_by_date_is_rejected(capsys):
    exit_code = main(["--undo", "--by", "date"])

    out = capsys.readouterr().out
    assert exit_code != 0
    assert "Traceback" not in out


def test_undo_with_config_is_rejected(tmp_path, capsys):
    config = _write_config(tmp_path, '[extensions]\n".pdf" = "Documents"\n')

    exit_code = main(["--undo", "--config", str(config)])

    out = capsys.readouterr().out
    assert exit_code != 0
    assert "Traceback" not in out


def test_undo_with_apply_flag_is_rejected(capsys):
    exit_code = main(["--undo", "--apply"])

    out = capsys.readouterr().out
    assert exit_code != 0
    assert "Traceback" not in out


def test_missing_directory_without_undo_is_rejected(capsys):
    exit_code = main([])

    out = capsys.readouterr().out
    assert exit_code != 0
    assert "Traceback" not in out


def test_category_mode_still_works_after_history_wiring(tmp_path, monkeypatch):
    _make_files(tmp_path, ["bank_statement.pdf"])
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    exit_code = main([str(tmp_path), "--apply"])

    assert exit_code == 0
    assert (tmp_path / "Finance" / "bank_statement.pdf").exists()


def test_date_mode_still_works_after_history_wiring(tmp_path, monkeypatch):
    file = tmp_path / "report.pdf"
    file.write_text("data")
    _set_mtime(file, 2026, 8, 18)
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    exit_code = main([str(tmp_path), "--by", "date", "--apply"])

    assert exit_code == 0
    assert (tmp_path / "2026" / "08-August" / "report.pdf").exists()


def test_config_mode_still_works_after_history_wiring(tmp_path, monkeypatch):
    _make_files(tmp_path, ["march_paystub.pdf"])
    config = _write_config(
        tmp_path,
        """
[[filename_rules]]
pattern = "*paystub*"
category = "Payroll"
""",
    )
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    exit_code = main([str(tmp_path), "--config", str(config), "--apply"])

    assert exit_code == 0
    assert (tmp_path / "Payroll" / "march_paystub.pdf").exists()
