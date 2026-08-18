"""Classify files into categories based on filename patterns and extension."""

import fnmatch
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

OTHER_CATEGORY = "Other"

# Default ordered (pattern, category) rules checked against the
# filename only (not the full path) before falling back to
# extension-based classification. Patterns use fnmatch glob syntax
# and are matched case-insensitively. Order matters: the first
# pattern that matches wins, even if a later pattern would also
# match.
DEFAULT_FILENAME_RULES: tuple[tuple[str, str], ...] = (
    ("*statement*", "Finance"),
    ("*invoice*", "Finance"),
    ("*receipt*", "Finance"),
    ("*homework*", "School"),
    ("*assignment*", "School"),
    ("*tuition*", "School"),
    ("*resume*", "Resumes"),
    ("*cv*", "Resumes"),
)

DEFAULT_EXTENSIONS: Mapping[str, str] = MappingProxyType(
    {
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
)


@dataclass(frozen=True)
class ClassificationRules:
    """An immutable set of classification rules.

    `filename_rules` is an ordered sequence of (pattern, category)
    pairs, checked first-match-wins. `extensions` maps a lowercase
    extension (including the leading dot) to a category, used as a
    fallback when no filename rule matches.
    """

    filename_rules: tuple[tuple[str, str], ...]
    extensions: Mapping[str, str]


DEFAULT_RULES = ClassificationRules(
    filename_rules=DEFAULT_FILENAME_RULES, extensions=DEFAULT_EXTENSIONS
)


def classify_extension(extension: str, rules: ClassificationRules = DEFAULT_RULES) -> str:
    """Return the category for a file extension (e.g. ".jpg").

    Matching is case-insensitive. An empty or unrecognized extension
    returns the "Other" category. Does not touch the filesystem.
    """
    normalized = extension.lower()
    return rules.extensions.get(normalized, OTHER_CATEGORY)


def classify_filename(filename: str, rules: ClassificationRules = DEFAULT_RULES) -> str | None:
    """Return the category matched by a filename pattern rule, if any.

    Checks `rules.filename_rules` in order and returns the category
    of the first matching pattern. Matching is case-insensitive and
    applies to `filename` only (never a parent directory or full
    path). Returns None if no filename rule matches.
    """
    normalized = filename.lower()
    for pattern, category in rules.filename_rules:
        if fnmatch.fnmatchcase(normalized, pattern.lower()):
            return category
    return None


def classify_file(path: Path, rules: ClassificationRules = DEFAULT_RULES) -> str:
    """Return the category for a file.

    Precedence:
    1. Filename pattern rules (`rules.filename_rules`), matched
       against `path.name` only.
    2. Extension-based classification (`rules.extensions`) if no
       filename rule matched.
    3. "Other" if neither matches.

    For compound extensions (e.g. "archive.tar.gz"), only the final
    suffix (".gz") is used. Does not touch the filesystem.
    """
    filename_category = classify_filename(path.name, rules)
    if filename_category is not None:
        return filename_category
    return classify_extension(path.suffix, rules)
