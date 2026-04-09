from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
README_PATH = PROJECT_ROOT / "README.md"
DOCS_DIR = PROJECT_ROOT / "docs"
REQUIRED_DOCS = (
    Path("docs/architecture.md"),
    Path("docs/privacy.md"),
    Path("docs/security.md"),
    Path("docs/cloudflare.md"),
    Path("docs/access-matrix.md"),
    Path("docs/moderation.md"),
    Path("docs/disputes.md"),
)
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def test_required_handoff_docs_exist_and_are_linked_from_readme() -> None:
    readme_text = README_PATH.read_text(encoding="utf-8")

    for relative_path in REQUIRED_DOCS:
        absolute_path = PROJECT_ROOT / relative_path
        assert absolute_path.exists()
        assert absolute_path.read_text(encoding="utf-8").strip()
        assert f"]({relative_path.as_posix()})" in readme_text


def test_markdown_docs_local_links_resolve() -> None:
    markdown_paths = [README_PATH, *sorted(DOCS_DIR.glob("*.md"))]

    for source_path in markdown_paths:
        text = source_path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK_PATTERN.findall(text):
            normalized = target.split("#", 1)[0]
            if not normalized:
                continue
            if "://" in normalized or normalized.startswith(("mailto:", "#")):
                continue

            resolved = (source_path.parent / normalized).resolve()
            assert resolved.exists(), f"{source_path}: broken markdown link: {target}"
