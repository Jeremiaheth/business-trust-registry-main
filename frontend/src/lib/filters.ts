import type { SearchEntry } from "./types";

export interface DirectoryFilters {
  query: string;
  verifiedStatus: string;
  confidenceBand: string;
  disputeState: string;
  procurementOnly: boolean;
  minimumEvidenceCount: number;
  minimumScore: number;
  maximumScore: number;
}

export const DEFAULT_DIRECTORY_FILTERS: DirectoryFilters = {
  query: "",
  verifiedStatus: "",
  confidenceBand: "",
  disputeState: "",
  procurementOnly: false,
  minimumEvidenceCount: 0,
  minimumScore: 0,
  maximumScore: 1
};

export function applyDirectoryFilters(
  entries: SearchEntry[],
  filters: DirectoryFilters,
): SearchEntry[] {
  const query = filters.query.trim().toLowerCase();
  return entries.filter((entry) => {
    if (query.length > 0 && !entry.terms.some((term) => term.includes(query))) {
      return false;
    }
    if (filters.verifiedStatus && entry.display_state !== filters.verifiedStatus) {
      return false;
    }
    if (filters.confidenceBand && entry.confidence_band !== filters.confidenceBand) {
      return false;
    }
    if (filters.disputeState === "under_review" && !entry.open_review) {
      return false;
    }
    if (filters.disputeState === "not_under_review" && entry.open_review) {
      return false;
    }
    if (filters.procurementOnly && !entry.procurement_activity) {
      return false;
    }
    if (entry.evidence_count < filters.minimumEvidenceCount) {
      return false;
    }
    if (entry.score < filters.minimumScore || entry.score > filters.maximumScore) {
      return false;
    }
    return true;
  });
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-NG", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}
