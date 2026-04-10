import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { formatPercent } from "../lib/filters";
import type { SearchEntry } from "../lib/types";
import { StatusBadge } from "./StatusBadge";

interface BusinessCardProps {
  entry: SearchEntry;
}

export function BusinessCard({ entry }: BusinessCardProps) {
  return (
    <article className="business-card">
      <div className="business-card__topline">
        <div>
          <p className="business-card__id">{entry.btr_id}</p>
          <h3>{entry.display_name}</h3>
          <p className="muted">{entry.legal_name}</p>
        </div>
        <div className="score-chip">
          <span>Trust</span>
          <strong>{formatPercent(entry.score)}</strong>
        </div>
      </div>

      <p className="business-card__summary">{entry.summary}</p>

      <div className="business-card__metrics">
        <span>Confidence: {entry.confidence_band}</span>
        <span>Evidence: {entry.evidence_count}</span>
        <span>Jurisdiction: {entry.jurisdiction}</span>
      </div>

      <div className="badge-row">
        {entry.badges.map((badge) => (
          <StatusBadge badge={badge} key={`${entry.btr_id}-${badge.kind}-${badge.label}`} />
        ))}
      </div>

      <div className="business-card__footer">
        <span>Profile state: {entry.display_state.replaceAll("_", " ")}</span>
        <Link className="inline-link" to={`/businesses/${entry.btr_id}`}>
          View profile <ArrowRight size={16} />
        </Link>
      </div>
    </article>
  );
}
