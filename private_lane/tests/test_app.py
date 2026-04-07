from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from app import IntakeValidationError, handle_http_request, validate_intake_payload
from entry import Default


def test_validate_intake_payload_accepts_link_only_payload() -> None:
    document = validate_intake_payload(
        {
            "submission_id": "INTAKE-001",
            "business_reference": "BTR-ACME-001",
            "references": [
                {"kind": "url", "value": "https://example.com/public-source"},
                {"kind": "hash", "value": "0123456789abcdef0123456789abcdef"},
                {
                    "kind": "redacted_summary",
                    "value": "Redacted public-safe summary for initial review.",
                },
            ],
        }
    )

    assert document["submission_id"] == "INTAKE-001"
    assert document["business_reference"] == "BTR-ACME-001"
    assert len(document["references"]) == 3


def test_validate_intake_payload_rejects_binary_upload_fields() -> None:
    try:
        validate_intake_payload(
            {
                "submission_id": "INTAKE-002",
                "business_reference": "BTR-ACME-001",
                "attachments": ["evidence.pdf"],
                "references": [
                    {"kind": "url", "value": "https://example.com/public-source"},
                ],
            }
        )
    except IntakeValidationError as error:
        assert error.issues[0].render() == (
            "attachments: binary evidence uploads are not accepted in the private-lane skeleton"
        )
    else:
        raise AssertionError("expected link-only validation to reject attachment fields")


def test_intake_validation_route_returns_errors_for_invalid_payload() -> None:
    response = handle_http_request(
        method="POST",
        path="/intake/validate",
        body_text=json.dumps(
            {
                "submission_id": "",
                "business_reference": "BTR-ACME-001",
                "references": [],
            }
        ),
    )

    assert response.status == 400
    document = json.loads(response.body)
    assert document["accepted"] is False
    assert document["error"] == "validation_failed"
    assert "submission_id: must be a non-empty string" in document["issues"]


def test_health_endpoint_smoke() -> None:
    response = handle_http_request(method="GET", path="/health")

    assert response.status == 200
    document = json.loads(response.body)
    assert document == {
        "intake_mode": "link_only",
        "service": "btr-ng-private-lane",
        "status": "ok",
    }


def test_worker_entrypoint_routes_health_requests() -> None:
    @dataclass
    class FakeRequest:
        method: str
        url: str

        async def text(self) -> str:
            return ""

    response = asyncio.run(
        Default().fetch(FakeRequest(method="GET", url="https://example.com/health"))
    )

    assert response.status == 200
    assert '"status": "ok"' in response.body
