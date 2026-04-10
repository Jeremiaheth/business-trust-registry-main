export function AboutPage() {
  return (
    <div className="page page-about">
      <section className="page-hero page-hero--compact">
        <div>
          <p className="eyebrow">About BTR-NG</p>
          <h1>Transparent business trust infrastructure for Nigeria.</h1>
          <p>
            BTR-NG is an evidence-based business trust registry for Nigeria. It combines public
            profile metadata, evidence references, deterministic score snapshots, confidence markers,
            and correction workflows into a public decision-support layer.
          </p>
        </div>
      </section>

      <section className="panel-grid">
        <article className="panel-card">
          <h2>Scoring philosophy</h2>
          <p>
            Scores are computed from validated scoring policy inputs and exposed together with
            confidence, status, and evidence trails. Confidence indicates evidence completeness.
          </p>
        </article>
        <article className="panel-card">
          <h2>Evidence limitations</h2>
          <p>
            The public registry uses committed public sources and moderated evidence references.
            Absence of evidence does not imply absence of business activity.
          </p>
        </article>
        <article className="panel-card">
          <h2>Public-language posture</h2>
          <p>
            BTR-NG avoids certification claims, official-seal framing, and fabricated statuses. It
            is a civic-tech registry, not a government approval layer.
          </p>
        </article>
        <article className="panel-card">
          <h2>Beta caveats</h2>
          <p>
            CAC verification, PSC disclosure, sector tagging, and location facets remain explicitly
            unavailable in public beta until trustworthy integrations are added.
          </p>
        </article>
      </section>
    </div>
  );
}
