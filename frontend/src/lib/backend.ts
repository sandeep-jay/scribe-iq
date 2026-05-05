/** FastAPI helpers for server/client components */

export function apiBase(): string {
  return (
    process.env.NEXT_PUBLIC_SCRIBE_API_BASE?.replace(/\/$/, "") ??
    "http://127.0.0.1:8000"
  );
}

function authHeaders(): Record<string, string> {
  const key = process.env.NEXT_PUBLIC_SCRIBE_BACKEND_API_KEY?.trim();
  if (!key) return {};
  return { "X-API-Key": key };
}

async function wrap<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`API ${resp.status}: ${text || resp.statusText}`);
  }
  return (await resp.json()) as T;
}

export type BackendHealth = {
  status: string;
  service?: string;
  llm_provider?: string;
  note_generation_enabled?: boolean;
  meeting_prep_enabled?: boolean;
  responsible_ai_admin_enabled?: boolean;
  api_auth_configured?: boolean;
};

export async function fetchBackendHealth(): Promise<BackendHealth> {
  const resp = await fetch(`${apiBase()}/health`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
  return wrap<BackendHealth>(resp);
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
  /** True when summary was assembled locally (no Groq or Groq call failed). */
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
  const resp = await fetch(`${apiBase()}/patients/stats?${q}`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
  return wrap<CorpusPatientStats>(resp);
}

export async function fetchMeetingPrep(patientId: string, refresh = false): Promise<MeetingPrepPayload> {
  const q = new URLSearchParams({ domain: "clinical" });
  if (refresh) q.set("refresh", "true");
  const enc = encodeURIComponent(patientId);
  const resp = await fetch(`${apiBase()}/patients/${enc}/meeting-prep?${q}`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
  return wrap<MeetingPrepPayload>(resp);
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
  const resp = await fetch(`${base}/patients?${q}`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
  return wrap<PaginatedPatients>(resp);
}

export async function fetchPatient(patientId: string): Promise<PatientDetail> {
  const enc = encodeURIComponent(patientId);
  const resp = await fetch(`${apiBase()}/patients/${enc}`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
  return wrap<PatientDetail>(resp);
}

export async function fetchNote(noteId: string): Promise<NoteDetail> {
  const resp = await fetch(`${apiBase()}/notes/${noteId}`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
  return wrap<NoteDetail>(resp);
}

export async function postChat(payload: {
  message: string;
  patient_id?: string;
  conversation?: Array<{ role: "user" | "assistant" | "system"; content: string }>;
  top_k?: number;
}): Promise<ChatResponsePayload> {
  const resp = await fetch(`${apiBase()}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
  return wrap<ChatResponsePayload>(resp);
}

export async function postGenerateNote(
  body: GenerateNoteRequestPayload,
): Promise<GenerateNoteResponsePayload> {
  const resp = await fetch(`${apiBase()}/notes/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(body),
  });
  return wrap<GenerateNoteResponsePayload>(resp);
}


export function responsibleAiAdminUiEnabled(): boolean {
  return process.env.NEXT_PUBLIC_SCRIBE_ADMIN_UI === "true";
}

export type ResponsibleAiMetricsPayload = {
  summary: {
    total_interactions: number;
    success_rate: number;
    avg_latency_ms: number;
    citation_coverage: number;
    safety_flag_count: number;
    human_review_required: number;
  };
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  time_series: Array<{
    date: string;
    chat: number;
    meeting_prep: number;
    note_generation: number;
  }>;
};

export async function fetchResponsibleAiMetrics(): Promise<ResponsibleAiMetricsPayload> {
  const resp = await fetch(`${apiBase()}/admin/responsible-ai/metrics`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
  return wrap<ResponsibleAiMetricsPayload>(resp);
}

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
};

export async function fetchResponsibleAiInteractions(opts: {
  limit?: number;
  offset?: number;
} = {}): Promise<{ items: ResponsibleAiInteractionRow[]; total: number }> {
  const q = new URLSearchParams({
    limit: String(opts.limit ?? 50),
    offset: String(opts.offset ?? 0),
  });
  const resp = await fetch(`${apiBase()}/admin/responsible-ai/interactions?${q}`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
  return wrap<{ items: ResponsibleAiInteractionRow[]; total: number }>(resp);
}

export async function fetchResponsibleAiInteraction(id: string): Promise<Record<string, unknown>> {
  const enc = encodeURIComponent(id);
  const resp = await fetch(`${apiBase()}/admin/responsible-ai/interactions/${enc}`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
  return wrap<Record<string, unknown>>(resp);
}

