import { access, mkdtemp, readFile } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
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

async function exists(filePath) {
  try {
    await access(filePath, fsConstants.F_OK);
    return true;
  } catch {
    return false;
  }
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

async function main() {
  const accountId = requireEnv("CF_ACCOUNT_ID");
  const projectName = requireEnv("CF_PAGES_PROJECT");
  const pagesDir = requireEnv("CF_PAGES_DIR");
  const apiToken = requireEnv("CLOUDFLARE_API_TOKEN");
  const branch = process.env.CF_BRANCH ?? "main";
  const wranglerVersion = process.env.CF_WRANGLER_VERSION ?? "4.81.1";
  const commitHash = process.env.CF_COMMIT_HASH ?? "";
  const commitMessage = process.env.CF_COMMIT_MESSAGE ?? "";
  const commitDirty = process.env.CF_COMMIT_DIRTY ?? "";

  const uploadTokenResult = await fetchCloudflareJson(
    `https://api.cloudflare.com/client/v4/accounts/${accountId}/pages/projects/${projectName}/upload-token`,
    apiToken,
  );

  const tempDir = await mkdtemp(path.join(os.tmpdir(), "cf-pages-"));
  const manifestPath = path.join(tempDir, "manifest.json");

  await run(
    "npx",
    ["--yes", `wrangler@${wranglerVersion}`, "pages", "project", "upload", pagesDir, "--output-manifest-path", manifestPath],
    {
      env: {
        ...process.env,
        CF_PAGES_UPLOAD_JWT: uploadTokenResult.jwt,
      },
    },
  );

  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  const form = new FormData();
  form.set("manifest", JSON.stringify(manifest));
  form.set("branch", branch);
  if (commitHash) {
    form.set("commit_hash", commitHash);
  }
  if (commitMessage) {
    form.set("commit_message", commitMessage);
  }
  if (commitDirty) {
    form.set("commit_dirty", commitDirty);
  }

  for (const filename of ["_headers", "_redirects", "functions-filepath-routing-config.json", "_worker.bundle", "_routes.json"]) {
    const fullPath = path.join(pagesDir, filename);
    if (await exists(fullPath)) {
      form.set(filename, new Blob([await readFile(fullPath)]), filename);
    }
  }

  const deployment = await fetchCloudflareJson(
    `https://api.cloudflare.com/client/v4/accounts/${accountId}/pages/projects/${projectName}/deployments`,
    apiToken,
    {
      method: "POST",
      body: form,
    },
  );

  console.log(`DEPLOYMENT_ID=${deployment.id}`);
  console.log(`DEPLOYMENT_URL=${deployment.url}`);
}

await main();
