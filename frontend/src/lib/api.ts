import type {
  BusinessDocument,
  IndexDocument,
  IntakeSubmissionResponse,
  QueueStatus,
  ReportDocument,
  SearchDocument,
} from "./types";

const API_ROOT = "/api/v1";
export const PUBLIC_INTAKE_BASE_URL =
  import.meta.env.VITE_PUBLIC_INTAKE_BASE_URL ?? "https://forms.btr.dpdns.org";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    headers: {
      Accept: "application/json"
    }
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export async function fetchIndex(): Promise<IndexDocument> {
  return fetchJson<IndexDocument>(`${API_ROOT}/index.json`);
}

export async function fetchSearch(): Promise<SearchDocument> {
  return fetchJson<SearchDocument>(`${API_ROOT}/search.json`);
}

export async function fetchBusiness(btrId: string): Promise<BusinessDocument> {
  return fetchJson<BusinessDocument>(`${API_ROOT}/businesses/${btrId}.json`);
}

export async function fetchReport(btrId: string): Promise<ReportDocument> {
  return fetchJson<ReportDocument>(`${API_ROOT}/reports/${btrId}.json`);
}

export async function fetchQueueStatus(): Promise<QueueStatus> {
  return fetchJson<QueueStatus>(`${API_ROOT}/queue_status.json`);
}

export async function submitIntake(
  submissionType: "contact" | "claim" | "correction",
  payload: Record<string, unknown>,
): Promise<IntakeSubmissionResponse> {
  const response = await fetch(`${PUBLIC_INTAKE_BASE_URL}/api/intake/${submissionType}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json"
    },
    body: JSON.stringify(payload)
  });
  const data = (await response.json()) as IntakeSubmissionResponse & { error?: string };
  if (!response.ok) {
    throw new Error(data.error ?? `Submission failed with ${response.status}`);
  }
  return data;
}
