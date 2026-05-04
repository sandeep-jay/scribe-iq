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

export type MeetingPrepPayload = {
  patient_id: string;
  summary: string;
  generated_at: string;
  cached: boolean;
  prompt_version: string;
  model: string;
  /** True when summary was assembled locally (no Groq or Groq call failed). */
  degraded?: boolean;
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

export type ChatResponsePayload = {
  answer: string;
  citations: ChatCitation[];
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

export type GenerateNoteResponsePayload = {
  note_id: string;
  external_encounter_id: string;
  structured_note: Record<string, unknown>;
  embedding_written: boolean;
  replaced_existing: boolean;
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
