import pytest

from organizer.cli import main
from organizer.mover import MoveResult


def _make_files(tmp_path, names):
    for name in names:
        (tmp_path / name).write_text(name)


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


def test_partial_failure_reports_failed_count_and_returns_nonzero(
    tmp_path, monkeypatch, capsys
):
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

