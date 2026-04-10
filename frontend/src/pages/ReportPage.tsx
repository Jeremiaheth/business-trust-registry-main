import { Link, useParams } from "react-router-dom";
import { ScoreCard } from "../components/ScoreCard";
import { StatusBadge } from "../components/StatusBadge";
import { Timeline } from "../components/Timeline";
import { useApi } from "../hooks/useApi";
import { fetchReport } from "../lib/api";
import { formatDate } from "../lib/filters";

export function ReportPage() {
  const { btrId = "" } = useParams();
  const { data, loading, error } = useApi(() => fetchReport(btrId), [btrId]);

  if (loading) {
    return <div className="empty-state">Loading trust report…</div>;
  }
  if (!data || error) {
    return <div className="empty-state">Trust report unavailable: {error ?? "Unknown error"}</div>;
  }

  return (
    <div className="page page-report">
      <section className="page-hero page-hero--compact">
        <div>
          <p className="eyebrow">HTML trust report</p>
          <h1>{data.title}</h1>
          <p>{data.headline_summary}</p>
          <p className="muted">{data.decision_support_note}</p>
          <Link className="inline-link" to={`/businesses/${data.btr_id}`}>
            Back to business profile
          </Link>
        </div>
        <ScoreCard
          score={data.scorecard.score}
          confidence={data.scorecard.confidence}
          band={data.scorecard.band}
          headline={data.scorecard.display_state.replaceAll("_", " ")}
        />
      </section>

      <section className="profile-grid">
        <article className="panel-card">
          <h2>Report summary</h2>
          <div className="badge-row">
            {data.badges.map((badge) => (
              <StatusBadge badge={badge} key={`${data.btr_id}-${badge.label}`} />
            ))}
          </div>
          <p className="muted">Generated: {formatDate(data.generated_at)}</p>
          <Timeline items={data.timeline} />
        </article>
        <article className="panel-card">
          <h2>Evidence references</h2>
          <div className="evidence-list">
            {data.evidence.map((item) => (
              <article className="evidence-card" key={item.evidence_id}>
                <h3>{item.evidence_id}</h3>
                <p>{item.summary}</p>
                <div className="timeline__meta">
                  <span>{formatDate(item.observed_at)}</span>
                  <a href={item.source_url} rel="noreferrer" target="_blank">
                    Open source
                  </a>
                </div>
              </article>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
