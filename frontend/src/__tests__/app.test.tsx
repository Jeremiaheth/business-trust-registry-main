import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "../App";

const mockIndex = {
  generated_at: "2026-04-10T00:00:00Z",
  counts: {
    businesses: 12,
    evidence: 26,
    open_disputes: 2
  },
  filters: {
    verified_status: { enabled: true, label: "Verification status", options: ["normal", "under_review"] },
    trust_score_range: { enabled: true, label: "Trust score range", min: 0.2, max: 0.9 },
    confidence_level: { enabled: true, label: "Confidence level", options: ["limited", "moderate", "strong"], min: 0.2, max: 0.9 },
    evidence_count: { enabled: true, label: "Evidence count", min: 1, max: 5 },
    procurement_activity: { enabled: true, label: "Procurement", options: ["available", "not_available"] },
    open_review: { enabled: true, label: "Review", options: ["under_review", "not_under_review"] },
    sector: { enabled: false, label: "Sector", note: "Not yet available in public beta." },
    location: { enabled: false, label: "Location", note: "Not yet available in public beta." }
  },
  items: [
    {
      btr_id: "BTR-ACME-001",
      legal_name: "Insil Services Ltd",
      trading_name: "",
      jurisdiction: "NG",
      record_state: "published",
      score: 0.78,
      confidence: 0.71,
      confidence_band: "strong",
      band: "strong",
      status: "published",
      display_state: "normal",
      public_note: "Based on available verified evidence.",
      verification_timestamp: "2026-04-10T00:00:00Z",
      evidence_count: 4,
      procurement_activity: true,
      badges: [{ kind: "state", label: "Published profile", tone: "normal" }]
    }
  ]
};

const mockSearch = {
  generated_at: "2026-04-10T00:00:00Z",
  filters: mockIndex.filters,
  entries: [
    {
      btr_id: "BTR-ACME-001",
      display_name: "Insil Services Ltd",
      legal_name: "Insil Services Ltd",
      trading_name: "",
      jurisdiction: "NG",
      display_state: "normal",
      score: 0.78,
      confidence: 0.71,
      confidence_band: "strong",
      band: "strong",
      summary: "This profile is based on 4 public evidence references and a deterministic score snapshot.",
      evidence_count: 4,
      procurement_activity: true,
      open_review: false,
      badges: [{ kind: "state", label: "Published profile", tone: "normal" }],
      tags: ["federal-nocopo"],
      terms: ["insil services ltd", "btr-acme-001"],
      filters: {
        verified_status: "normal",
        confidence_level: "strong",
        procurement_activity: "available",
        open_review: "not_under_review"
      }
    }
  ]
};

const mockBusiness = {
  btr_id: "BTR-ACME-001",
  generated_at: "2026-04-10T00:00:00Z",
  profile: {
    legal_name: "Insil Services Ltd",
    jurisdiction: "NG",
    identifiers: {
      primary: "RC-12345"
    },
    public_links: ["https://example.com/public"]
  },
  score: {
    score: 0.78,
    confidence: 0.71,
    band: "strong",
    status: "published",
    display_state: "normal",
    public_note: "Based on available verified evidence.",
    verification_timestamp: "2026-04-10T00:00:00Z"
  },
  evidence: [
    {
      evidence_id: "EV-001",
      summary: "Award reference",
      observed_at: "2026-03-10T00:00:00Z",
      source_url: "https://example.com/evidence"
    }
  ],
  disputes: [],
  derived_records: [],
  presentation: {
    display_name: "Insil Services Ltd",
    headline_summary: "This profile is based on 4 public evidence references and a deterministic score snapshot.",
    trust_status_label: "Published profile",
    decision_support_note: "Decision-support only. BTR-NG publishes an evidence-based view and is not a government certification.",
    badges: [{ kind: "state", label: "Published profile", tone: "normal" }],
    confidence_band: "strong",
    dimension_breakdown: [
      {
        key: "identity",
        label: "Identity",
        availability: "available",
        score: 0.82,
        confidence: 0.8,
        weighted_score: 0.31,
        source_dimension: "identity",
        note: "Public identifier and profile continuity."
      }
    ],
    timeline: [
      {
        timestamp: "2026-04-10T00:00:00Z",
        type: "score_refresh",
        label: "Trust score refreshed",
        status: "normal",
        description: "Based on available verified evidence."
      }
    ],
    verification_panels: {
      identity: {
        availability: "available",
        label: "Identity verification",
        status: "evidence_backed",
        note: "Identity coverage is derived from public identifiers and linked evidence.",
        primary_identifier: "RC-12345"
      },
      cac: {
        availability: "unavailable_beta",
        label: "CAC verification",
        status: "unavailable_beta",
        note: "CAC integration is not yet available in the public beta."
      },
      psc: {
        availability: "unavailable_beta",
        label: "PSC disclosure presence",
        status: "unavailable_beta",
        note: "PSC disclosure integration is not yet available in the public beta."
      },
      procurement: {
        availability: "available",
        label: "Procurement / NOCOPO signals",
        status: "available",
        note: "Procurement-linked signals are derived from published procurement data and remain complementary evidence.",
        awards_count: 2,
        buyer_diversity_count: 1,
        last_seen: "2026-04-02T00:00:00Z"
      },
      evidence_quality: {
        availability: "available",
        label: "Evidence quality",
        status: "available",
        note: "Evidence quality reflects the completeness of public-source references in the profile.",
        evidence_count: 4,
        source_types: ["procurement_notice"]
      }
    },
    report: {
      availability: "html_only",
      route: "/reports/BTR-ACME-001",
      api_path: "/api/v1/reports/BTR-ACME-001.json",
      title: "Insil Services Ltd trust report",
      note: "HTML report only in public beta. No signed artifact is published in this phase."
    }
  }
};

const mockReport = {
  btr_id: "BTR-ACME-001",
  generated_at: "2026-04-10T00:00:00Z",
  display_name: "Insil Services Ltd",
  title: "Insil Services Ltd trust report",
  decision_support_note: "Decision-support only. BTR-NG publishes an evidence-based view and is not a government certification.",
  headline_summary: "This profile is based on 4 public evidence references and a deterministic score snapshot.",
  badges: [{ kind: "state", label: "Published profile", tone: "normal" }],
  scorecard: {
    score: 0.78,
    confidence: 0.71,
    confidence_band: "strong",
    band: "strong",
    status: "published",
    display_state: "normal",
    verification_timestamp: "2026-04-10T00:00:00Z"
  },
  dimension_breakdown: [],
  timeline: [],
  verification_panels: {},
  evidence: [
    {
      evidence_id: "EV-001",
      summary: "Award reference",
      observed_at: "2026-03-10T00:00:00Z",
      source_url: "https://example.com/evidence"
    }
  ],
  disputes: []
};

const mockQueue = {
  mode: "normal",
  stale: false,
  open_counts: {
    disputes: 2
  },
  maintenance_message: "Public scoring is available."
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/index.json")) {
        return Promise.resolve(new Response(JSON.stringify(mockIndex)));
      }
      if (url.endsWith("/api/v1/search.json")) {
        return Promise.resolve(new Response(JSON.stringify(mockSearch)));
      }
      if (url.endsWith("/api/v1/businesses/BTR-ACME-001.json")) {
        return Promise.resolve(new Response(JSON.stringify(mockBusiness)));
      }
      if (url.endsWith("/api/v1/reports/BTR-ACME-001.json")) {
        return Promise.resolve(new Response(JSON.stringify(mockReport)));
      }
      if (url.endsWith("/api/v1/queue_status.json")) {
        return Promise.resolve(new Response(JSON.stringify(mockQueue)));
      }
      if (url.includes("/api/intake/contact")) {
        return Promise.resolve(
          new Response(JSON.stringify({ ok: true, intake_reference: "INT-0001", status: "received" })),
        );
      }
      return Promise.resolve(new Response(JSON.stringify({ error: "not found" }), { status: 404 }));
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  );
}

test("renders homepage and directory routes", async () => {
  renderAt("/");
  expect(await screen.findByRole("heading", { name: /decision-support trust profiles/i })).toBeInTheDocument();
  expect(await screen.findByText(/registry coverage/i)).toBeInTheDocument();
});

test("renders directory and applies search query", async () => {
  renderAt("/directory?q=insil");
  expect(await screen.findByRole("heading", { name: /search the public registry/i })).toBeInTheDocument();
  expect((await screen.findAllByText("Insil Services Ltd")).length).toBeGreaterThan(0);
  expect(screen.getByDisplayValue("insil")).toBeInTheDocument();
});

test("renders business profile route", async () => {
  renderAt("/businesses/BTR-ACME-001");
  expect(await screen.findByRole("heading", { name: "Insil Services Ltd" })).toBeInTheDocument();
  expect(await screen.findByText(/decision-support only/i)).toBeInTheDocument();
  expect(screen.getByText(/CAC verification/i)).toBeInTheDocument();
});

test("renders report and contact routes", async () => {
  const user = userEvent.setup();
  renderAt("/contact?type=contact");
  expect(await screen.findByRole("heading", { name: /contact the registry team/i })).toBeInTheDocument();
  await user.type(screen.getByLabelText(/contact name/i), "Ada");
  await user.type(screen.getByLabelText(/contact email/i), "ada@example.com");
  await user.type(screen.getByLabelText(/public summary/i), "Need more detail on public evidence.");
  await user.click(screen.getByRole("checkbox"));
  await user.click(screen.getByRole("button", { name: /submit intake/i }));
  expect(await screen.findByText(/INT-0001/i)).toBeInTheDocument();

  renderAt("/reports/BTR-ACME-001");
  expect(await screen.findByRole("heading", { name: /insil services ltd trust report/i })).toBeInTheDocument();
});

test("renders about route", async () => {
  renderAt("/about");
  await waitFor(() => {
    expect(screen.getByRole("heading", { name: /transparent business trust infrastructure/i })).toBeInTheDocument();
  });
});
