'use client';

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";

import type { ChatCitation } from "@/lib/backend";
import { apiBase, postChat } from "@/lib/backend";

type Role = "user" | "assistant";

type Row = {
  role: Role;
  text: string;
};

function ChatSurface() {
  const searchParams = useSearchParams();
  const presetPatientId = searchParams.get("patient_id") ?? "";

  const patientId = presetPatientId;

  const [input, setInput] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const [lastCit, setLastCit] = useState<ChatCitation[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiOrigin = useMemo(() => apiBase(), []);

  const send = async () => {
    const msg = input.trim();
    if (!msg) return;
    setBusy(true);
    setError(null);
    const prior = [...rows];
    const history: Array<{ role: "user" | "assistant"; content: string }> = prior.map((r) =>
      r.role === "assistant"
        ? { role: "assistant", content: r.text }
        : { role: "user", content: r.text },
    );
    try {
      setRows((xs) => [...xs, { role: "user", text: msg }]);
      const payload: Parameters<typeof postChat>[0] = {
        message: msg,
        conversation: history,
      };
      if (patientId) payload.patient_id = patientId;
      const resp = await postChat(payload);
      setLastCit(resp.citations);
      setRows((xs) => [...xs, { role: "assistant", text: resp.answer }]);
      setInput("");
    } catch (e) {
      setError((e as Error).message);
      setRows(prior);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-50">
          <p className="font-medium">RAG chat retrieval is intentionally deferred in this sprint.</p>
          <p className="mt-2 text-xs text-amber-900/80 dark:text-amber-100/80">
            Vector chat requires OpenAI embeddings (`OPENAI_API_KEY` + `python -m scripts.load_corpus --embed`). Until then,
            <span className="font-medium"> POST /chat </span> returns 503. Use the patient chart{" "}
            <span className="font-medium">Pre-Meeting Summary</span> (Groq + cached) for AI-grounded narrative instead.
          </p>
        </div>

<div className="grid gap-10 lg:grid-cols-[2fr_minmax(16rem_1fr)]">
      <div className="space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">Chat-on-corpus</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Browser → <span className="font-mono text-xs">{apiOrigin}</span>
            . Requires seeded embeddings (`scribe-load-corpus --embed`).
          </p>
          <p className="text-xs text-zinc-500">
            Patient scope:&nbsp;
            {patientId ? (
              <>
                grounded to{" "}
                <span className="font-mono">
                  {patientId.length > 12 ? `${patientId.slice(0, 8)}…` : patientId}
                </span>{" "}
                <Link className="text-indigo-600" href={`/patients/${encodeURIComponent(patientId)}`}>
                  Chart
                </Link>
              </>
            ) : (
              "whole corpus."
            )}
          </p>
        </div>

        <div className="min-h-[420px] space-y-3 rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
          {rows.length === 0 ? (
            <p className="text-sm text-zinc-600">Ask a factual question referencing the seeded notes.</p>
          ) : (
            rows.map((r, idx) => (
              <div
                key={`${idx}-${r.role}`}
                className={`max-w-xl rounded-xl px-3 py-2 text-sm ${
                  r.role === "user"
                    ? "ml-auto bg-indigo-50 text-indigo-900 dark:bg-indigo-900/30 dark:text-indigo-100"
                    : "mr-auto bg-zinc-50 text-zinc-900 dark:bg-zinc-900"
                }`}
              >
                {r.text}
              </div>
            ))
          )}
        </div>

        {error ? <p className="text-sm text-red-600">{error}</p> : null}

        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <textarea
            className="flex-1 rounded-xl border border-zinc-300 p-3 text-sm dark:border-zinc-700"
            rows={3}
            placeholder="Compose question…"
            value={input}
            disabled={busy}
            onChange={(e) => setInput(e.target.value)}
          />
          <button
            type="button"
            disabled={busy}
            onClick={send}
            className="rounded-xl bg-zinc-900 px-6 py-3 text-sm font-medium text-white disabled:opacity-40 dark:bg-white dark:text-black"
          >
            {busy ? "…" : "Send"}
          </button>
        </div>
      </div>

      <aside className="space-y-4 rounded-xl border border-zinc-200 p-4 text-sm dark:border-zinc-800">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Citations</h2>
        {lastCit.length === 0 ? (
          <p className="text-zinc-500">Send a prompt to hydrate retrieved excerpts.</p>
        ) : (
          <div className="space-y-3">
            {lastCit.map((c) => (
              <div key={c.note_id} className="space-y-1 rounded-xl bg-zinc-50 p-3 text-xs dark:bg-zinc-900">
                <p className="break-all font-mono">{c.note_id}</p>
                <p className="text-[11px] text-zinc-500">
                  cosine similarity {(Math.max(0, Math.min(1, c.similarity)) * 100).toFixed(1)}%
                </p>
                <p className="whitespace-pre-wrap text-zinc-800 dark:text-zinc-100">{c.excerpt}</p>
              </div>
            ))}
          </div>
        )}
      </aside>
    </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="text-sm text-zinc-500">Loading…</div>}>
      <ChatSurface />
    </Suspense>
  );
}
