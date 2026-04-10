import { expect, test } from "vitest";
import worker from "../src/index";
import { validateIntakePayload } from "../src/validation";

class FakePreparedStatement {
  constructor(
    private readonly query: string,
    private readonly collector: Array<{ query: string; params: unknown[] }>,
  ) {}

  bind(...params: unknown[]) {
    return {
      run: async () => {
        this.collector.push({ query: this.query, params });
        return { success: true };
      }
    };
  }
}

class FakeD1Database {
  statements: Array<{ query: string; params: unknown[] }> = [];

  prepare(query: string) {
    return new FakePreparedStatement(query, this.statements);
  }
}

const env = {
  INTAKE_DB: new FakeD1Database() as unknown as D1Database,
  PUBLIC_SITE_ORIGIN: "https://www.btr.dpdns.org",
  BYPASS_TURNSTILE: "true"
};

test("health route returns healthy status", async () => {
  const response = await worker.fetch(new Request("https://forms.btr.dpdns.org/health"), env);
  expect(response.status).toBe(200);
  expect(await response.json()).toEqual({
    ok: true,
    status: "healthy",
    service: "public-intake"
  });
});

test("contact submission persists a received intake record", async () => {
  const request = new Request("https://forms.btr.dpdns.org/api/intake/contact", {
    method: "POST",
    headers: {
      "content-type": "application/json"
    },
    body: JSON.stringify({
      contact_name: "Ada Okafor",
      contact_email: "ada@example.com",
      message: "I need clarity on a public evidence reference.",
      privacy_consent: true,
      turnstile_token: "test-token"
    })
  });

  const response = await worker.fetch(request, env);
  expect(response.status).toBe(200);
  const data = await response.json() as { intake_reference: string };
  expect(data.intake_reference.startsWith("INT-")).toBe(true);
});

test("claim validation requires public links or hashes", () => {
  const result = validateIntakePayload("claim", {
    contact_name: "Ada Okafor",
    contact_email: "ada@example.com",
    message: "Claim request",
    privacy_consent: true
  });

  expect(result.ok).toBe(false);
  if (!result.ok) {
    expect(result.error).toMatch(/at least one public link or public hash/i);
  }
});

test("correction endpoint rejects attachments", async () => {
  const request = new Request("https://forms.btr.dpdns.org/api/intake/correction", {
    method: "POST",
    headers: {
      "content-type": "application/json"
    },
    body: JSON.stringify({
      contact_name: "Ada Okafor",
      contact_email: "ada@example.com",
      message: "Correction request",
      public_links: ["https://example.com/reference"],
      privacy_consent: true,
      attachments: ["binary"],
      turnstile_token: "test-token"
    })
  });

  const response = await worker.fetch(request, env);
  expect(response.status).toBe(400);
  const data = await response.json() as { error: string };
  expect(data.error).toMatch(/attachments are not accepted/i);
});
