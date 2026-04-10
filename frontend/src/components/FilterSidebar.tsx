import type { ChangeEvent } from "react";
import type { DirectoryFilters } from "../lib/filters";
import type { FilterMetadata } from "../lib/types";

interface FilterSidebarProps {
  filters: DirectoryFilters;
  metadata: Record<string, FilterMetadata>;
  onChange: (next: DirectoryFilters) => void;
}

export function FilterSidebar({ filters, metadata, onChange }: FilterSidebarProps) {
  function update<K extends keyof DirectoryFilters>(key: K, value: DirectoryFilters[K]) {
    onChange({
      ...filters,
      [key]: value
    });
  }

  const scoreMin = metadata.trust_score_range?.min ?? 0;
  const scoreMax = metadata.trust_score_range?.max ?? 1;

  return (
    <aside className="filter-sidebar">
      <div className="filter-group">
        <label htmlFor="status-filter">Verification status</label>
        <select
          id="status-filter"
          value={filters.verifiedStatus}
          onChange={(event: ChangeEvent<HTMLSelectElement>) => update("verifiedStatus", event.target.value)}
        >
          <option value="">All states</option>
          {metadata.verified_status?.options?.map((option) => (
            <option key={option} value={option}>
              {option.replace("_", " ")}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="confidence-filter">Confidence</label>
        <select
          id="confidence-filter"
          value={filters.confidenceBand}
          onChange={(event) => update("confidenceBand", event.target.value)}
        >
          <option value="">All levels</option>
          {metadata.confidence_level?.options?.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="review-filter">Review state</label>
        <select
          id="review-filter"
          value={filters.disputeState}
          onChange={(event) => update("disputeState", event.target.value)}
        >
          <option value="">All review states</option>
          {metadata.open_review?.options?.map((option) => (
            <option key={option} value={option}>
              {option.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="minimum-score">Trust score range</label>
        <div className="range-fields">
          <input
            id="minimum-score"
            type="number"
            min={scoreMin}
            max={scoreMax}
            step="0.05"
            value={filters.minimumScore}
            onChange={(event) => update("minimumScore", Number(event.target.value))}
          />
          <input
            type="number"
            min={scoreMin}
            max={scoreMax}
            step="0.05"
            value={filters.maximumScore}
            onChange={(event) => update("maximumScore", Number(event.target.value))}
          />
        </div>
      </div>

      <div className="filter-group">
        <label htmlFor="minimum-evidence">Minimum evidence count</label>
        <input
          id="minimum-evidence"
          type="number"
          min={0}
          value={filters.minimumEvidenceCount}
          onChange={(event) => update("minimumEvidenceCount", Number(event.target.value))}
        />
      </div>

      <div className="filter-group checkbox-row">
        <input
          id="procurement-only"
          type="checkbox"
          checked={filters.procurementOnly}
          onChange={(event) => update("procurementOnly", event.target.checked)}
        />
        <label htmlFor="procurement-only">Procurement-linked evidence only</label>
      </div>

      <div className="filter-group filter-group--disabled">
        <label>Sector</label>
        <input type="text" disabled placeholder={metadata.sector?.note ?? "Unavailable"} />
      </div>

      <div className="filter-group filter-group--disabled">
        <label>Location</label>
        <input type="text" disabled placeholder={metadata.location?.note ?? "Unavailable"} />
      </div>
    </aside>
  );
}
