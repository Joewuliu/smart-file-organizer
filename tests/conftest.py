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


@pytest.fixture(autouse=True)
def _isolated_state(monkeypatch, tmp_path):
    """Redirect the managed-destinations state file to a per-test
    tmp_path location, for the same reason as `_isolated_history`:
    nothing in the suite should ever touch the developer's real
    ~/.smart-file-organizer/state.json.
    """
    monkeypatch.setattr(
        "organizer.state.DEFAULT_STATE_PATH", tmp_path / "_test_state" / "state.json"
    )
