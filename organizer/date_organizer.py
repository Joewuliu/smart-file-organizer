"""Derive a year/month destination category from a file's modification time."""

import calendar
from datetime import datetime
from pathlib import Path

_MONTH_DIR_NAMES = frozenset(f"{month:02d}-{calendar.month_name[month]}" for month in range(1, 13))


def date_category_for_file(path: Path) -> str:
    """Return the "YYYY/MM-MonthName" category for `path`'s mtime.

    Uses the file's last-modified time (mtime) in local time, not
    creation time and not the current wall-clock date. Reads the
    timestamp via `stat()` only; never modifies the filesystem.
    """
    modified = datetime.fromtimestamp(path.stat().st_mtime)
    month_name = calendar.month_name[modified.month]
    return f"{modified.year}/{modified.month:02d}-{month_name}"


def is_date_destination_dir(relative_path: Path) -> bool:
    """Return True if `relative_path` (a directory path relative to a
    scan root) has the exact "YYYY/MM-MonthName" shape this module
    generates, e.g. "2026/08-August".

    Requires both levels to match together, not just a 4-digit top
    directory, so an unrelated folder a user happens to have named
    like a year isn't mistaken for one of the organizer's own date
    destination trees. Used to keep recursive scanning from
    rediscovering and re-organizing files already placed there.
    """
    parts = relative_path.parts
    if len(parts) != 2:
        return False
    year, month_dir = parts
    return len(year) == 4 and year.isdigit() and month_dir in _MONTH_DIR_NAMES
