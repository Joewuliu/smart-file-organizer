"""Track destination directories the organizer has actually created/used.

Lets recursive scanning distinguish organizer-managed destinations
from ordinary user folders that merely share a category name (e.g. a
real `root/School/` folder the tool has never organized into). State
is tracked per organization root and updated only after moves that
actually succeed.
"""

import json
from pathlib import Path

from organizer.mover import MoveResult

DEFAULT_STATE_PATH = Path.home() / ".smart-file-organizer" / "state.json"


class StateError(Exception):
    """Raised when the state file exists but cannot be safely interpreted.

    Callers should treat this as fatal for the recursive operation in
    progress rather than falling back to any assumed set of
    exclusions — a corrupted file must never silently become "no
    exclusions" (which could rediscover and re-move already-organized
    files) or "arbitrary exclusions" (which could hide real source
    files from being organized).
    """


def _resolve(path: Path | None) -> Path:
    return path if path is not None else DEFAULT_STATE_PATH


def _root_key(root: Path) -> str:
    return str(root.resolve())


def _load_raw(path: Path) -> dict:
    if not path.exists():
        return {"roots": {}}

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise StateError(f"State file is not valid JSON: {path}: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("roots"), dict):
        raise StateError(f"State file has an unrecognized structure: {path}")

    return data


def _write_raw(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2))
    tmp_path.replace(path)


def managed_directories(root: Path, path: Path | None = None) -> set[Path]:
    """Return the directories (relative to `root`) known to be
    organizer-managed destinations for `root`.

    Returns an empty set if no state file exists yet, or if `root`
    has no recorded entry (nothing has been organized there yet
    under explicit state tracking).

    Raises StateError if the state file exists but is corrupted or
    has an unrecognized shape for `root`'s entry.
    """
    data = _load_raw(_resolve(path))
    entry = data["roots"].get(_root_key(root))
    if entry is None:
        return set()

    directories = entry.get("managed_directories")
    if not isinstance(directories, list) or not all(isinstance(d, str) for d in directories):
        raise StateError(f"State entry for {root} has an unrecognized structure")

    return {Path(*d.split("/")) for d in directories}


def record_managed_destinations(
    results: list[MoveResult], root: Path, path: Path | None = None
) -> None:
    """Record the destination directories used by successful moves in
    `results` as organizer-managed for `root`.

    Only directories from moves with `success is True` are recorded;
    a failed move never marks its would-be destination as managed.
    If nothing succeeded, the state file is left untouched. Merges
    with (rather than replaces) any directories already recorded for
    `root`, and leaves every other root's entry untouched.
    """
    new_dirs = {
        result.move.destination.parent.relative_to(root) for result in results if result.success
    }
    if not new_dirs:
        return

    resolved_path = _resolve(path)
    data = _load_raw(resolved_path)
    key = _root_key(root)
    entry = data["roots"].setdefault(key, {"managed_directories": []})

    existing = set(entry.get("managed_directories", []))
    existing.update(d.as_posix() for d in new_dirs)
    entry["managed_directories"] = sorted(existing)

    _write_raw(data, resolved_path)
