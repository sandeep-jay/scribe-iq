'use client';

/**
 * Encounter note generation UI. Errors use structured ``logError`` with a stable
 * ``feature_area`` so support can filter console exports without scraping user text.
 */

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import {
  apiBase,
  fetchBackendHealth,
  postGenerateNote,
  responsibleAiAdminUiEnabled,
  type BackendHealth,
  type NoteGenerationAudit,
} from "@/lib/backend";
import { logError } from "@/lib/logger";

type Props = {
  patientId: string;
  /** Pre-fill encounter id (used from encounter viewer for targeted regenerates). */
  seedEncounterId?: string;
  /** Optionally seed textarea (typically an existing transcript you are revising). */
  seedTranscript?: string;
};

export function GenerateNotePanel({ patientId, seedEncounterId, seedTranscript }: Props) {
  const router = useRouter();

  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [transcript, setTranscript] = useState(seedTranscript ?? "");
  const [specialty, setSpecialty] = useState("");
  const [sessionDate, setSessionDate] = useState("");
  const [externalEncounterId, setExternalEncounterId] = useState(seedEncounterId ?? "");
  const [replaceExisting, setReplaceExisting] = useState(Boolean(seedEncounterId));

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);
  const [lastAudit, setLastAudit] = useState<NoteGenerationAudit | null>(null);

  useEffect(() => {
    let alive = true;
    setLoadError(null);

    const load = async () => {
      try {
        const h = await fetchBackendHealth();
        if (!alive) return;
        setHealth(h);
      } catch (e) {
        if (!alive) return;
        logError("generate_note_health_load_failed", {
          feature_area: "generate_note",
          patient_id: patientId,
          error: (e as Error).message,
        });
        setHealth(null);
        setLoadError((e as Error).message);
      }
    };

    const usingIdle = typeof window !== "undefined" && "requestIdleCallback" in window;
    const sched =
      usingIdle
        ? window.requestIdleCallback(() => void load(), { timeout: 1200 })
        : window.setTimeout(() => void load(), 1);

    return () => {
      alive = false;
      if (usingIdle) window.cancelIdleCallback(sched as number);
      else window.clearTimeout(sched as number);
    };
  }, [patientId]);

  useEffect(() => {
    setExternalEncounterId(seedEncounterId ?? "");
    setReplaceExisting(Boolean(seedEncounterId));
  }, [seedEncounterId]);

  useEffect(() => {
    setTranscript(seedTranscript ?? "");
  }, [seedTranscript]);

  if (!health && loadError === null) {
    return (
      <section className="rounded-xl border border-dashed border-zinc-300 p-4 text-xs text-zinc-500 dark:border-zinc-700">
        Checking backend capability… (<span className="font-mono">{apiBase()}</span>)
      </section>
    );
  }

  if (loadError) {
    return (
      <section className="space-y-2 rounded-xl border border-red-200 bg-red-50 p-5 text-xs text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-100">
        <h2 className="text-[11px] font-semibold uppercase tracking-wide text-red-800 dark:text-red-200">
          Could not probe FastAPI `/health`
        </h2>
        <p className="leading-relaxed">
          {(loadError ?? "").slice(0, 600)}
          {(loadError?.length ?? 0) > 600 ? "…" : ""}
        </p>
        <p className="leading-relaxed opacity-90">
          Verify <span className="font-mono">NEXT_PUBLIC_SCRIBE_API_BASE</span> / CORS, or start uvicorn on{" "}
          <span className="font-mono">{apiBase()}</span>.
        </p>
        <p className="leading-relaxed opacity-90">
          <span className="font-semibold">Note:</span> &quot;Failed to fetch&quot; means the browser did not get an HTTP response from FastAPI (offline API, wrong URL, mixed content, or CORS). The configured LLM provider is only used after the request reaches the backend.
        </p>
      </section>
    );
  }

  if (!health) {
    return null;
  }

  const enabled = Boolean(health.note_generation_enabled);

  if (!enabled) {
    return (
      <section className="space-y-2 rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-950 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
        <h2 className="text-[11px] font-semibold uppercase tracking-wide text-amber-900 dark:text-amber-200">
          LLM encounter drafting
        </h2>
        <p className="text-xs leading-relaxed">
          The backend reports <strong className="font-mono">note_generation_enabled = false</strong>. Set{' '}
          <span className="font-mono">NOTE_GENERATION_ENABLED=true</span> in{' '}
          <span className="font-mono">backend/.env</span> with a valid{' '}
          <span className="font-mono">LLM_PROVIDER</span> and provider credentials, restart uvicorn, and refresh — then transcripts can
          be drafted into persisted notes for{' '}
          <span className="font-mono">{patientId.slice(0, 8)}…</span>.
        </p>
        {health.api_auth_configured ? (
          <p className="text-xs leading-relaxed opacity-90">
            Shared-secret auth appears enabled server-side — mirror{' '}
            <span className="font-mono">BACKEND_API_KEY</span> into{' '}
            <span className="font-mono">NEXT_PUBLIC_SCRIBE_BACKEND_API_KEY</span> for browser calls (trusted demos only).
          </p>
        ) : null}
      </section>
    );
  }

  const submit = async () => {
    const t = transcript.trim();
    if (!t) return;

    const encTrim = externalEncounterId.trim();

    setBusy(true);
    setError(null);
    setLastResult(null);

    try {
      const resp = await postGenerateNote({
        patient_id: patientId,
        transcript: t,
        specialty: specialty.trim() || undefined,
        session_date: sessionDate.trim() || undefined,
        external_encounter_id: encTrim.length ? encTrim : undefined,
        replace_existing: Boolean(replaceExisting && encTrim.length),
      });

      const mode = resp.replaced_existing ? "Updated" : "Created";
      setLastResult(
        `${mode} note ${resp.note_id} · encounter ${resp.external_encounter_id}${resp.embedding_written ? " · embedding written" : ""}.`,
      );
      setLastAudit(resp.audit ?? null);
      if (!resp.replaced_existing) {
        setTranscript("");
      }
      router.refresh();
    } catch (e) {
      logError("generate_note_submit_failed", { error: (e as Error).message });
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="min-w-0 max-w-full space-y-4 rounded-xl border border-indigo-200 bg-indigo-50/70 p-5 text-sm text-indigo-950 dark:border-indigo-950 dark:bg-indigo-950/30 dark:text-indigo-50">
      <header className="space-y-1">
        <h2 className="text-[11px] font-semibold uppercase tracking-wide">LLM encounter drafting</h2>
        <p className="text-[11px] text-indigo-800 dark:text-indigo-100">
          <span className="font-mono">POST /notes/generate</span> → configured LLM structured JSON persisted on Postgres.
        </p>
      </header>

      <label className="block space-y-1 text-[11px] font-semibold uppercase tracking-wide text-indigo-950 dark:text-indigo-100">
        Transcript *
        <textarea
          disabled={busy}
          value={transcript}
          placeholder="Paste a conversation verbatim…"
          onChange={(e) => setTranscript(e.target.value)}
          rows={11}
          className="w-full rounded-lg border border-indigo-200 bg-white p-3 text-[13px] leading-relaxed text-zinc-900 placeholder:text-xs placeholder:normal-case placeholder:text-zinc-400 dark:border-indigo-800 dark:bg-zinc-950 dark:text-white"
        />
      </label>

      <div className="grid gap-3 sm:grid-cols-3">
        <label className="space-y-1 text-[11px] font-semibold uppercase tracking-wide text-indigo-950 dark:text-indigo-100">
          Specialty
          <input
            disabled={busy}
            value={specialty}
            onChange={(e) => setSpecialty(e.target.value)}
            placeholder="Family medicine"
            className="w-full rounded-lg border border-indigo-200 bg-white px-3 py-2 text-sm dark:border-indigo-800 dark:bg-zinc-950"
          />
        </label>

        <label className="space-y-1 text-[11px] font-semibold uppercase tracking-wide text-indigo-950 dark:text-indigo-100">
          Session date
          <input
            disabled={busy}
            type="date"
            value={sessionDate}
            onChange={(e) => setSessionDate(e.target.value)}
            className="w-full rounded-lg border border-indigo-200 bg-white px-3 py-2 text-sm dark:border-indigo-800 dark:bg-zinc-950"
          />
        </label>

        <label className="space-y-1 text-[11px] font-semibold uppercase tracking-wide text-indigo-950 dark:text-indigo-100">
          Encounter key
          <input
            disabled={busy}
            value={externalEncounterId}
            onChange={(e) => setExternalEncounterId(e.target.value)}
            placeholder="Leave blank → generated-<uuid>"
            className="w-full rounded-lg border border-indigo-200 bg-white px-3 py-2 text-xs dark:border-indigo-800 dark:bg-zinc-950"
          />
        </label>
      </div>

      <label className="flex items-center gap-2 text-[11px] text-indigo-950 dark:text-indigo-100">
        <input
          type="checkbox"
          disabled={busy || !externalEncounterId.trim()}
          checked={replaceExisting && Boolean(externalEncounterId.trim())}
          onChange={(e) => setReplaceExisting(e.target.checked)}
        />
        Replace structured note for the encounter key above (explicit regenerate).
      </label>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={busy || !transcript.trim()}
          onClick={() => submit()}
          className="rounded-lg bg-indigo-950 px-4 py-2 text-[11px] font-semibold uppercase tracking-wide text-white disabled:opacity-40 dark:bg-white dark:text-black"
        >
          {busy ? "Generating…" : "Generate structured note"}
        </button>
        <Link href={`/patients/${encodeURIComponent(patientId)}`} className="text-[11px] underline">
          Reload chart metadata
        </Link>
      </div>

      {error ? (
        <p className="text-xs leading-snug text-red-600">{error.slice(0, 1200)}</p>
      ) : null}

      {lastResult ? (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900 dark:border-emerald-950 dark:bg-emerald-950/40 dark:text-emerald-100">
          {lastResult}
        </p>
      ) : null}
      {responsibleAiAdminUiEnabled() && lastAudit ? (
        <p className="text-xs">
          <Link
            href={`/admin/responsible-ai/${lastAudit.interaction_id}`}
            className="font-medium text-indigo-700 underline decoration-indigo-300 underline-offset-2 hover:text-indigo-900 dark:text-indigo-300"
          >
            Why this draft?
          </Link>
        </p>
      ) : null}
    </section>
  );
}
