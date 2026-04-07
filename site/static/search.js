document.addEventListener("DOMContentLoaded", () => {
  const app = document.querySelector("[data-search-app]");
  if (!app) {
    return;
  }

  const input = app.querySelector("#search-input");
  const results = app.querySelector("[data-search-results]");
  const searchUrl = app.getAttribute("data-search-url");
  const profilePrefix = app.getAttribute("data-profile-prefix");

  if (!(input instanceof HTMLInputElement) || !(results instanceof HTMLElement) || !searchUrl || !profilePrefix) {
    return;
  }

  const render = (entries, query) => {
    const normalized = query.trim().toLowerCase();
    const filtered = normalized
      ? entries.filter((entry) => entry.terms.some((term) => term.includes(normalized)))
      : entries;

    if (filtered.length === 0) {
      results.innerHTML = '<article class="panel"><p>No public profiles match that query.</p></article>';
      return;
    }

    results.innerHTML = filtered
      .map((entry) => `
        <article class="search-result-card">
          <div class="profile-card__meta">
            <span class="badge">${entry.display_state.replaceAll("_", " ")}</span>
          </div>
          <h3>${entry.display_name}</h3>
          <p class="muted">${entry.legal_name}</p>
          <p class="muted">${entry.tags.join(", ")}</p>
          <a class="text-link" href="${profilePrefix}${entry.btr_id}/">Open profile</a>
        </article>
      `)
      .join("");
  };

  fetch(searchUrl)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Failed to load search index: ${response.status}`);
      }
      return response.json();
    })
    .then((payload) => {
      const entries = Array.isArray(payload.entries) ? payload.entries : [];
      render(entries, "");
      input.addEventListener("input", () => render(entries, input.value));
    })
    .catch(() => {
      results.innerHTML = '<article class="panel"><p>Search is temporarily unavailable.</p></article>';
    });
});
