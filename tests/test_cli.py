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

