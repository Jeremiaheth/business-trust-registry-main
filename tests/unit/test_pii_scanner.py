from __future__ import annotations

from pathlib import Path

import pytest

from btr_ng.repo_safety.pii_scanner import RepoSafetyError, scan_repo_safety

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOOD_FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "pii_good"
BAD_FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "pii_bad"


def test_repo_safety_rejects_obvious_pii_and_forbidden_file_types() -> None:
    with pytest.raises(RepoSafetyError) as error:
        scan_repo_safety(BAD_FIXTURE_DIR)

    message = str(error.value)
    assert "possible phone number detected" in message
    assert "personal email address detected" in message
    assert "sensitive identity label detected" in message
    assert "identity-document keyword detected" in message
    assert "forbidden file type in public repo: '.pdf'" in message


def test_repo_safety_accepts_safe_fixture_tree() -> None:
    scanned_files = scan_repo_safety(GOOD_FIXTURE_DIR)

    assert scanned_files == 2


def test_project_repo_passes_repo_safety_scan() -> None:
    scanned_files = scan_repo_safety(PROJECT_ROOT)

    assert scanned_files > 0
