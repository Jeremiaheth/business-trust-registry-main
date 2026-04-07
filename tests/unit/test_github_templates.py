from __future__ import annotations

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ISSUE_TEMPLATE_DIR = PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE"


def test_issue_forms_parse_and_include_required_safety_warnings() -> None:
    warning_text = "do not upload evidence"
    no_personal_data_text = "do not include personal data"
    links_only_text = "use links and hashes only"

    for path in sorted(ISSUE_TEMPLATE_DIR.glob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))

        assert isinstance(data, dict)
        assert isinstance(data.get("body"), list)
        body_text = path.read_text(encoding="utf-8").lower()
        assert warning_text in body_text
        assert no_personal_data_text in body_text
        assert links_only_text in body_text


def test_issue_forms_do_not_define_upload_fields() -> None:
    forbidden_field_types = {"file", "attachment", "upload"}

    for path in sorted(ISSUE_TEMPLATE_DIR.glob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

        body = data.get("body", [])
        assert isinstance(body, list)
        for item in body:
            assert isinstance(item, dict)
            item_type = str(item.get("type", "")).lower()
            assert item_type not in forbidden_field_types


def test_pull_request_template_includes_privacy_and_validation_checks() -> None:
    template_path = PROJECT_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"
    text = template_path.read_text(encoding="utf-8")

    assert "I did not add personal data to the public repo." in text
    assert "`python -m btr_ng.cli lint-copy`" in text
    assert "`python -m btr_ng.cli scan-repo-safety`" in text
