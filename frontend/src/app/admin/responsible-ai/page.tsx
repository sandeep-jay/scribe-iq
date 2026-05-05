"use client";

import Link from "next/link";
import { Fragment, useEffect, useState } from "react";

import {
  fetchBackendHealth,
  fetchResponsibleAiInteractions,
  fetchResponsibleAiMetrics,
  type BackendHealth,
  type ResponsibleAiInteractionRow,
  type ResponsibleAiMetricsPayload,
} from "@/lib/backend";

function Kpi({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{value}</p>
      {hint ? <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">{hint}</p> : null}
    </div>
  );
}

function riskBadge(tier: string) {
  const t = (tier || "").toLowerCase();
  const cls =
    t === "high"
      ? "bg-rose-100 text-rose-900 dark:bg-rose-950/50 dark:text-rose-100"
      : t === "medium"
        ? "bg-amber-100 text-amber-950 dark:bg-amber-950/40 dark:text-amber-100"
        : "bg-emerald-100 text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-100";
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold capitalize ${cls}`}>
      {t || "—"}
    </span>
  );
}

export default function ResponsibleAiControlCenterPage() {
  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [metrics, setMetrics] = useState<ResponsibleAiMetricsPayload | null>(null);
  const [rows, setRows] = useState<ResponsibleAiInteractionRow[]>([]);
  const [total, setTotal] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [h, m, list] = await Promise.all([
          fetchBackendHealth(),
          fetchResponsibleAiMetrics(),
          fetchResponsibleAiInteractions({ limit: 50 }),
        ]);
        if (!cancelled) {
          setHealth(h);
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

  const trust = metrics?.trust_context;
  const ragEnabled =
    health?.note_generation_enabled !== undefined ||
    health?.meeting_prep_enabled !== undefined;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-white">Responsible AI Control Center</h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-600 dark:text-zinc-300">
          Traceability, safety, source-grounding, and model governance for clinical AI workflows. Risk labels are{" "}
          <strong>heuristic</strong> (demo governance), not clinical severity scores.
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

      {health ? (
        <div className="rounded-lg border border-zinc-200 bg-zinc-50/80 p-4 text-sm dark:border-zinc-800 dark:bg-zinc-900/40">
          <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">System capabilities</p>
          <ul className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-zinc-800 dark:text-zinc-200">
            <li>
              <span className="text-zinc-500">LLM provider:</span> {health.llm_provider ?? "—"}
            </li>
            <li>
              <span className="text-zinc-500">Note generation:</span>{" "}
              {health.note_generation_enabled ? "Enabled" : "Off"}
            </li>
            <li>
              <span className="text-zinc-500">Meeting prep:</span>{" "}
              {health.meeting_prep_enabled ? "Enabled" : "Off"}
            </li>
            <li>
              <span className="text-zinc-500">RAG chat:</span>{" "}
              {ragEnabled ? "Configured (embeddings may still be required)" : "—"}
            </li>
            <li>
              <span className="text-zinc-500">Admin API:</span>{" "}
              {health.responsible_ai_admin_enabled ? "On" : "Off"}
            </li>
          </ul>
        </div>
      ) : !err ? (
        <p className="text-sm text-zinc-500">Loading system context…</p>
      ) : null}

      {trust ? (
        <div className="rounded-lg border border-indigo-200 bg-indigo-50/60 p-4 dark:border-indigo-900/50 dark:bg-indigo-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-800 dark:text-indigo-200">
            AI trust signals
          </p>
          <ul className="mt-2 space-y-1 text-sm text-indigo-950 dark:text-indigo-100">
            <li>Source-grounding: tracked per interaction (citations + retrieved note ids)</li>
            <li>Prompt + model traceability: {trust.prompt_and_model_traceability ? "Enabled" : "—"}</li>
            <li>PHI minimization in audit previews: {trust.phi_redaction_enabled ? "Enabled" : "—"}</li>
            <li>Deterministic safety checks: {trust.safety_checks_enabled ? "Enabled" : "—"}</li>
            <li>Audit retention: {trust.audit_storage}</li>
          </ul>
        </div>
      ) : null}

      {metrics ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Kpi label="Total AI runs" value={metrics.summary.total_interactions} />
          <Kpi label="Success rate" value={(metrics.summary.success_rate * 100).toFixed(1) + "%"} />
          <Kpi label="Citation coverage" value={(metrics.summary.citation_coverage * 100).toFixed(1) + "%"} />
          <Kpi label="Safety-flagged rows" value={metrics.summary.safety_flag_count} />
          <Kpi
            label="Clinical review signals"
            value={metrics.summary.clinical_review_signals ?? metrics.summary.human_review_required}
            hint="Note-generation workflows + legacy keyword scan"
          />
          <Kpi
            label="Avg latency (generated)"
            value={
              metrics.summary.avg_latency_ms_generated !== undefined
                ? metrics.summary.avg_latency_ms_generated + " ms"
                : metrics.summary.avg_latency_ms + " ms"
            }
            hint="Excludes cache-hit meeting prep rows (<5ms)"
          />
        </div>
      ) : (
        <p className="text-sm text-zinc-500">Loading metrics…</p>
      )}

      {metrics?.safety_breakdown?.length ? (
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
          <p className="text-sm font-semibold text-zinc-900 dark:text-white">Safety analysis (checks ran)</p>
          <p className="mt-1 text-xs text-zinc-500">
            Counts include zeros so an empty dashboard still shows the taxonomy—not “no checks.”
          </p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {metrics.safety_breakdown.map((s) => (
              <div
                key={s.code}
                className="flex items-center justify-between rounded-md border border-zinc-100 px-3 py-2 text-sm dark:border-zinc-800"
              >
                <span className="text-zinc-700 dark:text-zinc-200">{s.label}</span>
                <span className="font-mono text-zinc-900 dark:text-zinc-100">{s.count}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div>
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">Recent interactions</h2>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-300">Total: {total}</p>
        <div className="mt-4 overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-zinc-50 text-xs font-semibold uppercase text-zinc-500 dark:bg-zinc-900/50">
              <tr>
                <th className="px-2 py-2"></th>
                <th className="px-3 py-2">Time</th>
                <th className="px-3 py-2">Workflow</th>
                <th className="px-3 py-2">Mode</th>
                <th className="px-3 py-2">Risk</th>
                <th className="px-3 py-2">Sources</th>
                <th className="px-3 py-2">Citations</th>
                <th className="px-3 py-2">Patient</th>
                <th className="px-3 py-2">Model</th>
                <th className="px-3 py-2">Prompt</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Latency</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
              {rows.map((r) => {
                const open = expanded === r.id;
                const ld =
                  r.latency_display ?? {
                    kind: "unknown",
                    label: r.latency_ms != null ? `${r.latency_ms} ms` : "—",
                    cached: false,
                    latency_ms: r.latency_ms ?? null,
                  };
                return (
                  <Fragment key={r.id}>
                    <tr className="bg-white dark:bg-zinc-950">
                      <td className="px-2 py-2">
                        <button
                          type="button"
                          aria-expanded={open}
                          className="rounded px-1 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-900 dark:hover:text-white"
                          onClick={() => setExpanded(open ? null : r.id)}
                        >
                          {open ? "▽" : "▷"}
                        </button>
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 text-zinc-700 dark:text-zinc-200">
                        {r.created_at ? new Date(r.created_at).toLocaleString() : "—"}
                      </td>
                      <td className="px-3 py-2">{r.interaction_type}</td>
                      <td className="px-3 py-2 capitalize">{r.run_mode ?? "generated"}</td>
                      <td className="px-3 py-2">{riskBadge(r.risk_tier ?? "low")}</td>
                      <td className="px-3 py-2 font-mono text-xs">{r.source_count ?? 0}</td>
                      <td className="px-3 py-2 font-mono text-xs">{r.citation_count ?? 0}</td>
                      <td className="px-3 py-2 font-mono text-xs">{r.patient_id ?? "—"}</td>
                      <td className="px-3 py-2">{r.model_name ?? "—"}</td>
                      <td className="px-3 py-2">{r.prompt_version ?? "—"}</td>
                      <td className="px-3 py-2">{r.status ?? "—"}</td>
                      <td className="px-3 py-2">
                        <span title={ld.kind}>{ld.label}</span>
                      </td>
                      <td className="px-3 py-2">
                        <Link
                          className="text-indigo-600 hover:underline dark:text-indigo-400"
                          href={`/admin/responsible-ai/${r.id}`}
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                    {open ? (
                      <tr className="bg-zinc-50 dark:bg-zinc-900/40">
                        <td colSpan={13} className="px-4 py-3 text-sm text-zinc-700 dark:text-zinc-200">
                          <p className="text-xs font-semibold uppercase text-zinc-500">Summary preview (redacted)</p>
                          <p className="mt-1 whitespace-pre-wrap">{r.output_preview ?? "—"}</p>
                          <p className="mt-2 text-xs text-zinc-500">
                            Request {r.request_id} · Risk tier is heuristic (governance demo), not a clinical assessment.
                          </p>
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                );
              })}
              {!rows.length && !err ? (
                <tr>
                  <td className="px-3 py-6 text-center text-zinc-500" colSpan={13}>
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
