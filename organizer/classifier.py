"""Classify files into categories based on their extension."""

from pathlib import Path

OTHER_CATEGORY = "Other"

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


def classify_file(path: Path) -> str:
    """Return the category for a file based on its suffix.

    For compound extensions (e.g. "archive.tar.gz"), only the final
    suffix (".gz") is used. Does not touch the filesystem.
    """
    return classify_extension(path.suffix)
