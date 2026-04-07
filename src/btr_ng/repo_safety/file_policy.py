"""File policy checks for the public repository surface."""

from __future__ import annotations

from pathlib import Path

FORBIDDEN_BINARY_EXTENSIONS = frozenset(
    {
        ".bmp",
        ".doc",
        ".docx",
        ".gif",
        ".ico",
        ".jpeg",
        ".jpg",
        ".pdf",
        ".png",
        ".ppt",
        ".pptx",
        ".webp",
        ".xls",
        ".xlsx",
    }
)

ALWAYS_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
    }
)

ALWAYS_SKIP_PREFIXES = (
    Path("tests") / "fixtures",
)

DEFAULT_GENERATED_PREFIXES = (
    Path("build"),
    Path("derived") / "nocopo",
    Path("public"),
    Path("site") / "dist",
)


def iter_repo_files(project_root: Path, include_generated: bool = False) -> tuple[Path, ...]:
    """Return deterministic file paths that should be scanned."""
    if not project_root.exists():
        raise ValueError(f"project root does not exist: {project_root}")
    if not project_root.is_dir():
        raise ValueError(f"project root must be a directory: {project_root}")

    files: list[Path] = []
    for path in sorted(project_root.rglob("*")):
        if not path.is_file():
            continue
        relative_path = path.relative_to(project_root)
        if _should_skip(relative_path, include_generated=include_generated):
            continue
        files.append(path)
    return tuple(files)


def scan_forbidden_file_types(
    project_root: Path,
    include_generated: bool = False,
) -> list[tuple[Path, str]]:
    """Return file-policy issues for forbidden binary extensions."""
    issues: list[tuple[Path, str]] = []
    for path in iter_repo_files(project_root, include_generated=include_generated):
        if path.suffix.lower() in FORBIDDEN_BINARY_EXTENSIONS:
            issues.append(
                (
                    path,
                    f"forbidden file type in public repo: '{path.suffix.lower()}'",
                )
            )
    return issues


def _should_skip(relative_path: Path, include_generated: bool) -> bool:
    if any(part in ALWAYS_SKIP_DIR_NAMES for part in relative_path.parts):
        return True
    if any(
        relative_path == prefix or relative_path.is_relative_to(prefix)
        for prefix in ALWAYS_SKIP_PREFIXES
    ):
        return True
    if include_generated:
        return False
    return any(
        relative_path == prefix or relative_path.is_relative_to(prefix)
        for prefix in DEFAULT_GENERATED_PREFIXES
    )
