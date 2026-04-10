import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="empty-state">
      <h1>Page not found</h1>
      <p>The requested page is outside the current public beta routes.</p>
      <Link className="inline-link" to="/">
        Return to homepage
      </Link>
    </div>
  );
}
