export type SubmissionType = "contact" | "claim" | "correction";

export interface Env {
  INTAKE_DB: D1Database;
  PUBLIC_SITE_ORIGIN?: string;
  TURNSTILE_SECRET_KEY?: string;
  TURNSTILE_SITE_KEY?: string;
  BYPASS_TURNSTILE?: string;
}

export interface IntakePayload {
  business_reference?: string;
  organization_name?: string;
  contact_name?: string;
  contact_email?: string;
  message?: string;
  public_links?: string[];
  public_hashes?: string[];
  privacy_consent?: boolean;
  turnstile_token?: string;
  attachments?: unknown;
}

export interface NormalizedIntakeSubmission {
  submissionId: string;
  submissionType: SubmissionType;
  createdAt: string;
  updatedAt: string;
  businessReference: string;
  organizationName: string;
  contactName: string;
  contactEmail: string;
  publicMessage: string;
  publicLinks: string[];
  publicHashes: string[];
  privacyConsent: boolean;
}

export interface ValidationResult {
  ok: true;
  submission: NormalizedIntakeSubmission;
}

export interface ValidationErrorResult {
  ok: false;
  error: string;
  status: number;
}

export type ValidationOutcome = ValidationResult | ValidationErrorResult;
