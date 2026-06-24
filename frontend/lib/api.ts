export type ConfidenceLabel = "high" | "warn" | "red" | "refuse";

export interface Citation {
  clause_number: string;
  page_number: number | null;
  filename: string;
  quote_en: string;
}

export interface AskResponse {
  conversation_id: string;
  answer_ar: string;
  confidence: number;
  confidence_label: ConfidenceLabel;
  citations: Citation[];
}

// Resolve the backend base URL. In GitHub Codespaces the browser loads the
// frontend from `<name>-3000.app.github.dev`; the backend is the sibling
// `<name>-8000.app.github.dev`, so derive it from the current host first (works
// without touching NEXT_PUBLIC_API_BASE_URL, which docker-compose pins to
// localhost:8000). Falls back to the build-time env var, then localhost for
// local/desktop port-forwarding use.
function resolveApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const match = window.location.host.match(/^(.+)-3000\.(.+)$/);
    if (match) return `${window.location.protocol}//${match[1]}-8000.${match[2]}`;
  }
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

const API_BASE_URL = resolveApiBaseUrl();

export async function askQuestion(question: string, conversationId: string | null): Promise<AskResponse> {
  const response = await fetch(`${API_BASE_URL}/api/qa/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });

  if (!response.ok) {
    throw new Error(`فشل الاتصال بالخادم (${response.status})`);
  }

  return response.json();
}

// ---- Contracts ----

export interface ContractSummary {
  id: number;
  filename: string;
  contract_type: string | null;
  page_count: number | null;
  last_ingested_at: string | null;
}

export async function listContracts(): Promise<ContractSummary[]> {
  const response = await fetch(`${API_BASE_URL}/api/contracts`);
  if (!response.ok) {
    throw new Error(`تعذّر جلب قائمة العقود (${response.status})`);
  }
  return response.json();
}

// ---- Risk scanning ----

export type Severity = "high" | "medium" | "low";

export interface RiskResultRow {
  rule_key: string;
  severity: Severity;
  explanation_ar: string;
  clause_number: string | null;
  page_number: number | null;
  confidence: number;
}

export async function getRiskResults(contractId: number): Promise<RiskResultRow[]> {
  const response = await fetch(`${API_BASE_URL}/api/risk/${contractId}`);
  if (!response.ok) {
    throw new Error(`تعذّر جلب نتائج المخاطر (${response.status})`);
  }
  return response.json();
}

export async function triggerRiskScan(contractId: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/risk/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contract_id: contractId }),
  });
  if (!response.ok) {
    throw new Error(`تعذّر بدء فحص المخاطر (${response.status})`);
  }
}

// ---- Background-job status (shared shape for risk + ingestion) ----

export type JobState = "idle" | "running" | "done" | "error";

export interface IngestionFileEntry {
  name: string;
  reason?: string;
}

export interface IngestionSummary {
  ingested: IngestionFileEntry[];
  skipped: IngestionFileEntry[];
  failed: IngestionFileEntry[];
  error?: string;
}

export interface JobStatus {
  status: JobState;
  // risk scan
  findings_count?: number;
  // ingestion
  summary?: IngestionSummary | null;
  error?: string;
}

export async function getRiskScanStatus(contractId: number): Promise<JobStatus> {
  const response = await fetch(`${API_BASE_URL}/api/risk/scan/status?contract_id=${contractId}`);
  if (!response.ok) {
    throw new Error(`تعذّر جلب حالة الفحص (${response.status})`);
  }
  return response.json();
}

// ---- Ingestion ----

export async function triggerIngestion(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/ingest/run`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`تعذّر بدء الاستيعاب (${response.status})`);
  }
}

export async function getIngestionStatus(): Promise<JobStatus> {
  const response = await fetch(`${API_BASE_URL}/api/ingest/status`);
  if (!response.ok) {
    throw new Error(`تعذّر جلب حالة الاستيعاب (${response.status})`);
  }
  return response.json();
}
