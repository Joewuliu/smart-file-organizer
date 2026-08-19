"""Persist and reconstruct the most recent successful apply operation.

Stores just enough to undo the last `--apply`: for each move that
actually succeeded, its original source and final destination. Only
the single most recent operation is tracked (no multi-entry history,
no redo).
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from organizer.mover import MoveResult
from organizer.planner import PlannedMove

DEFAULT_HISTORY_PATH = Path.home() / ".smart-file-organizer" / "history.json"


@dataclass
class HistoryMove:
    source: Path
    destination: Path


@dataclass
class HistoryOperation:
    timestamp: str
    moves: list[HistoryMove]


def _resolve(path: Path | None) -> Path:
    return path if path is not None else DEFAULT_HISTORY_PATH


def _write(operation: HistoryOperation, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": operation.timestamp,
        "moves": [
            {"source": str(move.source), "destination": str(move.destination)}
            for move in operation.moves
        ],
    }
    path.write_text(json.dumps(data, indent=2))


def record_operation(results: list[MoveResult], path: Path | None = None) -> None:
    """Record the successful moves from an apply as the operation
    `--undo` will reverse next.

    Only moves with `success is True` are recorded; failed moves are
    never included. If nothing succeeded, any previously recorded
    operation is left untouched (this apply produced nothing new to
    undo). Overwrites any existing history, since V1 tracks only the
    single most recent operation.
    """
    successful = [result.move for result in results if result.success]
    if not successful:
        return

    moves = [HistoryMove(source=move.source, destination=move.destination) for move in successful]
    operation = HistoryOperation(timestamp=datetime.now(timezone.utc).isoformat(), moves=moves)
    _write(operation, _resolve(path))


def load_last_operation(path: Path | None = None) -> HistoryOperation | None:
    """Return the most recently recorded operation, or None if there
    is nothing to undo."""
    resolved = _resolve(path)
    if not resolved.exists():
        return None

    data = json.loads(resolved.read_text())
    moves = [
        HistoryMove(source=Path(entry["source"]), destination=Path(entry["destination"]))
        for entry in data["moves"]
    ]
    return HistoryOperation(timestamp=data["timestamp"], moves=moves)


def build_undo_plan(operation: HistoryOperation) -> list[PlannedMove]:
    """Build the reverse-direction plan that restores `operation`.

    Each recorded move's final destination becomes the undo source,
    and its original source becomes the undo destination. `category`
    is left blank; it has no meaning for an undo move.
    """
    return [
        PlannedMove(source=move.destination, destination=move.source, category="")
        for move in operation.moves
    ]


def save_remaining_operation(moves: list[HistoryMove], path: Path | None = None) -> None:
    """Overwrite history with only the moves that still need
    restoring, after a partially-successful undo."""
    operation = HistoryOperation(timestamp=datetime.now(timezone.utc).isoformat(), moves=moves)
    _write(operation, _resolve(path))


def clear_history(path: Path | None = None) -> None:
    """Remove any stored operation, after a fully successful undo."""
    _resolve(path).unlink(missing_ok=True)
