"""Build a plan of file moves without touching the filesystem."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from organizer.classifier import DEFAULT_RULES, ClassificationRules, classify_file
from organizer.date_organizer import date_category_for_file


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


def _plan_with_categorizer(
    files: list[Path], root: Path, categorize: Callable[[Path], str]
) -> list[PlannedMove]:
    """Shared planning loop: category/destination resolution and collision
    handling, independent of how `categorize` derives a category for a file.
    """
    reserved: set[Path] = set()
    plan: list[PlannedMove] = []

    for source in files:
        category = categorize(source)
        dest_dir = root / category

        if dest_dir.exists() and not dest_dir.is_dir():
            raise NotADirectoryError(f"Category path exists and is not a directory: {dest_dir}")

        destination = _first_free_destination(dest_dir, source.name, reserved)
        reserved.add(destination)
        plan.append(PlannedMove(source=source, destination=destination, category=category))

    return plan


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
    return _plan_with_categorizer(files, root, lambda source: classify_file(source, rules))


def plan_moves_by_date(files: list[Path], root: Path) -> list[PlannedMove]:
    """Plan where each file in `files` should move to, organized by
    modification date instead of category.

    Each file is placed at `root / "YYYY/MM-MonthName" / filename`
    based on its mtime (see `date_organizer.date_category_for_file`);
    filename and extension classification are not consulted at all.
    Collision handling, the non-directory-parent check, and the
    "never touches the filesystem" guarantee are identical to
    `plan_moves()`.
    """
    return _plan_with_categorizer(files, root, date_category_for_file)


def plan_moves_by_category_and_date(
    files: list[Path], root: Path, rules: ClassificationRules = DEFAULT_RULES
) -> list[PlannedMove]:
    """Plan where each file in `files` should move to, organized by
    both category and modification date.

    Composes `classify_file()` and `date_category_for_file()` rather
    than reimplementing either: each file is placed at
    `root / category / "YYYY/MM-MonthName" / filename`. Collision
    handling, the non-directory-parent check, and the "never touches
    the filesystem" guarantee are identical to `plan_moves()` and
    `plan_moves_by_date()`.
    """

    def categorize(source: Path) -> str:
        return f"{classify_file(source, rules)}/{date_category_for_file(source)}"

    return _plan_with_categorizer(files, root, categorize)
