from __future__ import annotations

from pathlib import Path

import pytest

from btr_ng.repo_safety.copy_linter import CopyLintError, lint_copy_paths, lint_project_copy

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_copy_linter_rejects_forbidden_phrase(tmp_path: Path) -> None:
    target = tmp_path / "bad.md"
    target.write_text("This document publishes an official rating.\n", encoding="utf-8")

    with pytest.raises(CopyLintError) as error:
        lint_copy_paths((target,))

    assert "forbidden phrase found: 'official rating'" in str(error.value)


def test_copy_linter_accepts_approved_copy(tmp_path: Path) -> None:
    target = tmp_path / "good.md"
    target.write_text(
        (
            "This evidence dossier is based on available verified evidence.\n"
            "Confidence indicates evidence completeness.\n"
        ),
        encoding="utf-8",
    )

    lint_copy_paths((target,))


def test_project_copy_targets_pass_default_lint() -> None:
    linted_paths = lint_project_copy(PROJECT_ROOT)

    assert PROJECT_ROOT / "docs" / "public-language-charter.md" in linted_paths
    assert PROJECT_ROOT / "docs" / "architecture.md" in linted_paths
    assert PROJECT_ROOT / "site" / "templates" / "base.html" in linted_paths
