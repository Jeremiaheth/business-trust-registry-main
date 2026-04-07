from __future__ import annotations

from cases import (
    CaseValidationError,
    build_sanitized_public_summary,
    create_case,
    export_queue_status,
    transition_case,
)


def test_create_case_accepts_link_only_references() -> None:
    case = create_case(
        {
            "case_id": "CASE-001",
            "kind": "correction",
            "btr_id": "BTR-ACME-001",
            "redacted_summary": "Public-safe redacted summary for correction review.",
            "evidence_references": [
                {"kind": "url", "value": "https://example.com/source"},
                {"kind": "hash", "value": "0123456789abcdef0123456789abcdef"},
            ],
        },
        now="2026-04-07T18:00:00Z",
    )

    assert case.state == "queued"
    assert case.case_id == "CASE-001"
    assert len(case.evidence_references) == 2


def test_transition_case_allows_review_then_resolution() -> None:
    queued_case = create_case(
        {
            "case_id": "CASE-002",
            "kind": "claim",
            "redacted_summary": "Public-safe redacted summary for a claim review.",
            "evidence_references": [
                {"kind": "url", "value": "https://example.com/source"},
            ],
        },
        now="2026-04-07T18:00:00Z",
    )

    under_review_case = transition_case(
        queued_case,
        new_state="under_review",
        updated_at="2026-04-08T10:00:00Z",
    )
    resolved_case = transition_case(
        under_review_case,
        new_state="resolved",
        updated_at="2026-04-09T09:30:00Z",
    )

    assert under_review_case.state == "under_review"
    assert resolved_case.state == "resolved"
    assert resolved_case.updated_at == "2026-04-09T09:30:00Z"


def test_build_sanitized_public_summary_excludes_private_upload_fields() -> None:
    case = create_case(
        {
            "case_id": "CASE-003",
            "kind": "verification",
            "btr_id": "BTR-LAGOON-001",
            "redacted_summary": "Public-safe summary for a verification request.",
            "evidence_references": [
                {"kind": "hash", "value": "0123456789abcdef0123456789abcdef"},
            ],
        },
        now="2026-04-07T18:00:00Z",
    )

    document = build_sanitized_public_summary(case)

    assert document == {
        "public_summary_version": 1,
        "case_id": "CASE-003",
        "kind": "verification",
        "state": "queued",
        "created_at": "2026-04-07T18:00:00Z",
        "updated_at": "2026-04-07T18:00:00Z",
        "btr_id": "BTR-LAGOON-001",
        "redacted_summary": "Public-safe summary for a verification request.",
        "evidence_references": [
            {
                "kind": "hash",
                "value": "0123456789abcdef0123456789abcdef",
            }
        ],
    }


def test_export_queue_status_counts_open_cases() -> None:
    queued_case = create_case(
        {
            "case_id": "CASE-004",
            "kind": "claim",
            "redacted_summary": "Public-safe summary for an open claim case.",
            "evidence_references": [
                {"kind": "url", "value": "https://example.com/claim"},
            ],
        },
        now="2026-04-05T12:00:00Z",
    )
    resolved_case = transition_case(
        create_case(
            {
                "case_id": "CASE-005",
                "kind": "verification",
                "redacted_summary": "Public-safe summary for a closed verification case.",
                "evidence_references": [
                    {"kind": "url", "value": "https://example.com/verification"},
                ],
            },
            now="2026-04-06T12:00:00Z",
        ),
        new_state="resolved",
        updated_at="2026-04-07T08:00:00Z",
    )

    snapshot = export_queue_status(
        [queued_case, resolved_case],
        generated_at="2026-04-07T18:00:00Z",
    )

    assert snapshot.open_case_count == 1
    assert snapshot.oldest_open_age_days == 2
    assert snapshot.open_counts == {
        "claims": 1,
        "corrections": 0,
        "verifications": 0,
    }
    assert snapshot.states == {"queued": 1}


def test_disallowed_fields_are_rejected() -> None:
    try:
        create_case(
            {
                "case_id": "CASE-006",
                "kind": "claim",
                "redacted_summary": "Public-safe summary for a rejected intake.",
                "attachments": ["evidence.pdf"],
                "evidence_references": [
                    {"kind": "url", "value": "https://example.com/source"},
                ],
            },
            now="2026-04-07T18:00:00Z",
        )
    except CaseValidationError as error:
        assert str(error) == "attachments is not accepted in the private lane"
    else:
        raise AssertionError("expected attachments to be rejected")
