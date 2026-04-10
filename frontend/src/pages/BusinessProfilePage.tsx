import { AlertTriangle, ArrowRight, Download, Landmark, ShieldCheck } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { ConfidenceMeter } from "../components/ConfidenceMeter";
import { ScoreCard } from "../components/ScoreCard";
import { StatusBadge } from "../components/StatusBadge";
import { Timeline } from "../components/Timeline";
import { useApi } from "../hooks/useApi";
import { fetchBusiness } from "../lib/api";
import { formatDate, formatPercent } from "../lib/filters";

export function BusinessProfilePage() {
  const { btrId = "" } = useParams();
  const { data, loading, error } = useApi(() => fetchBusiness(btrId), [btrId]);

  if (loading) {
    return <div className="empty-state">Loading business profile…</div>;
  }
  if (error || !data) {
    return <div className="empty-state">Profile unavailable: {error ?? "Unknown error"}</div>;
  }

  const reportRoute = data.presentation.report.route;
  const procurementPanel = data.presentation.verification_panels.procurement;

  return (
    <div className="page page-profile">
      <section className="page-hero page-hero--profile">
        <div>
          <p className="eyebrow">{data.btr_id}</p>
          <h1>{data.presentation.display_name}</h1>
          <p className="profile-summary">{data.presentation.headline_summary}</p>
          <div className="badge-row">
            {data.presentation.badges.map((badge) => (
              <StatusBadge badge={badge} key={`${data.btr_id}-${badge.label}`} />
            ))}
          </div>
          <p className="decision-note">
            <AlertTriangle size={16} />
            {data.presentation.decision_support_note}
          </p>
          <div className="cta-row">
            <Link className="button button--primary" to={reportRoute}>
              View Trust Report
            </Link>
            <Link className="button button--secondary" to={`/contact?type=correction&btrId=${data.btr_id}`}>
              Request correction
            </Link>
          </div>
        </div>
        <ScoreCard
          score={data.score.score}
          confidence={data.score.confidence}
          band={data.score.band}
          headline={data.presentation.trust_status_label}
        />
      </section>

      <section className="profile-grid">
        <article className="panel-card">
          <div className="panel-card__heading">
            <ShieldCheck />
            <h2>Verification posture</h2>
          </div>
          <p className="muted">Last score refresh: {formatDate(data.score.verification_timestamp)}</p>
          <ConfidenceMeter label="Confidence score" confidence={data.score.confidence} />
          <div className="dimension-grid">
            {data.presentation.dimension_breakdown.map((dimension) => (
              <article className="dimension-card" key={dimension.key}>
                <div className="dimension-card__header">
                  <h3>{dimension.label}</h3>
                  <span>
                    {dimension.availability === "available" && dimension.score !== null
                      ? formatPercent(dimension.score)
                      : "Beta"}
                  </span>
                </div>
                <p>{dimension.note}</p>
              </article>
            ))}
          </div>
        </article>

        <article className="panel-card">
          <div className="panel-card__heading">
            <Landmark />
            <h2>Verification panels</h2>
          </div>
          <div className="verification-panel-list">
            {Object.entries(data.presentation.verification_panels).map(([key, panel]) => (
              <article className="verification-panel" key={key}>
                <div className="verification-panel__title">
                  <h3>{panel.label}</h3>
                  <span className={`pill pill--${panel.status}`}>{panel.status.replaceAll("_", " ")}</span>
                </div>
                <p>{panel.note}</p>
                {panel.primary_identifier ? <p>Primary identifier: {panel.primary_identifier}</p> : null}
                {panel.awards_count !== undefined ? (
                  <p>
                    Procurement-linked awards: {panel.awards_count}, buyers: {panel.buyer_diversity_count}
                  </p>
                ) : null}
                {panel.last_seen ? <p>Last procurement signal: {formatDate(panel.last_seen)}</p> : null}
              </article>
            ))}
          </div>
        </article>
      </section>

      <section className="profile-grid">
        <article className="panel-card">
          <div className="panel-card__heading">
            <Download />
            <h2>Trust report</h2>
          </div>
          <p>
            The current public beta exposes an HTML trust report built from the public score
            snapshot, profile timeline, and linked evidence. No signed artifact is published in
            this phase.
          </p>
          <Link className="inline-link" to={reportRoute}>
            Open report <ArrowRight size={16} />
          </Link>
        </article>

        <article className="panel-card">
          <h2>Procurement signals</h2>
          <p>{procurementPanel.note}</p>
          <p>
            Procurement availability: {procurementPanel.availability.replaceAll("_", " ")}
          </p>
        </article>
      </section>

      <section className="profile-grid">
        <article className="panel-card">
          <h2>Verification timeline</h2>
          <Timeline items={data.presentation.timeline} />
        </article>
        <article className="panel-card">
          <h2>Evidence and review history</h2>
          <div className="evidence-list">
            {data.evidence.map((item) => (
              <article className="evidence-card" key={item.evidence_id}>
                <h3>{item.evidence_id}</h3>
                <p>{item.summary}</p>
                <div className="timeline__meta">
                  <span>{formatDate(item.observed_at)}</span>
                  <a href={item.source_url} rel="noreferrer" target="_blank">
                    Public source
                  </a>
                </div>
              </article>
            ))}
            {data.disputes.map((item) => (
              <article className="evidence-card" key={item.case_id}>
                <h3>{item.case_id}</h3>
                <p>{item.redacted_summary}</p>
                <div className="timeline__meta">
                  <span>{formatDate(item.updated_at)}</span>
                  <span>{item.state.replaceAll("_", " ")}</span>
                </div>
              </article>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
