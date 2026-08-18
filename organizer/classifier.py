"""Classify files into categories based on filename patterns and extension."""

import fnmatch
from pathlib import Path

OTHER_CATEGORY = "Other"

# Ordered (pattern, category) rules checked against the filename only
# (not the full path) before falling back to extension-based
# classification. Patterns use fnmatch glob syntax and are matched
# case-insensitively. The list is ordered top to bottom: the first
# pattern that matches wins, even if a later pattern would also match.
FILENAME_RULES: list[tuple[str, str]] = [
    ("*statement*", "Finance"),
    ("*invoice*", "Finance"),
    ("*receipt*", "Finance"),
    ("*homework*", "School"),
    ("*assignment*", "School"),
    ("*tuition*", "School"),
    ("*resume*", "Resumes"),
    ("*cv*", "Resumes"),
]

EXTENSION_CATEGORIES: dict[str, str] = {
    ".pdf": "Documents",
    ".doc": "Documents",
    ".docx": "Documents",
    ".txt": "Documents",
    ".rtf": "Documents",
    ".jpg": "Images",
    ".jpeg": "Images",
    ".png": "Images",
    ".gif": "Images",
    ".webp": "Images",
    ".xlsx": "Spreadsheets",
    ".xls": "Spreadsheets",
    ".csv": "Spreadsheets",
    ".mp4": "Videos",
    ".mov": "Videos",
    ".avi": "Videos",
    ".mkv": "Videos",
    ".mp3": "Audio",
    ".wav": "Audio",
    ".m4a": "Audio",
    ".zip": "Archives",
    ".tar": "Archives",
    ".gz": "Archives",
    ".7z": "Archives",
    ".py": "Code",
    ".js": "Code",
    ".ts": "Code",
    ".java": "Code",
    ".cpp": "Code",
    ".c": "Code",
    ".html": "Code",
    ".css": "Code",
    ".json": "Code",
}


def classify_extension(extension: str) -> str:
    """Return the category for a file extension (e.g. ".jpg").

    Matching is case-insensitive. An empty or unrecognized extension
    returns the "Other" category. Does not touch the filesystem.
    """
    normalized = extension.lower()
    return EXTENSION_CATEGORIES.get(normalized, OTHER_CATEGORY)


def classify_filename(filename: str) -> str | None:
    """Return the category matched by a filename pattern rule, if any.

    Checks `FILENAME_RULES` in order and returns the category of the
    first matching pattern. Matching is case-insensitive and applies
    to `filename` only (never a parent directory or full path).
    Returns None if no filename rule matches.
    """
    normalized = filename.lower()
    for pattern, category in FILENAME_RULES:
        if fnmatch.fnmatchcase(normalized, pattern.lower()):
            return category
    return None


def classify_file(path: Path) -> str:
    """Return the category for a file.

    Precedence:
    1. Filename pattern rules (see `FILENAME_RULES`), matched against
       `path.name` only.
    2. Extension-based classification if no filename rule matched.
    3. "Other" if neither matches.

    For compound extensions (e.g. "archive.tar.gz"), only the final
    suffix (".gz") is used. Does not touch the filesystem.
    """
    filename_category = classify_filename(path.name)
    if filename_category is not None:
        return filename_category
    return classify_extension(path.suffix)
