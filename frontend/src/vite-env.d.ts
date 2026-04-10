/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_PUBLIC_INTAKE_BASE_URL?: string;
  readonly VITE_TURNSTILE_SITE_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare global {
  interface Window {
    turnstile?: {
      render: (
        container: HTMLElement,
        options: {
          callback: (token: string) => void;
          sitekey: string;
          "error-callback"?: () => void;
          "expired-callback"?: () => void;
          theme?: "light" | "dark";
        },
      ) => string;
      remove: (widgetId: string) => void;
    };
  }
}

export {};
