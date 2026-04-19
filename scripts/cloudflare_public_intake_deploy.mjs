import { mkdtemp, readFile, readdir } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";

function requireEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

async function run(command, args, options = {}) {
  await new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: options.cwd,
      env: options.env,
      stdio: "inherit",
      shell: process.platform === "win32",
    });

    child.on("exit", (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(`${command} exited with code ${code ?? "unknown"}`));
    });
    child.on("error", reject);
  });
}

async function fetchCloudflareJson(url, token, init = {}) {
  const response = await fetch(url, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(init.headers ?? {}),
    },
  });
  const body = await response.json();
  if (!response.ok || body.success === false) {
    throw new Error(
      `Cloudflare API request failed (${response.status}): ${JSON.stringify(body.errors ?? body)}`,
    );
  }
  return body.result;
}

function splitSqlStatements(sqlText) {
  return sqlText
    .split(/;\s*(?:\r?\n|$)/)
    .map((statement) => statement.trim())
    .filter((statement) => statement.length > 0);
}

async function applyMigrations(accountId, databaseId, token, migrationsDir) {
  const entries = (await readdir(migrationsDir))
    .filter((name) => name.endsWith(".sql"))
    .sort();

  for (const entry of entries) {
    const sqlText = await readFile(path.join(migrationsDir, entry), "utf8");
    for (const statement of splitSqlStatements(sqlText)) {
      await fetchCloudflareJson(
        `https://api.cloudflare.com/client/v4/accounts/${accountId}/d1/database/${databaseId}/query`,
        token,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ sql: statement }),
        },
      );
    }
  }
}

async function main() {
  const repoRoot = requireEnv("CF_REPO_ROOT");
  const accountId = requireEnv("CF_ACCOUNT_ID");
  const zoneId = requireEnv("CF_ZONE_ID");
  const token = requireEnv("CLOUDFLARE_API_TOKEN");
  const workerName = requireEnv("CF_WORKER_NAME");
  const hostname = requireEnv("CF_HOSTNAME");
  const publicSiteOrigin = requireEnv("CF_PUBLIC_SITE_ORIGIN");
  const turnstileSiteKey = requireEnv("CF_TURNSTILE_SITE_KEY");
  const turnstileSecretKey = requireEnv("CF_TURNSTILE_SECRET_KEY");
  const databaseId = requireEnv("CF_D1_DATABASE_ID");
  const previewDatabaseId = requireEnv("CF_D1_PREVIEW_DATABASE_ID");
  const compatibilityDate = process.env.CF_COMPATIBILITY_DATE ?? "2025-11-01";

  const migrationsDir = path.join(repoRoot, "public_intake", "migrations");
  await applyMigrations(accountId, databaseId, token, migrationsDir);
  if (previewDatabaseId !== databaseId) {
    await applyMigrations(accountId, previewDatabaseId, token, migrationsDir);
  }

  const tempDir = await mkdtemp(path.join(os.tmpdir(), "cf-public-intake-"));
  const bundlePath = path.join(tempDir, "worker.js");
  await run(
    "npx",
    ["esbuild", "src/index.ts", "--bundle", "--format=esm", "--platform=browser", "--target=es2022", `--outfile=${bundlePath}`],
    { cwd: path.join(repoRoot, "public_intake"), env: process.env },
  );

  const metadata = {
    main_module: "worker.js",
    compatibility_date: compatibilityDate,
    bindings: [
      { name: "INTAKE_DB", type: "d1", id: databaseId },
      { name: "PUBLIC_SITE_ORIGIN", type: "plain_text", text: publicSiteOrigin },
      { name: "TURNSTILE_SITE_KEY", type: "plain_text", text: turnstileSiteKey },
      { name: "TURNSTILE_SECRET_KEY", type: "secret_text", text: turnstileSecretKey },
    ],
  };

  const form = new FormData();
  form.set("metadata", JSON.stringify(metadata));
  form.set("worker.js", new Blob([await readFile(bundlePath)], { type: "application/javascript+module" }), "worker.js");

  await fetchCloudflareJson(
    `https://api.cloudflare.com/client/v4/accounts/${accountId}/workers/scripts/${workerName}`,
    token,
    {
      method: "PUT",
      body: form,
    },
  );

  const domain = await fetchCloudflareJson(
    `https://api.cloudflare.com/client/v4/accounts/${accountId}/workers/domains`,
    token,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        hostname,
        service: workerName,
        zone_id: zoneId,
      }),
    },
  );

  console.log(`WORKER_NAME=${workerName}`);
  console.log(`WORKER_HOST=https://${hostname}/`);
  console.log(`WORKER_DOMAIN_ID=${domain.id ?? ""}`);
}

await main();
