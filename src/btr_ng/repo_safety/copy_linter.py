"""Copy linter for public-facing language discipline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

FORBIDDEN_PHRASES = (
    "certified",
    "guaranteed",
    "verified by government",
    "official rating",
    "trusted business",
    "fraudulent",
)

PREFERRED_PHRASES = (
    "evidence dossier",
    "time-stamped verification event",
    "derived from published procurement data",
    "based on available verified evidence",
    "confidence indicates evidence completeness",
)

DEFAULT_COPY_TARGETS = (
    Path("README.md"),
    Path("docs") / "architecture.md",
    Path("docs") / "privacy.md",
    Path("docs") / "security.md",
    Path("docs") / "access-matrix.md",
    Path("docs") / "moderation.md",
    Path("docs") / "disputes.md",
    Path("docs") / "public-language-charter.md",
    Path("site") / "templates" / "base.html",
    Path("site") / "templates" / "home.html",
    Path("site") / "templates" / "search.html",
    Path("site") / "templates" / "profile.html",
    Path("site") / "templates" / "404.html",
    Path("frontend") / "src" / "components" / "Layout.tsx",
    Path("frontend") / "src" / "pages" / "HomePage.tsx",
    Path("frontend") / "src" / "pages" / "AboutPage.tsx",
    Path("frontend") / "src" / "pages" / "BusinessProfilePage.tsx",
    Path("frontend") / "src" / "pages" / "ContactPage.tsx",
)
CHARTER_RELATIVE_PATH = Path("docs") / "public-language-charter.md"


@dataclass(frozen=True, slots=True)
class CopyLintIssue:
    """A single copy linting issue."""

    file_path: Path
    message: str

    def render(self) -> str:
        """Return a stable user-facing error line."""
        return f"{self.file_path}: {self.message}"


class CopyLintError(ValueError):
    """Raised when public-facing copy violates the language charter."""

    def __init__(self, issues: list[CopyLintIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("; ".join(issue.render() for issue in issues))


def lint_project_copy(project_root: Path) -> tuple[Path, ...]:
    """Lint the default public-facing copy targets under a project root."""
    targets = tuple(project_root / relative_path for relative_path in DEFAULT_COPY_TARGETS)
    required_phrases = {
        project_root / CHARTER_RELATIVE_PATH: PREFERRED_PHRASES,
        project_root / "site" / "templates" / "base.html": (
            "Scores are decision support only.",
            "confidence indicates evidence completeness",
        ),
        project_root / "frontend" / "src" / "components" / "Layout.tsx": (
            "confidence indicates evidence completeness",
            "government certification",
        ),
        project_root / "frontend" / "src" / "pages" / "AboutPage.tsx": (
            "civic-tech registry",
            "confidence indicates evidence completeness",
        ),
    }
    lint_copy_paths(targets, required_phrases)
    return targets


def lint_copy_paths(
    paths: tuple[Path, ...],
    required_phrases_by_path: Mapping[Path, tuple[str, ...]] | None = None,
) -> None:
    """Lint the provided paths for forbidden copy and required disclaimers."""
    required_phrases = required_phrases_by_path or {}
    issues: list[CopyLintIssue] = []

    for path in paths:
        if not path.exists():
            issues.append(CopyLintIssue(path, "required copy target is missing"))
            continue
        if not path.is_file():
            issues.append(CopyLintIssue(path, "copy target must be a regular file"))
            continue

        text = path.read_text(encoding="utf-8")
        lowered = text.lower()

        if path.name != CHARTER_RELATIVE_PATH.name:
            for phrase in FORBIDDEN_PHRASES:
                if phrase in lowered:
                    issues.append(
                        CopyLintIssue(
                            path,
                            f"forbidden phrase found: '{phrase}'",
                        )
                    )

        for phrase in required_phrases.get(path, ()):
            if phrase.lower() not in lowered:
                issues.append(
                    CopyLintIssue(
                        path,
                        f"required phrase missing: '{phrase}'",
                    )
                )

    if issues:
        raise CopyLintError(issues)
