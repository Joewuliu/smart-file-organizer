"""Build a plan of file moves without touching the filesystem."""

from dataclasses import dataclass
from pathlib import Path

from organizer.classifier import DEFAULT_RULES, ClassificationRules, classify_file


@dataclass
class PlannedMove:
    source: Path
    destination: Path
    category: str


def _first_free_destination(dest_dir: Path, filename: str, reserved: set[Path]) -> Path:
    candidate = dest_dir / filename
    if not candidate.exists() and candidate not in reserved:
        return candidate

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        candidate = dest_dir / f"{stem} ({counter}){suffix}"
        if not candidate.exists() and candidate not in reserved:
            return candidate
        counter += 1


def plan_moves(
    files: list[Path], root: Path, rules: ClassificationRules = DEFAULT_RULES
) -> list[PlannedMove]:
    """Plan where each file in `files` should move to under `root`.

    Each file is classified with `classify_file()` using `rules`
    (built-in defaults unless a custom `ClassificationRules` is
    passed in) and placed at `root / category / filename`. If that
    destination is already taken (on disk or by an earlier
    PlannedMove in this plan), a numbered suffix "name (1).ext",
    "name (2).ext", ... is used instead. Input ordering is preserved.
    Raises NotADirectoryError if a category path already exists as a
    non-directory file. Never creates directories, moves files, or
    otherwise touches the filesystem.
    """
    reserved: set[Path] = set()
    plan: list[PlannedMove] = []

    for source in files:
        category = classify_file(source, rules)
        dest_dir = root / category

        if dest_dir.exists() and not dest_dir.is_dir():
            raise NotADirectoryError(
                f"Category path exists and is not a directory: {dest_dir}"
            )

        destination = _first_free_destination(dest_dir, source.name, reserved)
        reserved.add(destination)
        plan.append(PlannedMove(source=source, destination=destination, category=category))

    return plan
