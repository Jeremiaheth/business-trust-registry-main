from __future__ import annotations

import pytest

from btr_ng.schema import (
    SchemaValidationError,
    iter_schema_names,
    load_schema,
    load_validator,
    validate_document,
)

VALID_DOCUMENTS = {
    "business-record": {
        "btr_id": "BTR-ACME-001",
        "legal_name": "Acme Procurement Services Ltd",
        "jurisdiction": "NG",
        "identifiers": {
            "primary": "RC-123456"
        },
        "public_links": [
            "https://example.com/acme"
        ],
        "evidence_refs": [
            "EVID-ACME-001"
        ],
        "derived_signals": {
            "procurement_activity": True,
            "manual_verification": False,
            "flags": [
                "public-procurement-footprint"
            ]
        },
        "record_state": "active",
        "updated_at": "2026-04-07T10:00:00Z"
    },
    "evidence-item": {
        "evidence_id": "EVID-ACME-001",
        "source_url": "https://example.com/evidence/acme",
        "source_type": "procurement_notice",
        "observed_at": "2026-04-06T10:00:00Z",
        "recorded_at": "2026-04-07T10:00:00Z",
        "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "access": "public_reference",
        "summary": "Procurement award notice referencing the supplier.",
        "related_businesses": [
            "BTR-ACME-001"
        ],
        "tags": [
            "procurement"
        ]
    },
    "trust-score": {
        "btr_id": "BTR-ACME-001",
        "score": 0.73,
        "confidence": 0.81,
        "band": "high",
        "status": "published",
        "display_state": "normal",
        "evidence_count": 4,
        "generated_at": "2026-04-07T10:00:00Z",
        "verification_timestamp": "2026-04-07T10:00:00Z",
        "public_note": "Based on available verified evidence.",
        "explanation": {
            "top_positive_signals": [
                "repeat procurement activity"
            ],
            "top_negative_signals": [
                "limited manual verification"
            ]
        }
    },
    "dispute-record": {
        "case_id": "CASE-ACME-001",
        "btr_id": "BTR-ACME-001",
        "review_type": "fact_correction",
        "state": "under_review",
        "redacted_summary": "Business requested correction of a public metadata field.",
        "evidence_pack_refs": [
            "PACK-ACME-001"
        ],
        "opened_at": "2026-04-07T10:00:00Z",
        "updated_at": "2026-04-07T12:00:00Z"
    },
    "queue-status": {
        "generated_at": "2026-04-07T10:00:00Z",
        "mode": "normal",
        "stale": False,
        "open_counts": {
            "claims": 1,
            "corrections": 2,
            "disputes": 0,
            "verifications": 0
        }
    },
    "privacy-posture": {
        "public_repo_accepts_personal_data": False,
        "public_repo_accepts_evidence_uploads": False,
        "public_repo_accepts_public_disputes": False,
        "allowed_public_submission_kinds": [
            "claim_business",
            "correct_public_metadata"
        ],
        "private_lane_status": "deferred"
    }
}

INVALID_DOCUMENTS = {
    "business-record": (
        {
            "btr_id": "BTR-ACME-001",
            "legal_name": "Acme Procurement Services Ltd",
            "jurisdiction": "NG",
            "identifiers": {
                "primary": "RC-123456"
            },
            "public_links": [
                "https://example.com/acme"
            ],
            "evidence_refs": [
                "wrong-evidence-id"
            ],
            "derived_signals": {
                "procurement_activity": True,
                "manual_verification": False,
                "flags": []
            },
            "record_state": "active",
            "updated_at": "2026-04-07T10:00:00Z"
        },
        "evidence_refs.0"
    ),
    "evidence-item": (
        {
            "evidence_id": "EVID-ACME-001",
            "source_url": "https://example.com/evidence/acme",
            "source_type": "procurement_notice",
            "observed_at": "2026-04-06T10:00:00Z",
            "recorded_at": "2026-04-07T10:00:00Z",
            "sha256": "short",
            "access": "public_reference",
            "summary": "Procurement award notice referencing the supplier."
        },
        "sha256"
    ),
    "trust-score": (
        {
            "btr_id": "BTR-ACME-001",
            "score": 1.2,
            "confidence": 0.81,
            "band": "high",
            "status": "published",
            "display_state": "normal",
            "evidence_count": 4,
            "generated_at": "2026-04-07T10:00:00Z",
            "verification_timestamp": "2026-04-07T10:00:00Z",
            "public_note": "Based on available verified evidence.",
            "explanation": {
                "top_positive_signals": [
                    "repeat procurement activity"
                ],
                "top_negative_signals": []
            }
        },
        "score"
    ),
    "dispute-record": (
        {
            "case_id": "CASE-ACME-001",
            "btr_id": "BTR-ACME-001",
            "review_type": "fact_correction",
            "state": "under_review",
            "redacted_summary": "Business requested correction of a public metadata field.",
            "evidence_pack_refs": [
                "PACK-ACME-001"
            ],
            "opened_at": "2026-04-07T10:00:00Z",
            "updated_at": "2026-04-07T12:00:00Z",
            "raw_evidence_blob": "forbidden"
        },
        "$"
    ),
    "queue-status": (
        {
            "generated_at": "2026-04-07T10:00:00Z",
            "mode": "broken",
            "stale": False,
            "open_counts": {
                "claims": 1,
                "corrections": 2,
                "disputes": 0,
                "verifications": 0
            }
        },
        "mode"
    ),
    "privacy-posture": (
        {
            "public_repo_accepts_personal_data": False,
            "public_repo_accepts_evidence_uploads": False,
            "public_repo_accepts_public_disputes": False,
            "allowed_public_submission_kinds": [],
            "private_lane_status": "deferred"
        },
        "allowed_public_submission_kinds"
    )
}


def test_all_canonical_schemas_compile() -> None:
    for schema_name in iter_schema_names():
        schema = load_schema(schema_name)
        validator = load_validator(schema_name)

        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert validator.schema["title"]


@pytest.mark.parametrize(("schema_name", "document"), VALID_DOCUMENTS.items())
def test_minimal_valid_documents_pass(
    schema_name: str,
    document: dict[str, object],
) -> None:
    validate_document(schema_name, document)


@pytest.mark.parametrize(
    ("schema_name", "document", "expected_path"),
    [
        (schema_name, document, expected_path)
        for schema_name, (document, expected_path) in INVALID_DOCUMENTS.items()
    ],
)
def test_invalid_documents_fail_with_actionable_path(
    schema_name: str,
    document: dict[str, object],
    expected_path: str,
) -> None:
    with pytest.raises(SchemaValidationError) as error:
        validate_document(schema_name, document)

    assert any(expected_path in issue for issue in error.value.issues)
