from pathlib import Path

import pytest

from organizer.classifier import classify_file
from organizer.config import ConfigError, load_rules


def _write_config(tmp_path, content):
    path = tmp_path / "rules.toml"
    path.write_text(content)
    return path


def test_custom_filename_rule(tmp_path):
    path = _write_config(
        tmp_path,
        """
[[filename_rules]]
pattern = "*paystub*"
category = "Payroll"
""",
    )

    rules = load_rules(path)

    assert rules.filename_rules == (("*paystub*", "Payroll"),)


def test_custom_extension_rule(tmp_path):
    path = _write_config(
        tmp_path,
        """
[extensions]
".pdf" = "Documents"
""",
    )

    rules = load_rules(path)

    assert rules.extensions[".pdf"] == "Documents"


def test_filename_rule_overrides_extension_rule(tmp_path):
    path = _write_config(
        tmp_path,
        """
[[filename_rules]]
pattern = "*paystub*"
category = "Payroll"

[extensions]
".pdf" = "Documents"
""",
    )

    rules = load_rules(path)

    assert classify_file(Path("march_paystub.pdf"), rules) == "Payroll"


def test_first_matching_filename_rule_wins(tmp_path):
    path = _write_config(
        tmp_path,
        """
[[filename_rules]]
pattern = "*paystub*"
category = "Payroll"

[[filename_rules]]
pattern = "*march*"
category = "Monthly"
""",
    )

    rules = load_rules(path)

    assert classify_file(Path("march_paystub.pdf"), rules) == "Payroll"


def test_matching_remains_case_insensitive(tmp_path):
    path = _write_config(
        tmp_path,
        """
[[filename_rules]]
pattern = "*paystub*"
category = "Payroll"
""",
    )

    rules = load_rules(path)

    assert classify_file(Path("MARCH_PAYSTUB.PDF"), rules) == "Payroll"


def test_missing_config_file_raises_clear_error(tmp_path):
    missing = tmp_path / "does_not_exist.toml"

    with pytest.raises(ConfigError):
        load_rules(missing)


def test_malformed_toml_raises_clear_error(tmp_path):
    path = _write_config(tmp_path, "this is not [ valid toml")

    with pytest.raises(ConfigError):
        load_rules(path)


def test_unsafe_category_containing_forward_slash(tmp_path):
    path = _write_config(
        tmp_path,
        """
[[filename_rules]]
pattern = "*x*"
category = "a/b"
""",
    )

    with pytest.raises(ConfigError):
        load_rules(path)


def test_unsafe_category_containing_backslash(tmp_path):
    path = _write_config(
        tmp_path,
        """
[extensions]
".pdf" = 'a\\b'
""",
    )

    with pytest.raises(ConfigError):
        load_rules(path)


def test_unsafe_category_dotdot(tmp_path):
    path = _write_config(
        tmp_path,
        """
[extensions]
".pdf" = ".."
""",
    )

    with pytest.raises(ConfigError):
        load_rules(path)


def test_empty_category_rejected(tmp_path):
    path = _write_config(
        tmp_path,
        """
[extensions]
".pdf" = ""
""",
    )

    with pytest.raises(ConfigError):
        load_rules(path)


def test_duplicate_extension_keys_rejected(tmp_path):
    # TOML itself forbids a duplicate key in the same table, so this
    # surfaces as a TOMLDecodeError, which load_rules wraps as ConfigError.
    path = _write_config(
        tmp_path,
        """
[extensions]
".pdf" = "Documents"
".pdf" = "Other"
""",
    )

    with pytest.raises(ConfigError):
        load_rules(path)


def test_duplicate_filename_pattern_first_one_wins(tmp_path):
    # Unlike extensions, TOML permits repeating [[filename_rules]]
    # entries with the same pattern; the documented first-match
    # policy resolves the conflict deterministically rather than
    # rejecting the config.
    path = _write_config(
        tmp_path,
        """
[[filename_rules]]
pattern = "*x*"
category = "First"

[[filename_rules]]
pattern = "*x*"
category = "Second"
""",
    )

    rules = load_rules(path)

    assert classify_file(Path("xfile.pdf"), rules) == "First"


def test_missing_sections_mean_empty_not_builtin_defaults(tmp_path):
    path = _write_config(tmp_path, "")

    rules = load_rules(path)

    assert rules.filename_rules == ()
    assert rules.extensions == {}


def test_extension_key_must_start_with_dot(tmp_path):
    path = _write_config(
        tmp_path,
        """
[extensions]
"pdf" = "Documents"
""",
    )

    with pytest.raises(ConfigError):
        load_rules(path)


def test_absolute_path_category_rejected(tmp_path):
    path = _write_config(
        tmp_path,
        """
[extensions]
".pdf" = "/etc/passwd"
""",
    )

    with pytest.raises(ConfigError):
        load_rules(path)


def test_load_rules_does_not_touch_filesystem_beyond_reading(tmp_path):
    path = _write_config(
        tmp_path,
        """
[extensions]
".pdf" = "Documents"
""",
    )
    before = sorted(tmp_path.iterdir())

    load_rules(path)

    assert sorted(tmp_path.iterdir()) == before
