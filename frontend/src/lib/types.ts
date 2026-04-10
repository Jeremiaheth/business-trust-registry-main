export interface Badge {
  kind: string;
  label: string;
  tone: string;
}

export interface FilterMetadata {
  enabled: boolean;
  label: string;
  options?: string[];
  min?: number;
  max?: number;
  note?: string;
}

export interface IndexEntry {
  btr_id: string;
  legal_name: string;
  trading_name: string;
  jurisdiction: string;
  record_state: string;
  score: number;
  confidence: number;
  confidence_band: string;
  band: string;
  status: string;
  display_state: string;
  public_note: string;
  verification_timestamp: string;
  evidence_count: number;
  procurement_activity: boolean;
  badges: Badge[];
}

export interface SearchEntry {
  btr_id: string;
  display_name: string;
  legal_name: string;
  trading_name: string;
  jurisdiction: string;
  display_state: string;
  score: number;
  confidence: number;
  confidence_band: string;
  band: string;
  summary: string;
  evidence_count: number;
  procurement_activity: boolean;
  open_review: boolean;
  badges: Badge[];
  tags: string[];
  terms: string[];
  filters: Record<string, string>;
}

export interface QueueStatus {
  mode: string;
  stale: boolean;
  open_counts: {
    disputes: number;
  };
  public_message?: string;
  maintenance_message?: string;
}

export interface DimensionBreakdown {
  key: string;
  label: string;
  availability: string;
  score: number | null;
  confidence: number | null;
  weighted_score: number | null;
  source_dimension: string | null;
  note: string;
}

export interface TimelineEvent {
  timestamp: string;
  type: string;
  label: string;
  status: string;
  description: string;
  source_url?: string;
}

export interface VerificationPanel {
  availability: string;
  label: string;
  status: string;
  note: string;
  primary_identifier?: string;
  public_links?: string[];
  evidence_count?: number;
  source_types?: string[];
  awards_count?: number;
  buyers?: string[];
  buyer_diversity_count?: number;
  last_seen?: string;
}

export interface ReportLink {
  availability: string;
  route: string;
  api_path: string;
  title: string;
  note: string;
}

export interface BusinessPresentation {
  display_name: string;
  headline_summary: string;
  trust_status_label: string;
  decision_support_note: string;
  badges: Badge[];
  confidence_band: string;
  dimension_breakdown: DimensionBreakdown[];
  timeline: TimelineEvent[];
  verification_panels: Record<string, VerificationPanel>;
  report: ReportLink;
}

export interface BusinessDocument {
  btr_id: string;
  generated_at: string;
  profile: {
    legal_name: string;
    trading_name?: string;
    jurisdiction: string;
    identifiers?: {
      primary?: string;
      secondary?: string[];
    };
    public_links?: string[];
  };
  score: {
    score: number;
    confidence: number;
    band: string;
    status: string;
    display_state: string;
    public_note: string;
    verification_timestamp: string;
  };
  evidence: Array<{
    evidence_id: string;
    summary: string;
    observed_at: string;
    source_url: string;
    source_type?: string;
    tags?: string[];
  }>;
  disputes: Array<{
    case_id: string;
    state: string;
    redacted_summary: string;
    updated_at: string;
  }>;
  derived_records: Array<{
    path: string;
    document: Record<string, unknown>;
  }>;
  presentation: BusinessPresentation;
}

export interface ReportDocument {
  btr_id: string;
  generated_at: string;
  display_name: string;
  title: string;
  decision_support_note: string;
  headline_summary: string;
  badges: Badge[];
  scorecard: {
    score: number;
    confidence: number;
    confidence_band: string;
    band: string;
    status: string;
    display_state: string;
    verification_timestamp: string;
  };
  dimension_breakdown: DimensionBreakdown[];
  timeline: TimelineEvent[];
  verification_panels: Record<string, VerificationPanel>;
  evidence: Array<{
    evidence_id: string;
    summary: string;
    observed_at: string;
    source_url: string;
    tags?: string[];
  }>;
  disputes: Array<{
    case_id: string;
    state: string;
    redacted_summary: string;
    updated_at: string;
  }>;
}

export interface IndexDocument {
  generated_at: string;
  counts: {
    businesses: number;
    evidence: number;
    open_disputes: number;
  };
  filters: Record<string, FilterMetadata>;
  items: IndexEntry[];
}

export interface SearchDocument {
  generated_at: string;
  filters: Record<string, FilterMetadata>;
  entries: SearchEntry[];
}

export interface IntakeSubmissionResponse {
  ok: boolean;
  intake_reference: string;
  status: string;
}
