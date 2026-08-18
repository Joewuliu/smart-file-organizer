"""Load and validate user-supplied classification rules from a TOML file."""

import tomllib
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from organizer.classifier import ClassificationRules


class ConfigError(Exception):
    """Raised when a user-supplied config file is missing or invalid."""


def _validate_category(category: object, context: str) -> str:
    if not isinstance(category, str) or not category:
        raise ConfigError(f"{context}: category must be a non-empty string, got {category!r}")
    if category in (".", ".."):
        raise ConfigError(f"{context}: category cannot be '{category}'")
    if "/" in category or "\\" in category:
        raise ConfigError(
            f"{context}: category cannot contain a path separator, got {category!r}"
        )
    if Path(category).is_absolute():
        raise ConfigError(f"{context}: category cannot be an absolute path, got {category!r}")
    return category


def _parse_filename_rules(raw: object) -> tuple[tuple[str, str], ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ConfigError("'filename_rules' must be an array of tables")

    rules: list[tuple[str, str]] = []
    for index, entry in enumerate(raw):
        context = f"filename_rules[{index}]"
        if not isinstance(entry, dict):
            raise ConfigError(f"{context}: must be a table with 'pattern' and 'category'")

        pattern = entry.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            raise ConfigError(f"{context}: 'pattern' must be a non-empty string")

        category = _validate_category(entry.get("category"), context)
        rules.append((pattern, category))

    return tuple(rules)


def _parse_extensions(raw: object) -> Mapping[str, str]:
    if raw is None:
        return MappingProxyType({})
    if not isinstance(raw, dict):
        raise ConfigError("'extensions' must be a table mapping extensions to categories")

    extensions: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.startswith("."):
            raise ConfigError(f"extensions: keys must start with '.', got {key!r}")
        category = _validate_category(value, f"extensions[{key!r}]")
        extensions[key.lower()] = category

    return MappingProxyType(extensions)


def load_rules(path: Path) -> ClassificationRules:
    """Load and validate classification rules from a TOML config file.

    The file fully defines the ruleset: a missing `filename_rules`
    array or `extensions` table means zero rules of that kind, not a
    merge with the built-in defaults.

    Raises ConfigError if the file is missing, isn't valid TOML, or
    contains an invalid rule (wrong shape, unsafe category name,
    etc). A config is either loaded successfully in full or not at
    all — never partially applied.
    """
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    if not path.is_file():
        raise ConfigError(f"Config path is not a file: {path}")

    try:
        with path.open("rb") as config_file:
            data = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in config file {path}: {exc}") from exc

    filename_rules = _parse_filename_rules(data.get("filename_rules"))
    extensions = _parse_extensions(data.get("extensions"))

    return ClassificationRules(filename_rules=filename_rules, extensions=extensions)
