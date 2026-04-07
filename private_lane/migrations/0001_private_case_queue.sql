CREATE TABLE IF NOT EXISTS private_cases (
  case_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('claim', 'correction', 'verification')),
  state TEXT NOT NULL CHECK (state IN ('queued', 'under_review', 'resolved', 'rejected')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  btr_id TEXT,
  redacted_summary TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS case_references (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL,
  reference_kind TEXT NOT NULL CHECK (reference_kind IN ('hash', 'url')),
  reference_value TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (case_id) REFERENCES private_cases(case_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_private_cases_state ON private_cases(state);
CREATE INDEX IF NOT EXISTS idx_private_cases_kind ON private_cases(kind);
CREATE INDEX IF NOT EXISTS idx_case_references_case_id ON case_references(case_id);
