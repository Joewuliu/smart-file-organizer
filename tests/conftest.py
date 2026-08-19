import pytest


@pytest.fixture(autouse=True)
def _isolated_history(monkeypatch, tmp_path):
    """Redirect the undo-history file to a per-test tmp_path location.

    Applies to every test automatically so nothing in the suite ever
    reads or writes the developer's real
    ~/.smart-file-organizer/history.json.
    """
    monkeypatch.setattr(
        "organizer.history.DEFAULT_HISTORY_PATH", tmp_path / "_test_history" / "history.json"
    )
