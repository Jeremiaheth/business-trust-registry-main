import { persistSubmission } from "./store";
import { verifyTurnstile } from "./turnstile";
import type { Env, IntakePayload, SubmissionType } from "./types";
import { validateIntakePayload } from "./validation";

function corsHeaders(origin: string): HeadersInit {
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
  };
}

function jsonResponse(origin: string, status: number, body: Record<string, unknown>): Response {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: {
      ...corsHeaders(origin),
      "Content-Type": "application/json; charset=utf-8"
    }
  });
}

async function handleIntake(request: Request, env: Env, submissionType: SubmissionType): Promise<Response> {
  const origin = env.PUBLIC_SITE_ORIGIN ?? "https://www.btr.dpdns.org";
  const contentType = request.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return jsonResponse(origin, 415, { error: "Request content type must be application/json." });
  }

  const payload = (await request.json()) as IntakePayload;
  const validation = validateIntakePayload(submissionType, payload);
  if (!validation.ok) {
    return jsonResponse(origin, validation.status, { error: validation.error });
  }

  const token = typeof payload.turnstile_token === "string" ? payload.turnstile_token : "";
  const remoteIp = request.headers.get("CF-Connecting-IP");
  const turnstileValid = await verifyTurnstile(env, token, remoteIp);
  if (!turnstileValid) {
    return jsonResponse(origin, 403, { error: "Turnstile verification failed." });
  }

  await persistSubmission(env.INTAKE_DB, validation.submission);
  return jsonResponse(origin, 200, {
    ok: true,
    intake_reference: validation.submission.submissionId,
    status: "received"
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const origin = env.PUBLIC_SITE_ORIGIN ?? "https://www.btr.dpdns.org";
    const { pathname } = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(origin)
      });
    }

    if (request.method === "GET" && pathname === "/health") {
      return jsonResponse(origin, 200, {
        ok: true,
        status: "healthy",
        service: "public-intake"
      });
    }

    if (request.method === "POST" && pathname === "/api/intake/contact") {
      return handleIntake(request, env, "contact");
    }
    if (request.method === "POST" && pathname === "/api/intake/claim") {
      return handleIntake(request, env, "claim");
    }
    if (request.method === "POST" && pathname === "/api/intake/correction") {
      return handleIntake(request, env, "correction");
    }

    return jsonResponse(origin, 404, { error: "Route not found." });
  }
};
