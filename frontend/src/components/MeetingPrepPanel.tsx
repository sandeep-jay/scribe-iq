"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type { MeetingPrepPayload } from "@/lib/backend";
import { fetchMeetingPrep } from "@/lib/backend";

export function MeetingPrepPanel({ patientId }: { patientId: string }) {
  const [data, setData] = useState<MeetingPrepPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    async (refresh: boolean) => {
      setBusy(true);
      setErr(null);
      try {
        const res = await fetchMeetingPrep(patientId, refresh);
        setData(res);
      } catch (e) {
        setErr((e as Error).message);
      } finally {
        setBusy(false);
      }
    },
    [patientId],
  );

  useEffect(() => {
    void load(false);
  }, [load]);

  const paragraphs = useMemo(() => {
    const raw = (data?.summary ?? "").trim();
    if (!raw) return [];
    return raw
      .split(/\n\n+/)
      .map((p) => p.trim())
      .filter(Boolean);
  }, [data?.summary]);

  return (
    <section className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-6 text-sm text-indigo-950 dark:border-indigo-900 dark:bg-indigo-950/25 dark:text-indigo-50">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-indigo-800/80 dark:text-indigo-200/90">Pre-Meeting Summary</p>
          <p className="mt-1 text-[11px] text-indigo-900/70 dark:text-indigo-200/70">
            Grounded on stored notes + the curated longitudinal window. Cached until the note fingerprint changes.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-indigo-300 bg-white px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-indigo-800 dark:border-indigo-800 dark:bg-indigo-950 dark:text-indigo-100">
            AI
          </span>
          <button
            type="button"
            disabled={busy}
            onClick={() => void load(true)}
            className="rounded-lg border border-indigo-300 bg-white px-3 py-1.5 text-xs font-medium text-indigo-900 hover:bg-indigo-50 disabled:opacity-40 dark:border-indigo-800 dark:bg-indigo-950 dark:text-indigo-50 dark:hover:bg-indigo-900"
          >
            {busy ? "Working…" : "Regenerate"}
          </button>
        </div>
      </div>

      {err ? <p className="mt-3 text-sm text-red-700 dark:text-red-300">{err}</p> : null}

      {data?.degraded ? (
        <p className="mt-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-950 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100">
          Offline prep: Groq is not configured or the model call failed. Set <span className="font-mono">GROQ_API_KEY</span> in{" "}
          <span className="font-mono">backend/.env</span> and restart the API for AI-polished summaries.
        </p>
      ) : null}

      {!err && !data && busy ? <p className="mt-3 text-sm text-indigo-900/70">Generating summary…</p> : null}

      {data && !err ? (
        <div className="mt-4 space-y-3 text-sm leading-relaxed text-indigo-950 dark:text-indigo-50">
          {paragraphs.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
          <p className="text-[11px] text-indigo-900/60 dark:text-indigo-200/60">
            Model {data.model} · prompt {data.prompt_version} · {data.cached ? "served from cache" : "freshly generated"} ·{" "}
            {new Date(data.generated_at).toLocaleString()}
          </p>
        </div>
      ) : null}
    </section>
  );
}
