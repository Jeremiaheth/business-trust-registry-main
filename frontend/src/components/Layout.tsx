import { Building2, FilePenLine, Info, Mail, Search, ShieldCheck } from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";

function activeClassName({ isActive }: { isActive: boolean }) {
  return isActive ? "nav-link nav-link--active" : "nav-link";
}

export function Layout() {
  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="site-header__inner">
          <Link className="brand" to="/">
            <span className="brand__mark">
              <ShieldCheck size={22} />
            </span>
            <span>
              <strong>BTR-NG</strong>
              <small>Business Trust Registry Nigeria</small>
            </span>
          </Link>

          <nav className="site-nav" aria-label="Primary">
            <NavLink className={activeClassName} to="/">
              <Building2 size={16} /> Home
            </NavLink>
            <NavLink className={activeClassName} to="/directory">
              <Search size={16} /> Directory
            </NavLink>
            <NavLink className={activeClassName} to="/about">
              <Info size={16} /> About
            </NavLink>
            <NavLink className={activeClassName} to="/contact">
              <Mail size={16} /> Contact
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="page-shell">
        <Outlet />
      </main>

      <footer className="site-footer">
        <div className="site-footer__grid">
          <section>
            <p className="eyebrow">Transparency</p>
            <p>
              BTR-NG publishes evidence-based decision-support records. It is not a government certification and does not replace regulated due diligence.
            </p>
          </section>
          <section>
            <p className="eyebrow">Privacy</p>
            <p>
              Public submissions are moderation-gated. Contact, claim, and correction forms accept
              public links and hashes only in this beta.
            </p>
          </section>
          <section>
            <p className="eyebrow">Open data</p>
            <p>
              Procurement-linked signals are derived from published procurement data and linked
              public references.
            </p>
          </section>
          <section>
            <p className="eyebrow">Public beta</p>
            <p>
              Confidence indicates evidence completeness. Coverage remains partial while CAC, PSC,
              sector, and location integrations are still unavailable in public beta.
            </p>
            <Link className="inline-link" to="/contact?type=correction">
              <FilePenLine size={16} /> Request a correction
            </Link>
          </section>
        </div>
      </footer>
    </div>
  );
}
