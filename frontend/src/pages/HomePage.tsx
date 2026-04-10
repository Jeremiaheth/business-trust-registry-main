import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  ArrowRight,
  BadgeCheck,
  Building2,
  FileCheck2,
  Landmark,
  Scale,
  ShieldAlert
} from "lucide-react";
import { useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { SearchBar } from "../components/SearchBar";
import { ScoreCard } from "../components/ScoreCard";
import { StatusBadge } from "../components/StatusBadge";
import { useApi } from "../hooks/useApi";
import { fetchIndex, fetchQueueStatus } from "../lib/api";
import { formatPercent } from "../lib/filters";

gsap.registerPlugin(ScrollTrigger);

const featureCards = [
  {
    title: "CAC verification status",
    body: "Structured paneling is live, but CAC integration remains explicitly unavailable in the public beta.",
    icon: BadgeCheck
  },
  {
    title: "PSC disclosure presence",
    body: "PSC availability is shown transparently as unavailable beta until a defensible integration is added.",
    icon: ShieldAlert
  },
  {
    title: "Procurement history",
    body: "NOCOPO-linked procurement signals sit alongside public-source evidence rather than replacing it.",
    icon: Landmark
  },
  {
    title: "Trust report",
    body: "Every profile exposes an HTML trust report route built from the same public evidence and score snapshot.",
    icon: FileCheck2
  },
  {
    title: "Correction and dispute flow",
    body: "Open review states stay visible, with public beta messaging and an intake path for factual corrections.",
    icon: Scale
  }
];

export function HomePage() {
  const navigate = useNavigate();
  const sectionRef = useRef<HTMLDivElement | null>(null);
  const { data: index, loading: indexLoading } = useApi(fetchIndex, []);
  const { data: queueStatus } = useApi(fetchQueueStatus, []);

  useEffect(() => {
    if (!sectionRef.current) {
      return;
    }
    const ctx = gsap.context(() => {
      gsap.fromTo(
        ".hero-copy > *",
        { y: 30, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.8,
          stagger: 0.12,
          ease: "power2.out"
        },
      );
      gsap.utils.toArray<HTMLElement>(".reveal").forEach((element) => {
        gsap.fromTo(
          element,
          { y: 40, opacity: 0 },
          {
            y: 0,
            opacity: 1,
            duration: 0.7,
            ease: "power2.out",
            scrollTrigger: {
              trigger: element,
              start: "top 85%"
            }
          },
        );
      });
    }, sectionRef);
    return () => ctx.revert();
  }, []);

  const featured = index?.items.slice(0, 3) ?? [];
  const leadBusiness = featured[0];

  return (
    <div className="page page-home" ref={sectionRef}>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Evidence-based business trust registry for Nigeria</p>
          <h1>Decision-support trust profiles for Nigerian businesses, built from public evidence.</h1>
          <p className="hero-copy__lede">
            BTR-NG connects trust score snapshots, confidence markers, procurement-linked signals,
            public evidence, and correction workflows in one civic-tech registry.
          </p>
          <SearchBar onSearch={(query) => navigate(`/directory?q=${encodeURIComponent(query)}`)} />
          <div className="cta-row">
            <Link className="button button--primary" to="/directory">
              Search Businesses
            </Link>
            <Link className="button button--secondary" to="/contact?type=claim">
              Claim Your Profile
            </Link>
            {leadBusiness ? (
              <Link className="button button--ghost" to={`/reports/${leadBusiness.btr_id}`}>
                View Trust Report
              </Link>
            ) : null}
          </div>
        </div>

        <div className="hero-panel">
          <div className="hero-panel__grid">
            <article className="glass-card">
              <p className="eyebrow">Registry coverage</p>
              <h2>{index?.counts.businesses ?? "--"}</h2>
              <p>Public profiles in the current beta registry.</p>
            </article>
            <article className="glass-card">
              <p className="eyebrow">Public evidence</p>
              <h2>{index?.counts.evidence ?? "--"}</h2>
              <p>Time-stamped references linked to profile records.</p>
            </article>
            <article className="glass-card">
              <p className="eyebrow">Open reviews</p>
              <h2>{index?.counts.open_disputes ?? "--"}</h2>
              <p>Profiles currently marked under review or correction.</p>
            </article>
            <article className="glass-card">
              <p className="eyebrow">Queue status</p>
              <h2>{queueStatus?.mode ?? "normal"}</h2>
              <p>{queueStatus?.maintenance_message ?? "Public scoring is available."}</p>
            </article>
          </div>
        </div>
      </section>

      <section className="panel-grid reveal">
        <article className="panel-card">
          <h2>Identity verification</h2>
          <p>
            Identity coverage is based on linked public identifiers and evidence continuity. It is
            evidence-backed, not claimed.
          </p>
        </article>
        <article className="panel-card">
          <h2>Trust score</h2>
          <p>
            Trust scores summarize identity, compliance, performance, and responsiveness dimensions
            from a deterministic scoring policy.
          </p>
        </article>
        <article className="panel-card">
          <h2>Confidence score</h2>
          <p>
            Confidence indicates evidence completeness. A low-confidence score means the evidence is
            too thin for a stable interpretation.
          </p>
        </article>
        <article className="panel-card">
          <h2>Public sources</h2>
          <p>
            Procurement-linked signals are derived from published procurement data. BTR-NG keeps the
            source trail visible in the profile timeline.
          </p>
        </article>
      </section>

      <section className="feature-section reveal">
        <div className="section-heading">
          <p className="eyebrow">How verification works</p>
          <h2>Credibility-first profile design with explicit beta boundaries.</h2>
        </div>
        <div className="feature-grid">
          {featureCards.map(({ title, body, icon: Icon }) => (
            <article className="feature-card" key={title}>
              <div className="feature-card__icon">
                <Icon />
              </div>
              <h3>{title}</h3>
              <p>{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="featured-section reveal">
        <div className="section-heading">
          <p className="eyebrow">Featured profiles</p>
          <h2>Examples from the current public beta registry.</h2>
        </div>
        {indexLoading ? <p className="empty-state">Loading profiles…</p> : null}
        <div className="featured-grid">
          {featured.map((item) => (
            <article className="featured-profile" key={item.btr_id}>
              <div className="featured-profile__header">
                <div>
                  <p className="eyebrow">{item.btr_id}</p>
                  <h3>{item.legal_name}</h3>
                </div>
                <div className="score-chip">
                  <span>Trust</span>
                  <strong>{formatPercent(item.score)}</strong>
                </div>
              </div>
              <p>{item.public_note}</p>
              <div className="badge-row">
                {item.badges.map((badge) => (
                  <StatusBadge badge={badge} key={`${item.btr_id}-${badge.label}`} />
                ))}
              </div>
              <Link className="inline-link" to={`/businesses/${item.btr_id}`}>
                Open business profile <ArrowRight size={16} />
              </Link>
            </article>
          ))}
        </div>
      </section>

      <section className="trust-report-section reveal">
        <div className="section-heading">
          <p className="eyebrow">Trust at a glance</p>
          <h2>Structured cards for score, confidence, and evidence posture.</h2>
        </div>
        <div className="trust-report-grid">
          <ScoreCard
            score={leadBusiness?.score ?? 0.62}
            confidence={leadBusiness?.confidence ?? 0.58}
            band={leadBusiness?.band ?? "moderate"}
          />
          <article className="panel-card panel-card--contrast">
            <div className="panel-card__heading">
              <Building2 />
              <h3>Public-beta safeguards</h3>
            </div>
            <p>
              CAC, PSC, sector, and location are intentionally marked unavailable until a defensible
              public integration is ready. The product does not fabricate those fields.
            </p>
            <p className="muted">
              Scores are decision support only. They do not represent certification, approval, or a
              government decision.
            </p>
          </article>
        </div>
      </section>
    </div>
  );
}
