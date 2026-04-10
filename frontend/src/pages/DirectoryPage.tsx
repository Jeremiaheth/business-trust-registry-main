import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { BusinessCard } from "../components/BusinessCard";
import { FilterSidebar } from "../components/FilterSidebar";
import { SearchBar } from "../components/SearchBar";
import { useApi } from "../hooks/useApi";
import { fetchSearch } from "../lib/api";
import {
  applyDirectoryFilters,
  DEFAULT_DIRECTORY_FILTERS,
  type DirectoryFilters
} from "../lib/filters";

export function DirectoryPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialQuery = searchParams.get("q") ?? "";
  const { data, loading, error } = useApi(fetchSearch, []);
  const [filters, setFilters] = useState<DirectoryFilters>({
    ...DEFAULT_DIRECTORY_FILTERS,
    query: initialQuery
  });

  useEffect(() => {
    setFilters((current) => ({ ...current, query: initialQuery }));
  }, [initialQuery]);

  const filteredEntries = useMemo(
    () => applyDirectoryFilters(data?.entries ?? [], filters),
    [data?.entries, filters],
  );

  return (
    <div className="page page-directory">
      <section className="page-hero page-hero--compact">
        <div>
          <p className="eyebrow">Business directory</p>
          <h1>Search the public registry.</h1>
          <p>
            Filter profiles by trust score, confidence, review status, procurement-linked evidence,
            and evidence count. Sector and location remain unavailable in public beta.
          </p>
        </div>
        <SearchBar
          initialValue={filters.query}
          onSearch={(query) => {
            setFilters((current) => ({ ...current, query }));
            navigate(`/directory?q=${encodeURIComponent(query)}`);
          }}
        />
      </section>

      <section className="directory-layout">
        <FilterSidebar
          filters={filters}
          metadata={data?.filters ?? {}}
          onChange={setFilters}
        />

        <div className="directory-results">
          <div className="directory-results__header">
            <div>
              <p className="eyebrow">Search results</p>
              <h2>{filteredEntries.length} businesses</h2>
            </div>
            <p className="muted">
              Hybrid registry view: structured cards, public beta caveats, and evidence-first status
              markers.
            </p>
          </div>

          {loading ? <p className="empty-state">Loading directory…</p> : null}
          {error ? <p className="empty-state">Directory unavailable: {error}</p> : null}
          {!loading && filteredEntries.length === 0 ? (
            <p className="empty-state">No businesses match the current filters.</p>
          ) : null}

          <div className="business-card-list">
            {filteredEntries.map((entry) => (
              <BusinessCard entry={entry} key={entry.btr_id} />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
