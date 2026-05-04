"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";

import type { CorpusPatientStats, PatientListItem } from "@/lib/backend";

type SortKey = "name" | "external_id" | "note_count" | "last_session";
type SortDir = "asc" | "desc";

function formatDate(raw: string | null) {
  if (!raw) return "—";
  return raw.includes("T") ? raw.slice(0, 10) : raw;
}

function lastSessionSortKey(p: PatientListItem): string {
  if (!p.last_session_date) return "";
  const d = p.last_session_date;
  return d.includes("T") ? d.slice(0, 10) : d.trim();
}

function SortTh({
  label,
  sortKey,
  sortDir,
  activeKey,
  onSort,
  align = "left",
}: {
  label: string;
  sortKey: SortKey;
  sortDir: SortDir;
  activeKey: SortKey;
  onSort: (key: SortKey) => void;
  align?: "left" | "right";
}) {
  const active = activeKey === sortKey;
  const arrow = active ? (sortDir === "asc" ? "↑" : "↓") : "";
  const alignCls = align === "right" ? "justify-end text-right" : "text-left";
  return (
    <th
      className={align === "right" ? "px-4 py-3 text-right" : "px-4 py-3"}
      scope="col"
      aria-sort={active ? (sortDir === "asc" ? "ascending" : "descending") : undefined}
    >
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className={`inline-flex w-full items-center gap-1 ${alignCls} text-xs font-semibold uppercase tracking-wide text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-100`}
      >
        <span>{label}</span>
        {active ? <span className="tabular-nums text-zinc-700 dark:text-zinc-200">{arrow}</span> : null}
      </button>
    </th>
  );
}

export function PatientsExplorer({
  patients,
  stats,
}: {
  patients: PatientListItem[];
  stats: CorpusPatientStats;
}) {
  const [q, setQ] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const onSort = useCallback(
    (key: SortKey) => {
      if (key === sortKey) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortKey(key);
        setSortDir(key === "note_count" || key === "last_session" ? "desc" : "asc");
      }
    },
    [sortKey],
  );

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return patients;
    return patients.filter((p) => {
      const hay = `${p.name}\n${p.external_id}`.toLowerCase();
      return hay.includes(needle);
    });
  }, [patients, q]);

  const displayed = useMemo(() => {
    const rows = [...filtered];
    rows.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "name":
          cmp = a.name.localeCompare(b.name);
          break;
        case "external_id":
          cmp = a.external_id.localeCompare(b.external_id);
          break;
        case "note_count":
          cmp = a.note_count - b.note_count;
          break;
        case "last_session": {
          const sa = lastSessionSortKey(a);
          const sb = lastSessionSortKey(b);
          if (!sa && !sb) cmp = 0;
          else if (!sa) cmp = 1;
          else if (!sb) cmp = -1;
          else cmp = sa.localeCompare(sb);
          break;
        }
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return rows;
  }, [filtered, sortKey, sortDir]);

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
              <SortTh label="Name" sortKey="name" sortDir={sortDir} activeKey={sortKey} onSort={onSort} />
              <SortTh label="External ID" sortKey="external_id" sortDir={sortDir} activeKey={sortKey} onSort={onSort} />
              <SortTh label="Notes" sortKey="note_count" sortDir={sortDir} activeKey={sortKey} onSort={onSort} align="right" />
              <SortTh label="Last session" sortKey="last_session" sortDir={sortDir} activeKey={sortKey} onSort={onSort} />
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-zinc-500" scope="col">
                Open
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
            {displayed.map((p) => (
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
            {displayed.length === 0 ? (
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
