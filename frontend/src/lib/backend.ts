/**
 * FastAPI helpers for server/client components.
 *
 * All network calls go through ``trackedJson`` which:
 * - adds ``X-Request-ID`` (browser-generated fallback if missing) for correlation with backend logs
 * - emits structured JSON lines to the console (``logInfo`` / ``logWarn`` / ``logError``)
 * - intentionally avoids logging request/response bodies (PHI risk)
 *
 * Verbosity: set ``NEXT_PUBLIC_LOG_LEVEL=debug`` to also emit ``logDebug`` checkpoints from this module.
 */

import { logDebug, logError, logInfo, logWarn } from "./logger";

export function apiBase(): string {
  return (
    process.env.NEXT_PUBLIC_SCRIBE_API_BASE?.replace(/\/$/, "") ??
    "http://127.0.0.1:8000"
  );
}

function newRequestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `fe-${Date.now()}`;
}

function responseShapeMeta(value: unknown): Record<string, unknown> {
  if (value === null || value === undefined) return { result_kind: "nullish" };
  if (Array.isArray(value)) return { result_kind: "array", result_length: value.length };
  if (typeof value === "object") {
    const keys = Object.keys(value as object);
    return {
      result_kind: "object",
      result_key_count: keys.length,
      result_keys_preview: keys.slice(0, 20),
    };
  }
  return { result_kind: typeof value };
}

function requestPath(url: string): string {
  try {
    return new URL(url).pathname;
  } catch {
    return url;
  }
}

async function trackedJson<T>(event: string, url: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers ?? {});
  if (!headers.has("X-Request-ID")) headers.set("X-Request-ID", newRequestId());
  const method = (init.method ?? "GET").toUpperCase();
  const path = requestPath(url);
  const t0 = typeof performance !== "undefined" ? performance.now() : Date.now();
  logDebug("api_request_start", { event, method, path, request_id: headers.get("X-Request-ID") });
  try {
    const resp = await fetch(url, { ...init, headers });
    const elapsed =
      typeof performance !== "undefined"
        ? Math.round(performance.now() - t0)
        : Math.round(Date.now() - t0);
    const requestId = resp.headers.get("x-request-id") ?? headers.get("X-Request-ID");
    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      logWarn("api_response_error", {
        event,
        method,
        path,
        status: resp.status,
        duration_ms: elapsed,
        request_id: requestId,
      });
      throw new Error(`API ${resp.status}: ${text || resp.statusText}`);
    }
    logInfo("api_request_ok", {
      event,
      method,
      path,
      status: resp.status,
      duration_ms: elapsed,
      request_id: requestId,
    });
    const body = (await resp.json()) as T;
    logDebug("api_response_parsed", {
      event,
      method,
      path,
      status: resp.status,
      duration_ms: elapsed,
      request_id: requestId,
      ...responseShapeMeta(body),
    });
    return body;
  } catch (e) {
    const elapsed =
      typeof performance !== "undefined"
        ? Math.round(performance.now() - t0)
        : Math.round(Date.now() - t0);
    logError("api_request_failed", {
      event,
      method,
      path,
      duration_ms: elapsed,
      error: e instanceof Error ? e.message : String(e),
    });
    throw e;
  }
}

function authHeaders(): Record<string, string> {
  const key = process.env.NEXT_PUBLIC_SCRIBE_BACKEND_API_KEY?.trim();
  if (!key) return {};
  return { "X-API-Key": key };
}

export type BackendHealth = {
  status: string;
  service?: string;
  llm_provider?: string;
  llm_configured?: boolean;
  llm_json_mode?: "native" | "prompt_enforced" | "unavailable" | string;
  embedding_provider?: string;
  embedding_configured?: boolean;
  embedding_model?: string | null;
  embedding_dim?: number;
  note_generation_enabled?: boolean;
  meeting_prep_enabled?: boolean;
  responsible_ai_admin_enabled?: boolean;
  api_auth_configured?: boolean;
};

export async function fetchBackendHealth(): Promise<BackendHealth> {
  return trackedJson<BackendHealth>("health", `${apiBase()}/health`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
}

export type PatientListItem = {
  id: string;
  external_id: string;
  name: string;
  metadata: Record<string, unknown>;
  note_count: number;
  last_session_date: string | null;
  /** Any note row carries a longitudinal_context blob */
  has_longitudinal?: boolean;
  /** Lexicographic max of note.specialty in the grouped query (demo filter only) */
  last_specialty?: string | null;
};

export type PaginatedPatients = {
  patients: PatientListItem[];
  total: number;
  limit: number;
  offset: number;
};

export type CorpusPatientStats = {
  domain: string;
  total_patients: number;
  total_notes: number;
};

export type MeetingPrepAiAudit = {
  interaction_id: string;
  cached: boolean;
  source_fingerprint: string | null;
  prompt_version: string;
  source_count: number;
  safety_status: string;
};

export type MeetingPrepPayload = {
  patient_id: string;
  summary: string;
  generated_at: string;
  cached: boolean;
  prompt_version: string;
  model: string;
  /** True when summary was assembled locally (no LLM provider configured or provider call failed). */
  degraded?: boolean;
  ai_audit?: MeetingPrepAiAudit | null;
};


export type NotePreview = {
  id: string;
  external_encounter_id: string;
  corpus_note_id: string | null;
  session_date: string | null;
  specialty: string | null;
  summary: string | null;
  has_dialogue: boolean;
};

export type PatientDetail = {
  id: string;
  external_id: string;
  name: string;
  metadata: Record<string, unknown>;
  note_count: number;
  latest_longitudinal: Record<string, unknown> | null;
  longitudinal_medication_hints: string[];
  notes: NotePreview[];
};

export type NoteDetail = {
  id: string;
  patient_id: string;
  domain: string;
  external_encounter_id: string;
  corpus_note_id: string | null;
  specialty: string | null;
  source: string;
  session_date: string | null;
  created_at: string | null;
  conversation_text: string;
  structured_note: Record<string, unknown>;
  entity_payload: Record<string, unknown>;
  longitudinal_context: Record<string, unknown> | null;
  embedding_present: boolean;
};

export type ChatCitation = {
  note_id: string;
  similarity: number;
  excerpt: string;
  summary: string | null;
  external_encounter_id: string | null;
};

export type ChatAuditBlock = {
  interaction_id: string;
  model: string | null;
  prompt_version: string;
  source_count: number;
  safety_status: string;
  latency_ms: number;
};

export type ChatResponsePayload = {
  answer: string;
  citations: ChatCitation[];
  audit?: ChatAuditBlock | null;
};

export type GenerateNoteRequestPayload = {
  patient_id: string;
  transcript: string;
  specialty?: string | null;
  /** ISO yyyy-mm-dd when provided */
  session_date?: string | null;
  external_encounter_id?: string | null;
  replace_existing?: boolean;
};

export type NoteGenerationAudit = {
  interaction_id: string;
  prompt_version: string;
  requires_human_review: boolean;
  safety_status: string;
};

export type GenerateNoteResponsePayload = {
  note_id: string;
  external_encounter_id: string;
  structured_note: Record<string, unknown>;
  embedding_written: boolean;
  replaced_existing: boolean;
  audit?: NoteGenerationAudit | null;
};


export async function fetchCorpusPatientStats(): Promise<CorpusPatientStats> {
  const q = new URLSearchParams({ domain: "clinical" });
  return trackedJson<CorpusPatientStats>("patients_stats", `${apiBase()}/patients/stats?${q}`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
}

export async function fetchMeetingPrep(patientId: string, refresh = false): Promise<MeetingPrepPayload> {
  const q = new URLSearchParams({ domain: "clinical" });
  if (refresh) q.set("refresh", "true");
  const enc = encodeURIComponent(patientId);
  return trackedJson<MeetingPrepPayload>("meeting_prep", `${apiBase()}/patients/${enc}/meeting-prep?${q}`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
}

export async function fetchPatients(
  opts: { limit?: number; offset?: number } = {},
): Promise<PaginatedPatients> {
  const base = apiBase();
  const q = new URLSearchParams({
    domain: "clinical",
    limit: String(opts.limit ?? 200),
    offset: String(opts.offset ?? 0),
  });
  return trackedJson<PaginatedPatients>("patients_list", `${base}/patients?${q}`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
}

export async function fetchPatient(patientId: string): Promise<PatientDetail> {
  const enc = encodeURIComponent(patientId);
  return trackedJson<PatientDetail>("patient_detail", `${apiBase()}/patients/${enc}`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
}

export async function fetchNote(noteId: string): Promise<NoteDetail> {
  return trackedJson<NoteDetail>("note_detail", `${apiBase()}/notes/${noteId}`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
}

export async function postChat(payload: {
  message: string;
  patient_id?: string;
  conversation?: Array<{ role: "user" | "assistant" | "system"; content: string }>;
  top_k?: number;
}): Promise<ChatResponsePayload> {
  return trackedJson<ChatResponsePayload>("chat", `${apiBase()}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
}

export async function postGenerateNote(
  body: GenerateNoteRequestPayload,
): Promise<GenerateNoteResponsePayload> {
  return trackedJson<GenerateNoteResponsePayload>("notes_generate", `${apiBase()}/notes/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(body),
  });
}


export function responsibleAiAdminUiEnabled(): boolean {
  return process.env.NEXT_PUBLIC_SCRIBE_ADMIN_UI === "true";
}

export type ResponsibleAiTrustContext = {
  phi_redaction_enabled: boolean;
  prompt_and_model_traceability: boolean;
  audit_storage: string;
  safety_checks_enabled: boolean;
};

export type ResponsibleAiSafetyBreakdownItem = {
  code: string;
  label: string;
  count: number;
};

export type ResponsibleAiMetricsPayload = {
  summary: {
    total_interactions: number;
    success_rate: number;
    avg_latency_ms: number;
    avg_latency_ms_generated?: number;
    citation_coverage: number;
    safety_flag_count: number;
    human_review_required: number;
    clinical_review_signals?: number;
  };
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  time_series: Array<{
    date: string;
    chat: number;
    meeting_prep: number;
    note_generation: number;
  }>;
  safety_breakdown?: ResponsibleAiSafetyBreakdownItem[];
  trust_context?: ResponsibleAiTrustContext;
};

export async function fetchResponsibleAiMetrics(): Promise<ResponsibleAiMetricsPayload> {
  return trackedJson<ResponsibleAiMetricsPayload>("admin_metrics", `${apiBase()}/admin/responsible-ai/metrics`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
}

export type ResponsibleAiLatencyDisplay = {
  latency_ms: number | null;
  kind: string;
  label: string;
  cached: boolean;
};

export type ResponsibleAiInteractionRow = {
  id: string;
  request_id: string;
  interaction_type: string;
  patient_id: string | null;
  note_id: string | null;
  model_provider: string | null;
  model_name: string | null;
  prompt_version: string | null;
  status: string | null;
  latency_ms: number | null;
  created_at: string | null;
  citation_count?: number;
  source_count?: number;
  run_mode?: string;
  latency_display?: ResponsibleAiLatencyDisplay;
  risk_tier?: string;
  output_preview?: string | null;
};

export type ResponsibleAiInteractionsPayload = {
  items: ResponsibleAiInteractionRow[];
  total: number;
  limit: number;
  offset: number;
};

export async function fetchResponsibleAiInteractions(opts: {
  limit?: number;
  offset?: number;
} = {}): Promise<ResponsibleAiInteractionsPayload> {
  const q = new URLSearchParams({
    limit: String(opts.limit ?? 50),
    offset: String(opts.offset ?? 0),
  });
  return trackedJson<ResponsibleAiInteractionsPayload>(
    "admin_interactions",
    `${apiBase()}/admin/responsible-ai/interactions?${q}`,
    {
      cache: "no-store",
      headers: { ...authHeaders() },
    },
  );
}

export async function fetchResponsibleAiInteraction(id: string): Promise<Record<string, unknown>> {
  const enc = encodeURIComponent(id);
  return trackedJson<Record<string, unknown>>("admin_interaction_detail", `${apiBase()}/admin/responsible-ai/interactions/${enc}`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
}

