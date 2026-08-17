"""Scan a directory's immediate children for files to organize."""

from pathlib import Path

SKIPPED_FILENAMES = {"desktop.ini", "thumbs.db", ".ds_store"}


def scan_directory(directory: Path) -> list[Path]:
    """Return files directly inside `directory`, sorted alphabetically.

    Only immediate children are inspected; subdirectories are not
    recursed into. Subdirectories themselves, symlinks, and common
    system files (desktop.ini, Thumbs.db, .DS_Store, matched
    case-insensitively) are excluded. Sorting is case-insensitive by
    filename. Never modifies the filesystem.

    Raises FileNotFoundError if `directory` does not exist, and
    NotADirectoryError if it exists but is not a directory.
    """
    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory}")

    files = [
        entry
        for entry in directory.iterdir()
        if entry.is_file()
        and not entry.is_symlink()
        and entry.name.lower() not in SKIPPED_FILENAMES
    ]
    return sorted(files, key=lambda entry: entry.name.lower())
