import type { Env } from "./types";

interface TurnstileResponse {
  success: boolean;
}

export async function verifyTurnstile(
  env: Env,
  token: string,
  remoteIp: string | null,
): Promise<boolean> {
  if (env.BYPASS_TURNSTILE === "true") {
    return true;
  }

  const secret = env.TURNSTILE_SECRET_KEY;
  if (!secret) {
    return false;
  }

  const body = new URLSearchParams();
  body.set("secret", secret);
  body.set("response", token);
  if (remoteIp) {
    body.set("remoteip", remoteIp);
  }

  const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body
  });
  if (!response.ok) {
    return false;
  }
  const result = (await response.json()) as TurnstileResponse;
  return result.success === true;
}
