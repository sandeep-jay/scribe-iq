"use client";

import Link from "next/link";
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { GenerateNotePanel } from "@/components/GenerateNotePanel";
import { MeetingPrepPanel } from "@/components/MeetingPrepPanel";

export type JourneyNote = {
  id: string;
  external_encounter_id: string;
  session_date: string | null;
  specialty: string | null;
  summary: string | null;
};

type TabId = "read" | "sources" | "codes";

const ENCOUNTER_LIST_PAGE_SIZE = 10;

function strVal(val: unknown): string | undefined {
  if (val === null || val === undefined) return undefined;
  if (typeof val === "string") return val.trim() || undefined;
  if (typeof val === "number" && Number.isFinite(val)) return String(val);
  return undefined;
}

function compactEncounterLabel(raw: string | null | undefined): string {
  if (!raw) return "—";
  const s = raw.trim();
  if (s.length <= 22) return s;
  return `${s.slice(0, 10)}…${s.slice(-8)}`;
}

function encounterTitle(summary: string | null | undefined): string {
  const s = (summary ?? "").trim();
  if (s) return s;
  return "Visit (no synopsis yet)";
}

/** Strip leading SOAP enumeration (e.g. "1. Subjective") for denser previews. */
function encounterPreview(summary: string | null | undefined): string {
  const base = encounterTitle(summary);
  const stripped = base.replace(/^\s*\d+[.)]\s+/, "").trim();
  return stripped || base;
}


/** ISO yyyy-mm-dd strings sort lexicographically. Null / empty dates sink to the end for ascending timelines. */
function compareSessionDateIso(a: string | null, b: string | null): number {
  const as = (a ?? "").trim();
  const bs = (b ?? "").trim();
  if (!as && !bs) return 0;
  if (!as) return 1;
  if (!bs) return -1;
  return as.localeCompare(bs);
}

function isoDateFromSession(raw: string | null): string | null {
  if (!raw) return null;
  const s = raw.trim();
  if (s.length >= 10) return s.slice(0, 10);
  return null;
}

function ymdLocalToday(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** ICD-10-CM-ish: letter + 2 digits + optional decimal (conservative). */
const ICD_LIKE = /\b([A-TV-Z][0-9][0-9A-TV-Z](?:\.[0-9A-TV-Z]{1,4})?)\b/g;
/** SNOMED CT SCTIDs are often 6–18 digits. */
const SNOMED_LIKE = /\b([0-9]{6,18})\b/g;

function collectCodeLikeStrings(root: unknown): { icd: Set<string>; snomed: Set<string> } {
  const icd = new Set<string>();
  const snomed = new Set<string>();
  const visit = (v: unknown) => {
    if (v === null || v === undefined) return;
    if (typeof v === "string") {
      let m: RegExpExecArray | null;
      const s1 = v.toUpperCase();
      ICD_LIKE.lastIndex = 0;
      while ((m = ICD_LIKE.exec(s1)) !== null) icd.add(m[1]);
      SNOMED_LIKE.lastIndex = 0;
      while ((m = SNOMED_LIKE.exec(v)) !== null) {
        const d = m[1];
        if (d.length >= 6 && d.length <= 18) snomed.add(d);
      }
      return;
    }
    if (Array.isArray(v)) {
      v.forEach(visit);
      return;
    }
    if (typeof v === "object") {
      Object.values(v as Record<string, unknown>).forEach(visit);
    }
  };
  visit(root);
  return { icd, snomed };
}

function priorVisitRecord(pv: unknown): Record<string, unknown> | null {
  if (pv && typeof pv === "object" && !Array.isArray(pv)) return pv as Record<string, unknown>;
  return null;
}

function tabBtn(active: boolean, onClick: () => void, children: ReactNode) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg px-3 py-2 text-xs font-semibold uppercase tracking-wide transition ${
        active
          ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
          : "border border-zinc-200 bg-white text-zinc-600 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-300 dark:hover:bg-zinc-900"
      }`}
    >
      {children}
    </button>
  );
}

export function PatientChartTabs(props: {
  patientId: string;
  journeyNotes: JourneyNote[];
  longitudinal: Record<string, unknown> | null;
  priorVisits: unknown[] | null;
  meds: string[];
}) {
  const { patientId, journeyNotes, longitudinal, priorVisits, meds } = props;
  const [tab, setTab] = useState<TabId>("read");
  const [encounterListPage, setEncounterListPage] = useState(0);
  const journeySig = useMemo(() => journeyNotes.map((n) => n.id).join(","), [journeyNotes]);

  /** Oldest → newest so the most recent encounter sits on the right. */
  const timelineChronological = useMemo(
    () => [...journeyNotes].sort((a, b) => compareSessionDateIso(a.session_date, b.session_date)),
    [journeyNotes],
  );

  /** Encounter index: newest first (last clinical date at top). */
  const encountersNewestFirst = useMemo(
    () => [...journeyNotes].sort((a, b) => compareSessionDateIso(b.session_date, a.session_date)),
    [journeyNotes],
  );

  const encounterTotal = journeyNotes.length;
  const listMaxPage = Math.max(0, Math.ceil(encounterTotal / ENCOUNTER_LIST_PAGE_SIZE) - 1);

  useEffect(() => {
    setEncounterListPage(0);
  }, [patientId, journeySig]);

  useEffect(() => {
    setEncounterListPage((p) => Math.min(p, listMaxPage));
  }, [listMaxPage]);

  const listPageClamped = Math.min(encounterListPage, listMaxPage);
  const pagedEncounterList = useMemo(() => {
    const start = listPageClamped * ENCOUNTER_LIST_PAGE_SIZE;
    return encountersNewestFirst.slice(start, start + ENCOUNTER_LIST_PAGE_SIZE);
  }, [encountersNewestFirst, listPageClamped]);

  const globalLatestNoteId = encountersNewestFirst[0]?.id ?? null;

  const timelineScrollRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (tab !== "read") return;
    const el = timelineScrollRef.current;
    if (!el) return;
    const snapToLatest = () => {
      el.scrollLeft = Math.max(0, el.scrollWidth - el.clientWidth);
    };
    snapToLatest();
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(snapToLatest) : null;
    ro?.observe(el);
    return () => ro?.disconnect();
  }, [tab, journeySig, timelineChronological.length]);

  const todayYmd = ymdLocalToday();

  const encounterHref = (externalEncounterId: string) =>
    `/patients/${encodeURIComponent(patientId)}/encounters/${encodeURIComponent(externalEncounterId)}`;

  const priorBlocks = useMemo(() => priorVisits ?? [], [priorVisits]);
  const priorSourcesNewestFirst = useMemo(() => {
    const blocks = [...priorBlocks];
    blocks.sort((a, b) => {
      const va = priorVisitRecord(a);
      const vb = priorVisitRecord(b);
      const da = strVal(va?.date) ?? strVal(va?.visit_date) ?? "";
      const db = strVal(vb?.date) ?? strVal(vb?.visit_date) ?? "";
      return compareSessionDateIso(db, da);
    });
    return blocks;
  }, [priorBlocks]);
  const codeHints = useMemo(() => collectCodeLikeStrings(longitudinal), [longitudinal]);

  const fingerprint = strVal(longitudinal?.note_fingerprint) ?? strVal(longitudinal?.fingerprint);
  const bundleVersion = strVal(longitudinal?.bundle_version) ?? strVal(longitudinal?.version);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2 border-b border-zinc-200 pb-4 dark:border-zinc-800">
        {tabBtn(tab === "read", () => setTab("read"), "Read")}
        {tabBtn(tab === "sources", () => setTab("sources"), "Sources")}
        {tabBtn(tab === "codes", () => setTab("codes"), "Codes & map")}
        <p className="ml-auto max-w-md text-[11px] text-zinc-500">
          Clinician-first on <span className="font-medium text-zinc-700 dark:text-zinc-300">Read</span>; longitudinal as
          citations on <span className="font-medium text-zinc-700 dark:text-zinc-300">Sources</span>; demo codes on{" "}
          <span className="font-medium text-zinc-700 dark:text-zinc-300">Codes & map</span>.
        </p>
      </div>

      {tab === "read" ? (
        <div className="space-y-8">
          <MeetingPrepPanel patientId={patientId} />

          <section className="rounded-xl border border-zinc-200 p-6 text-sm dark:border-zinc-800">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-zinc-500">Care timeline</p>
                <p className="mt-1 text-xs text-zinc-500">
                  Full history on one axis: older visits extend left; the most recent stays on the right. The view
                  starts scrolled to the latest — drag left for older visits.
                </p>
              </div>
            </div>
            <div ref={timelineScrollRef} className="mt-6 overflow-x-auto pb-2">
              <div className="relative min-w-max px-2">
                <div className="absolute left-4 right-4 top-[11px] h-px bg-zinc-200 dark:bg-zinc-700" aria-hidden />
                <div className="relative flex gap-0">
                  {timelineChronological.map((n) => {
                    const isLatest = globalLatestNoteId !== null && n.id === globalLatestNoteId;
                    const day = isoDateFromSession(n.session_date);
                    const maybeToday = isLatest && day === todayYmd;
                    return (
                    <div key={n.id} className="flex flex-col items-center" style={{ minWidth: 112 }}>
                      <Link
                        href={encounterHref(n.external_encounter_id)}
                        className="group flex flex-col items-center text-center"
                      >
                        <span
                          className={
                            isLatest
                              ? "z-10 h-3.5 w-3.5 rounded-full border-2 border-white bg-indigo-600 shadow ring-2 ring-indigo-300/80 group-hover:bg-indigo-500 dark:border-zinc-950 dark:ring-indigo-500/50"
                              : "z-10 h-3 w-3 rounded-full border-2 border-white bg-indigo-500 shadow group-hover:bg-indigo-400 dark:border-zinc-950"
                          }
                        />
                        <p className="mt-2 max-w-[7.5rem] text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
                          {n.session_date ?? "—"}
                        </p>
                        <p className="mt-1 line-clamp-3 max-w-[7.5rem] text-xs font-medium leading-snug text-zinc-900 group-hover:text-indigo-600 dark:text-zinc-50 dark:group-hover:text-indigo-300">
                          {encounterPreview(n.summary)}
                        </p>
                        <p className="mt-1 text-[10px] text-zinc-500">{n.specialty ?? "Clinical"}</p>
                        {isLatest ? (
                          <div className="mt-1 flex flex-wrap justify-center gap-1">
                            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-100">
                              Latest
                            </span>
                            {maybeToday ? (
                              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-amber-950 dark:bg-amber-950/50 dark:text-amber-100">
                                Today?
                              </span>
                            ) : null}
                          </div>
                        ) : null}
                      </Link>
                    </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </section>

          {meds.length ? (
            <section className="rounded-xl border border-zinc-200 p-6 text-sm dark:border-zinc-800">
              <p className="text-xs uppercase tracking-wide text-zinc-500">Medications (recent union)</p>
              <p className="mt-2 text-xs text-zinc-500">
                Pulled across recent longitudinal bundles — not a prescribing list.
              </p>
              <ul className="mt-3 flex flex-wrap gap-2">
                {meds.slice(0, 36).map((m) => (
                  <li
                    key={m}
                    className="rounded-full border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-xs text-zinc-800 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
                  >
                    {m}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className="rounded-xl border border-zinc-200 p-6 text-sm dark:border-zinc-800">
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">Encounters</h2>
            <p className="mt-1 text-xs text-zinc-500">
              Newest sessions first — paginated ({ENCOUNTER_LIST_PAGE_SIZE} per page) so note generation stays in reach
              on long histories. Same visits as the timeline.
            </p>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-zinc-600 dark:text-zinc-300">
              <span>
                {encounterTotal === 0
                  ? "No encounters loaded."
                  : `Showing ${listPageClamped * ENCOUNTER_LIST_PAGE_SIZE + 1}–${Math.min(encounterTotal, (listPageClamped + 1) * ENCOUNTER_LIST_PAGE_SIZE)} of ${encounterTotal}`}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={listPageClamped <= 0}
                  onClick={() => setEncounterListPage((p) => Math.max(0, p - 1))}
                  className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-xs font-medium text-zinc-800 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:hover:bg-zinc-900"
                >
                  Previous
                </button>
                <button
                  type="button"
                  disabled={listPageClamped >= listMaxPage}
                  onClick={() => setEncounterListPage((p) => Math.min(listMaxPage, p + 1))}
                  className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-xs font-medium text-zinc-800 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:hover:bg-zinc-900"
                >
                  Next
                </button>
              </div>
            </div>
            <ul className="mt-4 divide-y divide-zinc-200 dark:divide-zinc-800">
              {pagedEncounterList.map((n) => (
                <li key={n.id} className="flex flex-wrap items-center justify-between gap-2 py-3 first:pt-0">
                  <div className="min-w-0">
                    <p className="line-clamp-2 text-sm font-medium leading-snug text-zinc-900 dark:text-zinc-50">
                      {encounterPreview(n.summary)}
                    </p>
                    <p className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                      <span>
                        {n.session_date ?? "—"} · {n.specialty ?? "Clinical"}
                      </span>
                      {globalLatestNoteId !== null && n.id === globalLatestNoteId ? (
                        <>
                          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-100">
                            Latest
                          </span>
                          {isoDateFromSession(n.session_date) === todayYmd ? (
                            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-950 dark:bg-amber-950/50 dark:text-amber-100">
                              Today?
                            </span>
                          ) : null}
                        </>
                      ) : null}
                    </p>
                    <p className="font-mono text-[10px] text-zinc-400" title={n.external_encounter_id}>
                      {compactEncounterLabel(n.external_encounter_id)}
                    </p>
                  </div>
                  <Link
                    className="shrink-0 text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
                    href={encounterHref(n.external_encounter_id)}
                  >
                    Open →
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          <GenerateNotePanel patientId={patientId} />
        </div>
      ) : null}

      {tab === "sources" ? (
        <section className="space-y-6 rounded-xl border border-zinc-200 p-6 text-sm dark:border-zinc-800">
          <div>
            <p className="text-xs uppercase tracking-wide text-zinc-500">Sources (curated prior window)</p>
            <p className="mt-2 text-sm text-zinc-700 dark:text-zinc-200">
              Prior visit rows are the <span className="font-medium">grounding context</span> bundled for adaptation /
              pre-meeting summary (capped K priors). Each numbered row is one source slice, not the full legal record.
            </p>
            {(fingerprint || bundleVersion) && (
              <p className="mt-2 text-[11px] text-zinc-500">
                {bundleVersion ? <span>Bundle: {bundleVersion} · </span> : null}
                {fingerprint ? <span className="font-mono">Fingerprint: {fingerprint}</span> : null}
              </p>
            )}
          </div>

          {!longitudinal ? (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">No longitudinal blob for this patient.</p>
          ) : priorBlocks.length === 0 ? (
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-lg bg-zinc-50 p-3 text-xs dark:bg-zinc-950">
              {JSON.stringify(longitudinal, null, 2)}
            </pre>
          ) : (
            <ol className="space-y-4">
              {priorSourcesNewestFirst.map((pv, idx) => {
                const vis = priorVisitRecord(pv);
                if (!vis) return null;
                const when = strVal(vis.date) ?? strVal(vis.visit_date) ?? "—";
                const reason = strVal(vis.reason) ?? strVal(vis.reason_summary) ?? "Reason not documented";
                const cc = strVal(vis.chief_complaint) ?? strVal(vis.cc);
                const eid = strVal(vis.encounter_id);
                const matchNote = eid ? journeyNotes.find((j) => j.external_encounter_id === eid) : undefined;

                return (
                  <li
                    key={`${when}-${idx}`}
                    className="rounded-lg border border-zinc-200 bg-zinc-50/80 p-4 dark:border-zinc-800 dark:bg-zinc-950/40"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <p className="text-xs font-semibold text-zinc-500">
                        <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-zinc-200 text-[11px] text-zinc-800 dark:bg-zinc-800 dark:text-zinc-100">
                          {idx + 1}
                        </span>
                        Source · {when}
                      </p>
                      {eid && matchNote ? (
                        <Link
                          href={encounterHref(eid)}
                          className="text-xs font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
                        >
                          Open encounter →
                        </Link>
                      ) : eid ? (
                        <span className="font-mono text-[10px] text-zinc-400" title={eid}>
                          {compactEncounterLabel(eid)}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-2 text-sm font-medium text-zinc-900 dark:text-zinc-50">{reason}</p>
                    {cc ? <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-300">CC: {cc}</p> : null}
                  </li>
                );
              })}
            </ol>
          )}

          <details className="rounded-lg border border-dashed border-zinc-300 p-3 text-xs dark:border-zinc-700">
            <summary className="cursor-pointer font-semibold uppercase tracking-wide text-zinc-600">Raw longitudinal JSON</summary>
            <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap text-[11px] text-zinc-700 dark:text-zinc-200">
              {JSON.stringify(longitudinal, null, 2)}
            </pre>
          </details>
        </section>
      ) : null}

      {tab === "codes" ? (
        <div className="space-y-6">
          <section className="rounded-xl border border-zinc-200 p-6 text-sm dark:border-zinc-800">
            <p className="text-xs uppercase tracking-wide text-zinc-500">Coding hints (regex scan, demo)</p>
            <p className="mt-2 text-xs text-zinc-500">
              ICD-10–like and long numeric tokens are extracted from the longitudinal JSON strings for showcase only —
              not a billing encoder.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {[...codeHints.icd].sort().map((c) => (
                <span
                  key={`icd-${c}`}
                  className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 font-mono text-xs text-emerald-950 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-50"
                >
                  ICD {c}
                </span>
              ))}
              {[...codeHints.snomed].length ? (
                [...codeHints.snomed].slice(0, 24).map((c) => (
                  <span
                    key={`sct-${c}`}
                    className="rounded-md border border-sky-200 bg-sky-50 px-2 py-1 font-mono text-[11px] text-sky-950 dark:border-sky-900 dark:bg-sky-950/40 dark:text-sky-50"
                  >
                    SCTID {c}
                  </span>
                ))
              ) : (
                <span className="text-xs text-zinc-500">No SNOMED-like digit tokens found in this bundle.</span>
              )}
            </div>
            {codeHints.icd.size === 0 && codeHints.snomed.size === 0 ? (
              <p className="mt-3 text-xs text-zinc-500">
                No code-like tokens in text fields. Enrich pipeline outputs or open an encounter for structured entities.
              </p>
            ) : null}
          </section>

          <section className="rounded-xl border border-zinc-200 p-6 text-sm dark:border-zinc-800">
            <p className="text-xs uppercase tracking-wide text-zinc-500">Concept map (lightweight)</p>
            <p className="mt-2 text-xs text-zinc-500">
              Conditions from prior sources, grouped by first letter — demo layout for ontology-style navigation (not a
              full terminology server).
            </p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {(() => {
                const labels = new Set<string>();
                priorBlocks.forEach((pv) => {
                  const vis = priorVisitRecord(pv);
                  if (!vis) return;
                  const conds = Array.isArray(vis.conditions) ? (vis.conditions as unknown[]) : [];
                  conds.forEach((c) => {
                    const s = String(c).trim();
                    if (s) labels.add(s);
                  });
                });
                const byLetter = new Map<string, string[]>();
                [...labels].sort((a, b) => a.localeCompare(b)).forEach((label) => {
                  const letter = (label[0] ?? "?").toUpperCase();
                  if (!byLetter.has(letter)) byLetter.set(letter, []);
                  byLetter.get(letter)!.push(label);
                });
                const letters = [...byLetter.keys()].sort();
                if (!letters.length) {
                  return <p className="text-sm text-zinc-600 dark:text-zinc-400">No condition strings in prior_visits.</p>;
                }
                return letters.map((L) => (
                  <div key={L} className="rounded-lg border border-zinc-200 bg-zinc-50/60 p-3 dark:border-zinc-800 dark:bg-zinc-900/40">
                    <p className="text-[11px] font-bold uppercase tracking-wide text-zinc-500">{L}</p>
                    <ul className="mt-2 space-y-1.5 text-xs text-zinc-800 dark:text-zinc-100">
                      {(byLetter.get(L) ?? []).slice(0, 12).map((t) => (
                        <li key={t} className="leading-snug">
                          {t}
                        </li>
                      ))}
                    </ul>
                    {(byLetter.get(L) ?? []).length > 12 ? (
                      <p className="mt-2 text-[10px] text-zinc-500">+{(byLetter.get(L) ?? []).length - 12} more</p>
                    ) : null}
                  </div>
                ));
              })()}
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
