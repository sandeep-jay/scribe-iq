"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  fetchResponsibleAiInteractions,
  fetchResponsibleAiMetrics,
  type ResponsibleAiInteractionRow,
  type ResponsibleAiMetricsPayload,
} from "@/lib/backend";

function Kpi({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{value}</p>
    </div>
  );
}

export default function ResponsibleAiControlCenterPage() {
  const [metrics, setMetrics] = useState<ResponsibleAiMetricsPayload | null>(null);
  const [rows, setRows] = useState<ResponsibleAiInteractionRow[]>([]);
  const [total, setTotal] = useState(0);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [m, list] = await Promise.all([
          fetchResponsibleAiMetrics(),
          fetchResponsibleAiInteractions({ limit: 50 }),
        ]);
        if (!cancelled) {
          setMetrics(m);
          setRows(list.items);
          setTotal(list.total);
        }
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : "Failed to load admin metrics.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-white">Responsible AI Control Center</h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-600 dark:text-zinc-300">
          Auditability, safety, source-grounding, and model governance for clinical AI workflows.
        </p>
      </div>

      {err ? (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950 dark:border-amber-600 dark:bg-amber-950/40 dark:text-amber-100">
          <p className="font-semibold">Unable to load dashboard</p>
          <p className="mt-1">{err}</p>
          <p className="mt-2 text-xs">
            Ensure the backend has{" "}
            <code className="rounded bg-black/5 px-1 py-0.5 dark:bg-white/10">RESPONSIBLE_AI_ADMIN_ENABLED=true</code>{" "}
            and your frontend points at the correct API base URL / API key.
          </p>
        </div>
      ) : null}

      {metrics ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Kpi label="Total AI runs" value={metrics.summary.total_interactions} />
          <Kpi label="Success rate" value={(metrics.summary.success_rate * 100).toFixed(1) + "%"} />
          <Kpi label="Citation coverage" value={(metrics.summary.citation_coverage * 100).toFixed(1) + "%"} />
          <Kpi label="Safety-flagged rows" value={metrics.summary.safety_flag_count} />
          <Kpi label="Human review (heuristic)" value={metrics.summary.human_review_required} />
          <Kpi label="Avg latency (ms)" value={metrics.summary.avg_latency_ms} />
        </div>
      ) : (
        <p className="text-sm text-zinc-500">Loading metrics…</p>
      )}

      <div>
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">Recent interactions</h2>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-300">Total: {total}</p>
        <div className="mt-4 overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-zinc-50 text-xs font-semibold uppercase text-zinc-500 dark:bg-zinc-900/50">
              <tr>
                <th className="px-3 py-2">Time</th>
                <th className="px-3 py-2">Workflow</th>
                <th className="px-3 py-2">Patient</th>
                <th className="px-3 py-2">Model</th>
                <th className="px-3 py-2">Prompt</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Latency</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
              {rows.map((r) => (
                <tr key={r.id} className="bg-white dark:bg-zinc-950">
                  <td className="whitespace-nowrap px-3 py-2 text-zinc-700 dark:text-zinc-200">
                    {r.created_at ? new Date(r.created_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-3 py-2">{r.interaction_type}</td>
                  <td className="px-3 py-2 font-mono text-xs">{r.patient_id ?? "—"}</td>
                  <td className="px-3 py-2">{r.model_name ?? "—"}</td>
                  <td className="px-3 py-2">{r.prompt_version ?? "—"}</td>
                  <td className="px-3 py-2">{r.status ?? "—"}</td>
                  <td className="px-3 py-2">{r.latency_ms ?? "—"}</td>
                  <td className="px-3 py-2">
                    <Link className="text-indigo-600 hover:underline dark:text-indigo-400" href={`/admin/responsible-ai/${r.id}`}>
                      View
                    </Link>
                  </td>
                </tr>
              ))}
              {!rows.length && !err ? (
                <tr>
                  <td className="px-3 py-6 text-center text-zinc-500" colSpan={8}>
                    No interactions logged yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
