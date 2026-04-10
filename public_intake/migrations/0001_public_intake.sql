CREATE TABLE IF NOT EXISTS intake_submissions (
  submission_id TEXT PRIMARY KEY,
  submission_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'received',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  business_reference TEXT,
  organization_name TEXT,
  contact_name TEXT NOT NULL,
  contact_email TEXT NOT NULL,
  public_message TEXT NOT NULL,
  public_links_json TEXT NOT NULL,
  public_hashes_json TEXT NOT NULL,
  privacy_consent INTEGER NOT NULL,
  moderation_notes TEXT,
  intake_source TEXT NOT NULL DEFAULT 'public_web'
);

CREATE INDEX IF NOT EXISTS intake_submissions_type_idx
  ON intake_submissions (submission_type, created_at DESC);

CREATE INDEX IF NOT EXISTS intake_submissions_business_idx
  ON intake_submissions (business_reference, created_at DESC);
