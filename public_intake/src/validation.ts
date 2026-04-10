import type {
  IntakePayload,
  NormalizedIntakeSubmission,
  SubmissionType,
  ValidationOutcome,
} from "./types";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function trimString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function normalizeList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => trimString(item))
    .filter((item) => item.length > 0);
}

function buildSubmissionId(now: Date): string {
  return `INT-${now.toISOString().slice(0, 10).replaceAll("-", "")}-${crypto
    .randomUUID()
    .slice(0, 8)
    .toUpperCase()}`;
}

export function validateIntakePayload(
  type: SubmissionType,
  payload: IntakePayload,
  now: Date = new Date(),
): ValidationOutcome {
  if (payload.attachments !== undefined) {
    return {
      ok: false,
      error: "Attachments are not accepted in the public beta. Submit public links or hashes only.",
      status: 400
    };
  }

  const contactName = trimString(payload.contact_name);
  const contactEmail = trimString(payload.contact_email);
  const message = trimString(payload.message);
  const businessReference = trimString(payload.business_reference);
  const organizationName = trimString(payload.organization_name);
  const publicLinks = normalizeList(payload.public_links);
  const publicHashes = normalizeList(payload.public_hashes);

  if (!contactName) {
    return { ok: false, error: "Contact name is required.", status: 400 };
  }
  if (!EMAIL_PATTERN.test(contactEmail)) {
    return { ok: false, error: "A valid contact email is required.", status: 400 };
  }
  if (!message) {
    return { ok: false, error: "A public summary is required.", status: 400 };
  }
  if (message.length > 5000) {
    return { ok: false, error: "Public summary exceeds the 5000 character limit.", status: 400 };
  }
  if (payload.privacy_consent !== true) {
    return { ok: false, error: "Privacy consent is required.", status: 400 };
  }
  if ((type === "claim" || type === "correction") && publicLinks.length + publicHashes.length === 0) {
    return {
      ok: false,
      error: "Claims and corrections require at least one public link or public hash.",
      status: 400
    };
  }

  const timestamp = now.toISOString();
  const submission: NormalizedIntakeSubmission = {
    submissionId: buildSubmissionId(now),
    submissionType: type,
    createdAt: timestamp,
    updatedAt: timestamp,
    businessReference,
    organizationName,
    contactName,
    contactEmail,
    publicMessage: message,
    publicLinks,
    publicHashes,
    privacyConsent: true
  };

  return { ok: true, submission };
}
