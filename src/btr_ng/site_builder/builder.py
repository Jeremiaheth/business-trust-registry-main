"""Render the static public site from generated API artifacts."""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape


class SiteBuildError(ValueError):
    """Raised when the static site cannot be rendered safely."""


def build_site(
    api_dir: Path,
    out_dir: Path,
    template_dir: Path,
    static_dir: Path,
) -> int:
    """Render the public beta site from static API artifacts."""
    index_document = _load_json_object(api_dir / "index.json")
    _load_json_object(api_dir / "search.json")
    business_documents = _load_business_documents(api_dir / "businesses")

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    page_count = 0
    out_dir.mkdir(parents=True, exist_ok=True)
    _copy_static_assets(static_dir, out_dir / "static")

    home_context = {
        "title": "BTR-NG",
        "page_name": "home",
        "root_prefix": "",
        "asset_prefix": "static/",
        "api_prefix": "api/v1/",
        "generated_at": str(index_document["generated_at"]),
        "items": cast(list[dict[str, object]], index_document["items"]),
    }
    _render_template(env, "home.html", out_dir / "index.html", home_context)
    page_count += 1

    search_context = {
        "title": "Search",
        "page_name": "search",
        "root_prefix": "../",
        "asset_prefix": "../static/",
        "api_prefix": "../api/v1/",
        "generated_at": str(index_document["generated_at"]),
        "items": cast(list[dict[str, object]], index_document["items"]),
    }
    _render_template(env, "search.html", out_dir / "search" / "index.html", search_context)
    page_count += 1

    for business_document in business_documents:
        btr_id = str(business_document["btr_id"])
        profile = cast(dict[str, object], business_document["profile"])
        score = cast(dict[str, object], business_document["score"])
        profile_context = {
            "title": str(profile["legal_name"]),
            "page_name": "profile",
            "root_prefix": "../../",
            "asset_prefix": "../../static/",
            "api_prefix": "../../api/v1/",
            "generated_at": str(business_document["generated_at"]),
            "business": business_document,
            "profile": profile,
            "score": score,
            "evidence": cast(list[dict[str, object]], business_document["evidence"]),
            "disputes": cast(list[dict[str, object]], business_document["disputes"]),
            "derived_records": cast(
                list[dict[str, object]], business_document.get("derived_records", [])
            ),
            "banner_label": _banner_label(str(score["display_state"])),
        }
        _render_template(
            env,
            "profile.html",
            out_dir / "businesses" / btr_id / "index.html",
            profile_context,
        )
        page_count += 1

    not_found_context = {
        "title": "Not Found",
        "page_name": "not-found",
        "root_prefix": "",
        "asset_prefix": "static/",
        "api_prefix": "api/v1/",
        "generated_at": str(index_document["generated_at"]),
    }
    _render_template(env, "404.html", out_dir / "404.html", not_found_context)
    page_count += 1

    return page_count


def _load_business_documents(directory: Path) -> tuple[dict[str, object], ...]:
    if not directory.exists():
        raise SiteBuildError(f"business API directory does not exist: {directory}")
    if not directory.is_dir():
        raise SiteBuildError(f"business API path must be a directory: {directory}")

    documents: list[dict[str, object]] = []
    for file_path in sorted(directory.glob("*.json")):
        documents.append(_load_json_object(file_path))
    if not documents:
        raise SiteBuildError(f"no business API documents found in {directory}")
    return tuple(documents)


def _copy_static_assets(source_dir: Path, destination_dir: Path) -> None:
    if not source_dir.exists():
        raise SiteBuildError(f"static asset directory does not exist: {source_dir}")
    if not source_dir.is_dir():
        raise SiteBuildError(f"static asset path must be a directory: {source_dir}")
    shutil.copytree(source_dir, destination_dir, dirs_exist_ok=True)


def _render_template(
    env: Environment,
    template_name: str,
    output_path: Path,
    context: Mapping[str, object],
) -> None:
    template = env.get_template(template_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(template.render(**context), encoding="utf-8")


def _load_json_object(file_path: Path) -> dict[str, object]:
    if not file_path.exists():
        raise SiteBuildError(f"missing required API artifact: {file_path}")
    try:
        document = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SiteBuildError(f"{file_path}: invalid JSON: {error.msg}") from error

    if not isinstance(document, dict):
        raise SiteBuildError(f"{file_path}: expected a top-level JSON object")
    return cast(dict[str, object], document)


def _banner_label(display_state: str) -> str:
    labels = {
        "normal": "Published profile",
        "insufficient_evidence": "Insufficient evidence",
        "under_review": "Under review",
        "maintenance": "Maintenance mode",
    }
    return labels.get(display_state, "Profile status")
