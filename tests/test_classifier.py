from pathlib import Path
from types import MappingProxyType

from organizer.classifier import (
    ClassificationRules,
    classify_extension,
    classify_file,
    classify_filename,
)


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


def test_statement_filename_rule_classifies_as_finance():
    assert classify_file(Path("WellsFargo_Statement_August.pdf")) == "Finance"
    assert classify_file(Path("bank_statement.pdf")) == "Finance"


def test_invoice_filename_rule_classifies_as_finance():
    assert classify_file(Path("UNC_Tuition_Invoice.pdf")) == "Finance"


def test_receipt_filename_rule_classifies_as_finance():
    assert classify_file(Path("store_receipt.pdf")) == "Finance"


def test_homework_filename_rule_classifies_as_school():
    assert classify_file(Path("math_homework.docx")) == "School"


def test_assignment_filename_rule_classifies_as_school():
    assert classify_file(Path("essay_assignment.docx")) == "School"


def test_tuition_filename_rule_classifies_as_school():
    assert classify_file(Path("tuition_reminder.pdf")) == "School"
    assert classify_filename("fall_tuition_plan.pdf") == "School"


def test_resume_filename_rule_classifies_as_resumes():
    assert classify_file(Path("resume_joseph.pdf")) == "Resumes"
    assert classify_file(Path("resume_final.docx")) == "Resumes"


def test_cv_filename_rule_classifies_as_resumes():
    assert classify_file(Path("my_cv.pdf")) == "Resumes"


def test_filename_rule_matching_is_case_insensitive():
    assert classify_file(Path("BANK_STATEMENT.PDF")) == "Finance"
    assert classify_file(Path("Resume_Final.DOCX")) == "Resumes"


def test_filename_rules_override_extension_classification():
    # vacation_invoice_photo.jpg would classify as Images by extension,
    # but the "*invoice*" filename rule takes precedence.
    assert classify_file(Path("vacation_invoice_photo.jpg")) == "Finance"


def test_extension_classification_still_works_when_no_filename_rule_matches():
    assert classify_file(Path("photo.jpg")) == "Images"


def test_unknown_file_still_returns_other():
    assert classify_file(Path("unknown.xyz")) == "Other"


def test_multiple_matching_filename_rules_use_first_match_priority():
    # "statement" and "invoice" both appear; "*statement*" is listed
    # first in FILENAME_RULES, so it wins even though "*invoice*" also
    # matches. This documents the deterministic first-match policy.
    assert classify_filename("invoice_statement_combo.pdf") == "Finance"


def test_tuition_invoice_follows_documented_rule_order():
    # "*invoice*" (Finance) is listed before "*tuition*" (School) in
    # FILENAME_RULES, so a filename matching both resolves to Finance.
    assert classify_file(Path("tuition_invoice.pdf")) == "Finance"


def test_filename_rules_match_filename_only_not_parent_directory():
    # The parent directory is named "Finance", but the filename itself
    # ("photo.jpg") matches no filename rule, so it must still fall
    # back to extension-based classification (Images), not inherit
    # "Finance" from the directory name.
    assert classify_file(Path("Finance") / "photo.jpg") == "Images"


def test_classify_filename_returns_none_when_no_rule_matches():
    assert classify_filename("photo.jpg") is None


def test_classify_file_uses_default_rules_when_none_supplied():
    # No config file means no `rules` argument is passed by callers
    # such as plan_moves(); classify_file()'s default parameter value
    # must reproduce the exact built-in behavior.
    assert classify_file(Path("bank_statement.pdf")) == "Finance"
    assert classify_file(Path("photo.jpg")) == "Images"


def test_classify_file_accepts_custom_rules_object():
    custom_rules = ClassificationRules(
        filename_rules=(("*paystub*", "Payroll"),),
        extensions=MappingProxyType({".pdf": "Legal"}),
    )

    assert classify_file(Path("march_paystub.pdf"), custom_rules) == "Payroll"
    assert classify_file(Path("contract.pdf"), custom_rules) == "Legal"
    assert classify_file(Path("contract.pdf")) == "Documents"
