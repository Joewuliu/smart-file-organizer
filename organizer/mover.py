"""Execute an already-built plan of file moves."""

import shutil
from dataclasses import dataclass

from organizer.planner import PlannedMove


@dataclass
class MoveResult:
    move: PlannedMove
    success: bool
    error: str | None = None


def _execute_one(move: PlannedMove) -> MoveResult:
    if not move.source.exists():
        return MoveResult(move, False, f"Source no longer exists: {move.source}")

    if move.destination.exists():
        return MoveResult(move, False, f"Destination already exists: {move.destination}")

    parent = move.destination.parent
    if parent.exists() and not parent.is_dir():
        return MoveResult(move, False, f"Destination parent is not a directory: {parent}")

    try:
        parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(move.source), str(move.destination))
    except (PermissionError, OSError) as exc:
        return MoveResult(move, False, str(exc))

    return MoveResult(move, True)


def execute_moves(plan: list[PlannedMove]) -> list[MoveResult]:
    """Execute each PlannedMove in `plan`, in order, and report outcomes.

    Uses the destination already decided by the planner as-is; never
    reclassifies a source file or picks an alternate destination.
    Immediately before each move, re-checks that the destination is
    still free — if it now exists, that move fails without touching
    either file. Missing sources, non-directory destination parents,
    and expected filesystem errors (PermissionError, OSError) are
    caught per move and reported as failures without stopping the
    rest of the batch. Never deletes, overwrites, or re-plans
    anything.
    """
    return [_execute_one(move) for move in plan]
