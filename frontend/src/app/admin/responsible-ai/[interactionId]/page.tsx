"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchResponsibleAiInteraction } from "@/lib/backend";

export default function ResponsibleAiInteractionDetailPage() {
  const params = useParams<{ interactionId: string }>();
  const id = params.interactionId;
  const [row, setRow] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetchResponsibleAiInteraction(id);
        if (!cancelled) setRow(r);
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : "Failed to load interaction.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-white">AI interaction detail</h1>
          <p className="mt-1 font-mono text-xs text-zinc-500">{id}</p>
        </div>
        <Link href="/admin/responsible-ai" className="text-sm text-indigo-600 hover:underline dark:text-indigo-400">
          Back to Control Center
        </Link>
      </div>

      {err ? (
        <div className="rounded-lg border border-rose-300 bg-rose-50 p-4 text-sm text-rose-950 dark:border-rose-700 dark:bg-rose-950/40 dark:text-rose-100">
          {err}
        </div>
      ) : null}

      {!row && !err ? <p className="text-sm text-zinc-500">Loading…</p> : null}

      {row ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-white">Traceability</h2>
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-zinc-500">Workflow</dt>
                <dd className="font-mono text-xs text-zinc-900 dark:text-zinc-100">{String(row.interaction_type ?? "—")}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-zinc-500">Status</dt>
                <dd className="font-mono text-xs">{String(row.status ?? "—")}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-zinc-500">Prompt version</dt>
                <dd className="font-mono text-xs">{String(row.prompt_version ?? "—")}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-zinc-500">System prompt hash</dt>
                <dd className="break-all font-mono text-[11px]">{String(row.system_prompt_hash ?? "—")}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-zinc-500">Input hash</dt>
                <dd className="break-all font-mono text-[11px]">{String(row.input_hash ?? "—")}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-zinc-500">Output hash</dt>
                <dd className="break-all font-mono text-[11px]">{String(row.output_hash ?? "—")}</dd>
              </div>
            </dl>
          </div>

          <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-white">Redacted previews</h2>
            <div className="mt-3 space-y-3 text-sm">
              <div>
                <p className="text-xs font-semibold uppercase text-zinc-500">Input</p>
                <pre className="mt-1 max-h-56 overflow-auto whitespace-pre-wrap rounded-md bg-zinc-50 p-3 text-xs text-zinc-800 dark:bg-zinc-900 dark:text-zinc-100">
                  {String(row.input_redacted_preview ?? "—")}
                </pre>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase text-zinc-500">Output</p>
                <pre className="mt-1 max-h-56 overflow-auto whitespace-pre-wrap rounded-md bg-zinc-50 p-3 text-xs text-zinc-800 dark:bg-zinc-900 dark:text-zinc-100">
                  {String(row.output_redacted_preview ?? "—")}
                </pre>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-zinc-200 bg-white p-4 lg:col-span-2 dark:border-zinc-800 dark:bg-zinc-950">
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-white">Raw metadata</h2>
            <pre className="mt-3 max-h-[520px] overflow-auto rounded-md bg-zinc-50 p-3 text-xs text-zinc-800 dark:bg-zinc-900 dark:text-zinc-100">
              {JSON.stringify(row, null, 2)}
            </pre>
          </div>
        </div>
      ) : null}
    </div>
  );
}
