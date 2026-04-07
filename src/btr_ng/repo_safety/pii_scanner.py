"""PII and public-upload scanner for the repository."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from btr_ng.repo_safety.file_policy import (
    FORBIDDEN_BINARY_EXTENSIONS,
    iter_repo_files,
    scan_forbidden_file_types,
)

PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?234[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}|0\d{10})(?!\d)",
    re.IGNORECASE,
)
BVN_NIN_PATTERN = re.compile(r"\b(?:BVN|NIN)\b", re.IGNORECASE)
PERSONAL_EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@(?:gmail\.com|yahoo\.com|hotmail\.com|outlook\.com|protonmail\.com|proton\.me)\b",
    re.IGNORECASE,
)
IDENTITY_KEYWORD_PATTERN = re.compile(
    r"\b(?:signature|signed by|passport|driver'?s license|national id|id card)\b",
    re.IGNORECASE,
)
TEXT_SCAN_EXTENSIONS = frozenset(
    {
        ".css",
        ".gitignore",
        ".html",
        ".js",
        ".json",
        ".md",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)


@dataclass(frozen=True, slots=True)
class RepoSafetyIssue:
    """A single repository safety issue."""

    file_path: Path
    message: str

    def render(self) -> str:
        """Return a stable user-facing issue string."""
        return f"{self.file_path}: {self.message}"


class RepoSafetyError(ValueError):
    """Raised when the repo contains public-safety violations."""

    def __init__(self, issues: list[RepoSafetyIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("; ".join(issue.render() for issue in issues))


def scan_repo_safety(project_root: Path, include_generated: bool = False) -> int:
    """Scan the repository for obvious PII and forbidden public-upload types."""
    issues: list[RepoSafetyIssue] = [
        RepoSafetyIssue(path, message)
        for path, message in scan_forbidden_file_types(
            project_root,
            include_generated=include_generated,
        )
    ]

    files = iter_repo_files(project_root, include_generated=include_generated)
    for path in files:
        if path.suffix.lower() in FORBIDDEN_BINARY_EXTENSIONS:
            continue
        if not _should_scan_text(path):
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        issues.extend(_scan_text_file(path, text))

    if issues:
        raise RepoSafetyError(issues)
    return len(files)


def _should_scan_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SCAN_EXTENSIONS or path.name in {"Makefile", "LICENSE"}


def _scan_text_file(file_path: Path, text: str) -> list[RepoSafetyIssue]:
    patterns = (
        (PHONE_PATTERN, "possible phone number detected"),
        (BVN_NIN_PATTERN, "sensitive identity label detected"),
        (PERSONAL_EMAIL_PATTERN, "personal email address detected"),
        (IDENTITY_KEYWORD_PATTERN, "identity-document keyword detected"),
    )

    issues: list[RepoSafetyIssue] = []
    for pattern, message in patterns:
        match = pattern.search(text)
        if match is None:
            continue
        issues.append(
            RepoSafetyIssue(
                file_path,
                f"{message}: '{match.group(0)}'",
            )
        )
    return issues
