"""Derive a year/month destination category from a file's modification time."""

import calendar
from datetime import datetime
from pathlib import Path


def date_category_for_file(path: Path) -> str:
    """Return the "YYYY/MM-MonthName" category for `path`'s mtime.

    Uses the file's last-modified time (mtime) in local time, not
    creation time and not the current wall-clock date. Reads the
    timestamp via `stat()` only; never modifies the filesystem.
    """
    modified = datetime.fromtimestamp(path.stat().st_mtime)
    month_name = calendar.month_name[modified.month]
    return f"{modified.year}/{modified.month:02d}-{month_name}"
