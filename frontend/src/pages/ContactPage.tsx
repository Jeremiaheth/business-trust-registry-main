import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { submitIntake } from "../lib/api";

type FormVariant = "contact" | "claim" | "correction";

const variants: FormVariant[] = ["contact", "claim", "correction"];

interface SubmissionState {
  error: string | null;
  intakeReference: string | null;
  loading: boolean;
}

function variantCopy(variant: FormVariant) {
  if (variant === "claim") {
    return {
      title: "Claim a business profile",
      description:
        "Submit public links and hashes only. Evidence uploads are disabled in public beta."
    };
  }
  if (variant === "correction") {
    return {
      title: "Request a correction",
      description:
        "Open a factual correction request with a public explanation and traceable public links."
    };
  }
  return {
    title: "Contact the registry team",
    description:
      "Use this channel for product questions, transparency requests, and moderation-safe public feedback."
  };
}

export function ContactPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentVariant = useMemo<FormVariant>(() => {
    const candidate = searchParams.get("type");
    return variants.includes(candidate as FormVariant) ? (candidate as FormVariant) : "contact";
  }, [searchParams]);
  const initialBusinessId = searchParams.get("btrId") ?? "";
  const [turnstileToken, setTurnstileToken] = useState("");
  const [state, setState] = useState<SubmissionState>({
    error: null,
    intakeReference: null,
    loading: false
  });
  const turnstileRef = useRef<HTMLDivElement | null>(null);
  const widgetIdRef = useRef<string | null>(null);
  const turnstileSiteKey = import.meta.env.VITE_TURNSTILE_SITE_KEY ?? "";

  useEffect(() => {
    if (!turnstileSiteKey || !turnstileRef.current) {
      return;
    }
    const existingScript = document.querySelector<HTMLScriptElement>(
      'script[data-turnstile-script="true"]',
    );

    function renderWidget() {
      if (!window.turnstile || !turnstileRef.current || widgetIdRef.current) {
        return;
      }
      widgetIdRef.current = window.turnstile.render(turnstileRef.current, {
        sitekey: turnstileSiteKey,
        theme: "light",
        callback: (token) => setTurnstileToken(token),
        "expired-callback": () => setTurnstileToken(""),
        "error-callback": () => setTurnstileToken("")
      });
    }

    if (existingScript) {
      renderWidget();
      return;
    }

    const script = document.createElement("script");
    script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
    script.async = true;
    script.defer = true;
    script.dataset.turnstileScript = "true";
    script.addEventListener("load", renderWidget);
    document.body.appendChild(script);

    return () => {
      if (widgetIdRef.current && window.turnstile) {
        window.turnstile.remove(widgetIdRef.current);
        widgetIdRef.current = null;
      }
    };
  }, [turnstileSiteKey]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const payload = {
      business_reference: String(form.get("business_reference") ?? ""),
      organization_name: String(form.get("organization_name") ?? ""),
      contact_name: String(form.get("contact_name") ?? ""),
      contact_email: String(form.get("contact_email") ?? ""),
      message: String(form.get("message") ?? ""),
      public_links: String(form.get("public_links") ?? "")
        .split("\n")
        .map((value) => value.trim())
        .filter(Boolean),
      public_hashes: String(form.get("public_hashes") ?? "")
        .split("\n")
        .map((value) => value.trim())
        .filter(Boolean),
      privacy_consent: form.get("privacy_consent") === "on",
      turnstile_token: turnstileToken
    };

    setState({
      error: null,
      intakeReference: null,
      loading: true
    });
    try {
      const response = await submitIntake(currentVariant, payload);
      setState({
        error: null,
        intakeReference: response.intake_reference,
        loading: false
      });
      formElement.reset();
      setTurnstileToken("");
    } catch (error) {
      setState({
        error: error instanceof Error ? error.message : "Submission failed",
        intakeReference: null,
        loading: false
      });
    }
  }

  const copy = variantCopy(currentVariant);

  return (
    <div className="page page-contact">
      <section className="page-hero page-hero--compact">
        <div>
          <p className="eyebrow">Public intake</p>
          <h1>{copy.title}</h1>
          <p>{copy.description}</p>
          <p className="muted">
            Claims and corrections accept public links and hashes only. No binary uploads are
            accepted in this phase.
          </p>
        </div>
      </section>

      <section className="contact-layout">
        <div className="contact-tabs" role="tablist" aria-label="Intake form variants">
          {variants.map((variant) => (
            <button
              className={variant === currentVariant ? "tab tab--active" : "tab"}
              key={variant}
              onClick={() => setSearchParams({ type: variant })}
              type="button"
            >
              {variant}
            </button>
          ))}
        </div>

        <form className="contact-form panel-card" onSubmit={handleSubmit}>
          <label>
            BTR ID or business reference
            <input defaultValue={initialBusinessId} name="business_reference" type="text" />
          </label>
          <label>
            Organization name
            <input name="organization_name" type="text" />
          </label>
          <label>
            Contact name
            <input name="contact_name" required type="text" />
          </label>
          <label>
            Contact email
            <input name="contact_email" required type="email" />
          </label>
          <label>
            Public summary
            <textarea name="message" required rows={6} />
          </label>
          <label>
            Public links
            <textarea name="public_links" rows={4} placeholder="One public URL per line" />
          </label>
          <label>
            Public hashes
            <textarea name="public_hashes" rows={3} placeholder="One digest reference per line" />
          </label>
          <label className="checkbox-row">
            <input name="privacy_consent" required type="checkbox" />
            <span>I consent to moderation and understand public-beta review may delay response.</span>
          </label>
          {turnstileSiteKey ? <div className="turnstile-shell" ref={turnstileRef} /> : null}
          {!turnstileSiteKey ? (
            <p className="muted">
              Turnstile site key is not configured in this preview build. Submission will only work
              once the site key is provided.
            </p>
          ) : null}
          {state.error ? <p className="error-text">{state.error}</p> : null}
          {state.intakeReference ? (
            <p className="success-text">Submission received. Intake reference: {state.intakeReference}</p>
          ) : null}
          <button
            className="button button--primary"
            disabled={state.loading || (Boolean(turnstileSiteKey) && !turnstileToken)}
            type="submit"
          >
            {state.loading ? "Submitting…" : "Submit intake"}
          </button>
        </form>
      </section>
    </div>
  );
}
