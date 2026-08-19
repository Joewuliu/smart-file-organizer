import pytest

from organizer.scanner import scan_directory


def test_empty_directory_returns_empty_list(tmp_path):
    assert scan_directory(tmp_path) == []


def test_files_are_returned(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.jpg").write_text("b")

    result = scan_directory(tmp_path)

    assert result == [tmp_path / "a.txt", tmp_path / "b.jpg"]


def test_subdirectories_are_ignored(tmp_path):
    (tmp_path / "file.txt").write_text("data")
    (tmp_path / "subdir").mkdir()

    result = scan_directory(tmp_path)

    assert result == [tmp_path / "file.txt"]


def test_files_inside_subdirectories_are_not_scanned(tmp_path):
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "nested.txt").write_text("data")
    (tmp_path / "top_level.txt").write_text("data")

    result = scan_directory(tmp_path)

    assert result == [tmp_path / "top_level.txt"]


def test_symlinks_are_skipped(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("data")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Platform/user does not support creating symlinks")

    result = scan_directory(tmp_path)

    assert result == [target]


@pytest.mark.parametrize(
    "filename", ["desktop.ini", "Thumbs.db", ".DS_Store", "DESKTOP.INI", "thumbs.DB"]
)
def test_system_files_are_skipped(tmp_path, filename):
    (tmp_path / filename).write_text("system")
    (tmp_path / "keep.txt").write_text("keep")

    result = scan_directory(tmp_path)

    assert result == [tmp_path / "keep.txt"]


def test_results_are_sorted_alphabetically_case_insensitive(tmp_path):
    (tmp_path / "banana.txt").write_text("b")
    (tmp_path / "Apple.txt").write_text("a")
    (tmp_path / "cherry.txt").write_text("c")

    result = scan_directory(tmp_path)

    assert [p.name for p in result] == ["Apple.txt", "banana.txt", "cherry.txt"]


def test_missing_directory_raises_file_not_found_error(tmp_path):
    missing = tmp_path / "does_not_exist"

    with pytest.raises(FileNotFoundError):
        scan_directory(missing)


def test_path_that_is_a_file_raises_not_a_directory_error(tmp_path):
    file_path = tmp_path / "not_a_dir.txt"
    file_path.write_text("data")

    with pytest.raises(NotADirectoryError):
        scan_directory(file_path)


def test_scan_does_not_modify_filesystem(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "subdir").mkdir()

    scan_directory(tmp_path)

    children = sorted(p.name for p in tmp_path.iterdir())
    assert children == ["a.txt", "subdir"]


# --- Milestone 11: recursive scanning ---


def test_default_scan_remains_non_recursive(tmp_path):
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "nested.txt").write_text("data")
    (tmp_path / "top_level.txt").write_text("data")

    result = scan_directory(tmp_path)

    assert result == [tmp_path / "top_level.txt"]


def test_recursive_scan_finds_nested_files(tmp_path):
    subdir = tmp_path / "Personal"
    subdir.mkdir()
    (subdir / "photo.jpg").write_text("data")
    (tmp_path / "loose.pdf").write_text("data")

    result = scan_directory(tmp_path, recursive=True)

    assert result == [tmp_path / "loose.pdf", subdir / "photo.jpg"]


def test_recursive_scan_returns_only_files_never_directories(tmp_path):
    subdir = tmp_path / "Personal" / "Deeper"
    subdir.mkdir(parents=True)
    (subdir / "notes.txt").write_text("data")

    result = scan_directory(tmp_path, recursive=True)

    assert all(p.is_file() for p in result)
    assert result == [subdir / "notes.txt"]


def test_recursive_scan_does_not_follow_directory_symlinks(tmp_path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "hidden.txt").write_text("data")
    link_dir = tmp_path / "link"
    try:
        link_dir.symlink_to(real_dir, target_is_directory=True)
    except OSError:
        pytest.skip("Platform/user does not support creating symlinks")

    result = scan_directory(tmp_path, recursive=True)

    assert result == [real_dir / "hidden.txt"]


def test_recursive_scan_skips_file_symlinks(tmp_path):
    subdir = tmp_path / "Personal"
    subdir.mkdir()
    target = subdir / "target.txt"
    target.write_text("data")
    link = subdir / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Platform/user does not support creating symlinks")

    result = scan_directory(tmp_path, recursive=True)

    assert result == [target]


def test_recursive_scan_skips_nested_system_files(tmp_path):
    subdir = tmp_path / "Personal"
    subdir.mkdir()
    (subdir / "desktop.ini").write_text("system")
    (subdir / "Thumbs.db").write_text("system")
    (subdir / "keep.txt").write_text("keep")

    result = scan_directory(tmp_path, recursive=True)

    assert result == [subdir / "keep.txt"]


def test_recursive_scan_ordering_is_deterministic_by_relative_path(tmp_path):
    (tmp_path / "zzz.txt").write_text("data")
    personal = tmp_path / "Personal"
    personal.mkdir()
    (personal / "aaa.txt").write_text("data")
    work = tmp_path / "Work"
    work.mkdir()
    (work / "bbb.txt").write_text("data")

    result = scan_directory(tmp_path, recursive=True)

    assert result == [personal / "aaa.txt", work / "bbb.txt", tmp_path / "zzz.txt"]


def test_recursive_scan_excludes_directories_matched_by_predicate(tmp_path):
    excluded = tmp_path / "Documents"
    excluded.mkdir()
    (excluded / "report.pdf").write_text("already organized")
    included = tmp_path / "Personal"
    included.mkdir()
    (included / "notes.txt").write_text("data")

    result = scan_directory(
        tmp_path,
        recursive=True,
        exclude_dir=lambda rel: rel.parts == ("Documents",),
    )

    assert result == [included / "notes.txt"]


def test_recursive_scan_does_not_modify_filesystem(tmp_path):
    subdir = tmp_path / "Personal"
    subdir.mkdir()
    (subdir / "notes.txt").write_text("data")

    scan_directory(tmp_path, recursive=True)

    assert (subdir / "notes.txt").exists()
    assert (subdir / "notes.txt").read_text() == "data"
