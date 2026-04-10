import type { NormalizedIntakeSubmission } from "./types";

export async function persistSubmission(
  database: D1Database,
  submission: NormalizedIntakeSubmission,
): Promise<void> {
  await database
    .prepare(
      `INSERT INTO intake_submissions (
        submission_id,
        submission_type,
        status,
        created_at,
        updated_at,
        business_reference,
        organization_name,
        contact_name,
        contact_email,
        public_message,
        public_links_json,
        public_hashes_json,
        privacy_consent,
        moderation_notes,
        intake_source
      ) VALUES (?, ?, 'received', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', 'public_web')`,
    )
    .bind(
      submission.submissionId,
      submission.submissionType,
      submission.createdAt,
      submission.updatedAt,
      submission.businessReference,
      submission.organizationName,
      submission.contactName,
      submission.contactEmail,
      submission.publicMessage,
      JSON.stringify(submission.publicLinks),
      JSON.stringify(submission.publicHashes),
      submission.privacyConsent ? 1 : 0,
    )
    .run();
}
