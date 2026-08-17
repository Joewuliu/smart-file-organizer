from pathlib import Path

from organizer.classifier import classify_extension, classify_file


def test_documents_category():
    for ext in [".pdf", ".doc", ".docx", ".txt", ".rtf"]:
        assert classify_extension(ext) == "Documents"


def test_images_category():
    for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        assert classify_extension(ext) == "Images"


def test_spreadsheets_category():
    for ext in [".xlsx", ".xls", ".csv"]:
        assert classify_extension(ext) == "Spreadsheets"


def test_videos_category():
    for ext in [".mp4", ".mov", ".avi", ".mkv"]:
        assert classify_extension(ext) == "Videos"


def test_audio_category():
    for ext in [".mp3", ".wav", ".m4a"]:
        assert classify_extension(ext) == "Audio"


def test_archives_category():
    for ext in [".zip", ".tar", ".gz", ".7z"]:
        assert classify_extension(ext) == "Archives"


def test_code_category():
    for ext in [".py", ".js", ".ts", ".java", ".cpp", ".c", ".html", ".css", ".json"]:
        assert classify_extension(ext) == "Code"


def test_unknown_extension_returns_other():
    assert classify_extension(".xyz") == "Other"
    assert classify_extension(".unknown") == "Other"


def test_no_extension_returns_other():
    assert classify_file(Path("README")) == "Other"
    assert classify_extension("") == "Other"


def test_uppercase_extension_is_case_insensitive():
    assert classify_file(Path("PHOTO.JPG")) == "Images"
    assert classify_file(Path("REPORT.PDF")) == "Documents"


def test_mixed_case_extension_is_case_insensitive():
    assert classify_extension(".Mp3") == "Audio"
    assert classify_extension(".Zip") == "Archives"


def test_compound_extension_uses_final_suffix():
    assert classify_file(Path("archive.tar.gz")) == "Archives"


def test_classify_file_uses_path_suffix():
    assert classify_file(Path("notes.docx")) == "Documents"
    assert classify_file(Path("video.mkv")) == "Videos"


def test_classifier_does_not_touch_filesystem(tmp_path):
    # No file is created on disk; classification is purely string-based.
    missing_file = tmp_path / "does_not_exist.pdf"
    assert classify_file(missing_file) == "Documents"
    assert not missing_file.exists()
