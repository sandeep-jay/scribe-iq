"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";

import type { CorpusPatientStats, PatientListItem } from "@/lib/backend";
import { usePatientsListSearchQuery } from "@/lib/usePatientsListSearchQuery";
import { patientInitials } from "@/lib/patientDisplay";

type SortKey = "name" | "external_id" | "note_count" | "last_session";
type SortDir = "asc" | "desc";
type MinEncounters = null | 2 | 5 | 10;

type AdvApplied = {
  name: string;
  externalId: string;
  from: string;
  to: string;
};

function formatDate(raw: string | null) {
  if (!raw) return "—";
  return raw.includes("T") ? raw.slice(0, 10) : raw;
}

function lastSessionSortKey(p: PatientListItem): string {
  if (!p.last_session_date) return "";
  const d = p.last_session_date;
  return d.includes("T") ? d.slice(0, 10) : d.trim();
}

function sessionYmd(raw: string | null): string | null {
  if (!raw) return null;
  const s = raw.trim();
  if (s.length >= 10) return s.slice(0, 10);
  return null;
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
  const { displayValue: listSearchQuery } = usePatientsListSearchQuery();
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [chipLongitudinal, setChipLongitudinal] = useState(false);
  const [chipMinEncounters, setChipMinEncounters] = useState<MinEncounters>(null);
  const [specialtyQ, setSpecialtyQ] = useState("");
  const [advOpen, setAdvOpen] = useState(false);
  const [advDraft, setAdvDraft] = useState<AdvApplied>({ name: "", externalId: "", from: "", to: "" });
  const [advApplied, setAdvApplied] = useState<AdvApplied>({ name: "", externalId: "", from: "", to: "" });

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
    const needle = listSearchQuery.trim().toLowerCase();
    const spec = specialtyQ.trim().toLowerCase();
    const advName = advApplied.name.trim().toLowerCase();
    const advExt = advApplied.externalId.trim().toLowerCase();
    const from = advApplied.from.trim();
    const to = advApplied.to.trim();

    return patients.filter((p) => {
      if (chipLongitudinal && !p.has_longitudinal) return false;
      if (chipMinEncounters !== null && p.note_count < chipMinEncounters) return false;
      if (needle) {
        const hay = `${p.name}\n${p.external_id}`.toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      if (spec) {
        const sp = (p.last_specialty ?? "").toLowerCase();
        if (!sp.includes(spec)) return false;
      }
      if (advName && !p.name.toLowerCase().includes(advName)) return false;
      if (advExt && !p.external_id.toLowerCase().includes(advExt)) return false;
      if (from || to) {
        const ymd = sessionYmd(p.last_session_date);
        if (!ymd) return false;
        if (from && ymd < from) return false;
        if (to && ymd > to) return false;
      }
      return true;
    });
  }, [patients, listSearchQuery, chipLongitudinal, chipMinEncounters, specialtyQ, advApplied]);

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
    <div className="min-w-0 max-w-full space-y-8">
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
            Synthetic cohort · {stats.total_patients} patients · {stats.total_notes} notes · showing{" "}
            <span className="font-medium tabular-nums text-zinc-900 dark:text-zinc-100">{displayed.length}</span> of{" "}
            <span className="tabular-nums">{patients.length}</span> loaded
          </p>
        </div>
        <div className="flex w-full max-w-md flex-col gap-2">
          <p className="text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">
            Name or external id: use the top search bar (same filter as <code className="rounded bg-zinc-100 px-1 py-0.5 font-mono text-[10px] text-zinc-700 dark:bg-zinc-800 dark:text-zinc-200">?q=</code> in the URL). Specialty, chips, and advanced search stay here.
          </p>
          <label className="text-sm">
            <span className="sr-only">Filter by specialty text</span>
            <input
              value={specialtyQ}
              onChange={(e) => setSpecialtyQ(e.target.value)}
              placeholder="Specialty contains…"
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none ring-zinc-200 focus:ring-2 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-50 dark:ring-zinc-800"
            />
          </label>
        </div>
      </div>


      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-zinc-400">Filters</span>
          <button
            type="button"
            onClick={() => setChipLongitudinal((v) => !v)}
            className={`rounded-full border px-3 py-1 text-xs font-medium ${
              chipLongitudinal
                ? "border-indigo-500 bg-indigo-50 text-indigo-950 dark:border-indigo-400 dark:bg-indigo-950/40 dark:text-indigo-50"
                : "border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800"
            }`}
          >
            Has longitudinal
          </button>
          {([2, 5, 10] as const).map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setChipMinEncounters((c) => (c === n ? null : n))}
              className={`rounded-full border px-3 py-1 text-xs font-medium ${
                chipMinEncounters === n
                  ? "border-indigo-500 bg-indigo-50 text-indigo-950 dark:border-indigo-400 dark:bg-indigo-950/40 dark:text-indigo-50"
                  : "border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800"
              }`}
            >
              ≥ {n} encounters
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => {
            setAdvDraft(advApplied);
            setAdvOpen(true);
          }}
          className="rounded-lg border border-zinc-300 bg-white px-3 py-2 text-xs font-semibold uppercase tracking-wide text-zinc-800 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800"
        >
          Advanced search
        </button>
      </div>

      {advOpen ? (
        <>
          <button
            type="button"
            aria-label="Close advanced search"
            className="fixed inset-0 z-40 bg-black/30"
            onClick={() => setAdvOpen(false)}
          />
          <aside className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-zinc-200 bg-white shadow-2xl dark:border-zinc-800 dark:bg-zinc-950">
            <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
              <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Advanced search</p>
              <button
                type="button"
                className="rounded-lg px-2 py-1 text-xs text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-900"
                onClick={() => setAdvOpen(false)}
              >
                Close
              </button>
            </div>
            <div className="flex-1 space-y-4 overflow-y-auto p-4 text-sm">
              <p className="text-xs text-zinc-500">
                Client-side filters on the loaded page (limit {patients.length}). Combine with chips and the top search bar.
              </p>
              <label className="block space-y-1">
                <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">Name contains</span>
                <input
                  value={advDraft.name}
                  onChange={(e) => setAdvDraft((d) => ({ ...d, name: e.target.value }))}
                  className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
                />
              </label>
              <label className="block space-y-1">
                <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">External ID contains</span>
                <input
                  value={advDraft.externalId}
                  onChange={(e) => setAdvDraft((d) => ({ ...d, externalId: e.target.value }))}
                  className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
                />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="block space-y-1">
                  <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">Last session from</span>
                  <input
                    type="date"
                    value={advDraft.from}
                    onChange={(e) => setAdvDraft((d) => ({ ...d, from: e.target.value }))}
                    className="w-full rounded-lg border border-zinc-300 bg-white px-2 py-2 text-xs dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
                  />
                </label>
                <label className="block space-y-1">
                  <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">Last session to</span>
                  <input
                    type="date"
                    value={advDraft.to}
                    onChange={(e) => setAdvDraft((d) => ({ ...d, to: e.target.value }))}
                    className="w-full rounded-lg border border-zinc-300 bg-white px-2 py-2 text-xs dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
                  />
                </label>
              </div>
            </div>
            <div className="flex gap-2 border-t border-zinc-200 p-4 dark:border-zinc-800">
              <button
                type="button"
                className="flex-1 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-white hover:bg-indigo-500"
                onClick={() => {
                  setAdvApplied({ ...advDraft });
                  setAdvOpen(false);
                }}
              >
                Apply
              </button>
              <button
                type="button"
                className="rounded-lg border border-zinc-300 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
                onClick={() => {
                  const empty = { name: "", externalId: "", from: "", to: "" };
                  setAdvDraft(empty);
                  setAdvApplied(empty);
                }}
              >
                Clear
              </button>
            </div>
          </aside>
        </>
      ) : null}

      <section className="min-w-0 overflow-x-auto overflow-y-hidden rounded-lg border border-zinc-200 dark:border-zinc-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-zinc-50 text-xs uppercase text-zinc-500 dark:bg-zinc-900">
            <tr>
              <SortTh label="Patient" sortKey="name" sortDir={sortDir} activeKey={sortKey} onSort={onSort} />
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
                <td className="px-4 py-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <span
                      className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-zinc-200 text-xs font-semibold text-zinc-800 dark:bg-zinc-800 dark:text-zinc-100"
                      aria-hidden
                    >
                      {patientInitials(p.name)}
                    </span>
                    <div className="min-w-0">
                      <p className="font-medium text-zinc-900 dark:text-zinc-50">{p.name}</p>
                      <p className="mt-0.5 text-xs text-zinc-500">
                        Last session {formatDate(p.last_session_date)} · {p.note_count} note{p.note_count === 1 ? "" : "s"}
                        {p.has_longitudinal ? (
                          <span className="ml-2 rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-100">
                            Longitudinal
                          </span>
                        ) : null}
                      </p>
                      {p.last_specialty ? (
                        <p className="mt-0.5 truncate text-[11px] text-zinc-500" title={p.last_specialty}>
                          Specialty: {p.last_specialty}
                        </p>
                      ) : null}
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 align-top text-xs text-zinc-500">{p.external_id}</td>
                <td className="px-4 py-3 align-top text-right tabular-nums">{p.note_count}</td>
                <td className="px-4 py-3 align-top">{formatDate(p.last_session_date)}</td>
                <td className="px-4 py-3 align-top text-right">
                  <Link className="text-indigo-600 hover:text-indigo-500" href={`/patients/${encodeURIComponent(p.id)}`}>
                    Open →
                  </Link>
                </td>
              </tr>
            ))}
            {displayed.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-sm text-zinc-600 dark:text-zinc-400" colSpan={5}>
                  No rows match filters.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </section>
    </div>
  );
}
