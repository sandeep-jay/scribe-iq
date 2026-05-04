"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { CorpusPatientStats, PatientListItem } from "@/lib/backend";

function formatDate(raw: string | null) {
  if (!raw) return "—";
  return raw.includes("T") ? raw.slice(0, 10) : raw;
}

export function PatientsExplorer({
  patients,
  stats,
}: {
  patients: PatientListItem[];
  stats: CorpusPatientStats;
}) {
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return patients;
    return patients.filter((p) => {
      const hay = `${p.name}\n${p.external_id}`.toLowerCase();
      return hay.includes(needle);
    });
  }, [patients, q]);

  return (
    <div className="space-y-8">
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">Patients</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">{stats.total_patients}</p>
        </div>
        <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">Encounters (notes)</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">{stats.total_notes}</p>
        </div>
        <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">Loaded rows</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">{patients.length}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">Patients</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Synthetic cohort · {stats.total_patients} patients · {stats.total_notes} notes
          </p>
        </div>
        <label className="w-full max-w-md text-sm">
          <span className="sr-only">Search patients</span>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search name or external id…"
            className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none ring-zinc-200 focus:ring-2 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-50 dark:ring-zinc-800"
          />
        </label>
      </div>

      <section className="overflow-hidden rounded-lg border border-zinc-200 dark:border-zinc-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-zinc-50 text-xs uppercase text-zinc-500 dark:bg-zinc-900">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">External ID</th>
              <th className="px-4 py-3 text-right">Notes</th>
              <th className="px-4 py-3">Last session</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
            {filtered.map((p) => (
              <tr key={p.id} className="hover:bg-zinc-50/70 dark:hover:bg-zinc-900/50">
                <td className="px-4 py-3 font-medium">{p.name}</td>
                <td className="px-4 py-3 text-xs text-zinc-500">{p.external_id}</td>
                <td className="px-4 py-3 text-right tabular-nums">{p.note_count}</td>
                <td className="px-4 py-3">{formatDate(p.last_session_date)}</td>
                <td className="px-4 py-3 text-right">
                  <Link className="text-indigo-600 hover:text-indigo-500" href={`/patients/${encodeURIComponent(p.id)}`}>
                    Open →
                  </Link>
                </td>
              </tr>
            ))}
            {filtered.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-sm text-zinc-600 dark:text-zinc-400" colSpan={5}>
                  No rows match this search.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </section>
    </div>
  );
}
