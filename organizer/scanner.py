"""Scan a directory for files to organize, optionally recursing into subdirectories."""

import os
from pathlib import Path
from typing import Callable

SKIPPED_FILENAMES = {"desktop.ini", "thumbs.db", ".ds_store"}


def _scan_flat(directory: Path) -> list[Path]:
    files = [
        entry
        for entry in directory.iterdir()
        if entry.is_file()
        and not entry.is_symlink()
        and entry.name.lower() not in SKIPPED_FILENAMES
    ]
    return sorted(files, key=lambda entry: entry.name.lower())


def _scan_recursive(directory: Path, exclude_dir: Callable[[Path], bool] | None) -> list[Path]:
    files: list[Path] = []

    for current_dir, subdirs, filenames in os.walk(directory, followlinks=False):
        current = Path(current_dir)

        kept_subdirs = []
        for name in subdirs:
            sub = current / name
            if sub.is_symlink():
                continue
            if exclude_dir is not None and exclude_dir(sub.relative_to(directory)):
                continue
            kept_subdirs.append(name)
        subdirs[:] = kept_subdirs

        for name in filenames:
            if name.lower() in SKIPPED_FILENAMES:
                continue
            entry = current / name
            if entry.is_symlink():
                continue
            if not entry.is_file():
                continue
            files.append(entry)

    return sorted(files, key=lambda entry: entry.relative_to(directory).as_posix().lower())


def scan_directory(
    directory: Path,
    recursive: bool = False,
    exclude_dir: Callable[[Path], bool] | None = None,
) -> list[Path]:
    """Return files inside `directory`, sorted deterministically.

    By default (`recursive=False`), only immediate children are
    inspected, matching the original non-recursive behavior exactly.
    With `recursive=True`, subdirectories are walked too, except:

    - symlinked directories are never followed
    - any subdirectory for which `exclude_dir(relative_path)` returns
      True is pruned entirely (its contents are never visited);
      `relative_path` is that directory's path relative to
      `directory`. Callers use this to keep the scanner from
      rediscovering the organizer's own destination folders.

    In both modes: only files are returned (never directories),
    symlinked files are skipped, and desktop.ini/Thumbs.db/.DS_Store
    are skipped case-insensitively. Recursive ordering is by each
    file's path relative to `directory` (case-insensitive); flat
    ordering is by filename (case-insensitive). Never modifies the
    filesystem.

    Raises FileNotFoundError if `directory` does not exist, and
    NotADirectoryError if it exists but is not a directory.
    """
    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory}")

    if recursive:
        return _scan_recursive(directory, exclude_dir)
    return _scan_flat(directory)
