import Link from "next/link";

import { GenerateNotePanel } from "@/components/GenerateNotePanel";
import { MeetingPrepPanel } from "@/components/MeetingPrepPanel";
import { fetchPatient } from "@/lib/backend";

type Props = { params: Promise<{ id: string }> };

function asRecord(val: unknown): Record<string, unknown> | null {
  if (val && typeof val === "object" && !Array.isArray(val)) {
    return val as Record<string, unknown>;
  }
  return null;
}

function strVal(val: unknown): string | undefined {
  if (val === null || val === undefined) return undefined;
  if (typeof val === "string") return val.trim() || undefined;
  if (typeof val === "number" && Number.isFinite(val)) return String(val);
  return undefined;
}

function formatUsd(val: unknown): string | undefined {
  if (typeof val !== "number" || !Number.isFinite(val)) return undefined;
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(
    val,
  );
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

export default async function PatientDetailPage({ params }: Props) {
  const { id: rawId } = await params;
  const pid = decodeURIComponent(rawId);

  let detail;
  try {
    detail = await fetchPatient(pid);
  } catch (e) {
    return (
      <div className="space-y-2">
        <h1 className="text-xl font-semibold">Patient detail</h1>
        <p className="text-sm text-red-600">{(e as Error).message}</p>
      </div>
    );
  }

  const meta = detail.metadata ?? {};
  const addr = asRecord(meta.address);
  const econ = asRecord(meta.economics);

  const cityState = [strVal(addr?.city), strVal(addr?.state)].filter(Boolean).join(", ");
  const line2 = [
    meta.birthdate ? `DOB ${strVal(meta.birthdate)}` : null,
    meta.deathdate ? `DOD ${strVal(meta.deathdate)}` : null,
    strVal(meta.sex) ? `${strVal(meta.sex)}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  const longitudinal = detail.latest_longitudinal;
  const longitudinalRec =
    longitudinal && typeof longitudinal === "object" && !Array.isArray(longitudinal) ? longitudinal : null;
  const priorVisitsRaw =
    longitudinalRec && Array.isArray((longitudinalRec as Record<string, unknown>).prior_visits)
      ? ((longitudinalRec as Record<string, unknown>).prior_visits as unknown[])
      : null;

  const journeyNotes = [...detail.notes].sort((a, b) => {
    const ad = a.session_date ?? "";
    const bd = b.session_date ?? "";
    return ad.localeCompare(bd);
  });

  const demographicsCardCls =
    "grid w-full gap-4 rounded-xl border border-zinc-200 p-6 text-sm dark:border-zinc-800";

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-10">
      <div className="grid gap-6 lg:grid-cols-12 lg:items-start">
        <section className="space-y-2 lg:col-span-12 xl:col-span-5">
          <p className="text-xs uppercase tracking-wide text-zinc-500">Patient record</p>
          <h1 className="text-3xl font-semibold">{detail.name}</h1>
          <p className="text-sm text-zinc-600 break-all dark:text-zinc-400">{detail.external_id}</p>
          {line2 ? <p className="text-sm text-zinc-700 dark:text-zinc-200">{line2}</p> : null}
          {cityState ? <p className="text-xs text-zinc-500">{cityState}</p> : null}
          <Link
            className="inline-block text-sm text-indigo-600 hover:text-indigo-500"
            href={`/chat?patient_id=${encodeURIComponent(detail.id)}`}
          >
            Open chat grounded to patient →
          </Link>
        </section>

        <section className={`${demographicsCardCls} lg:col-span-12 xl:col-span-7`}>
          <div>
            <p className="text-xs uppercase tracking-wide text-zinc-500">Synthea demographics</p>
            <dl className="mt-3 space-y-2 text-xs text-zinc-800 dark:text-zinc-100">
              {[
                ["Race", strVal(meta.race)],
                ["Ethnicity", strVal(meta.ethnicity)],
                ["Marital", strVal(meta.marital_status)],
                ["Birthplace", strVal(meta.birthplace)],
                ["Address", strVal(addr?.line)],
                ["ZIP", strVal(addr?.zip)],
              ].map(
                ([k, v]) =>
                  v ? (
                    <div key={k} className="flex gap-3">
                      <dt className="w-28 shrink-0 text-zinc-500">{k}</dt>
                      <dd className="min-w-0 flex-1 whitespace-pre-wrap">{v}</dd>
                    </div>
                  ) : null,
              )}
            </dl>
          </div>

          <div className="border-t border-zinc-200 pt-4 dark:border-zinc-800">
            <p className="text-xs uppercase tracking-wide text-zinc-500">Synthetic economics (Synthea)</p>
            <dl className="mt-3 space-y-2 text-xs text-zinc-800 dark:text-zinc-100">
              {[
                ["Annual income", formatUsd(econ?.annual_income)],
                ["Healthcare expenses", formatUsd(econ?.healthcare_expenses)],
                ["Coverage", formatUsd(econ?.healthcare_coverage)],
              ].map(
                ([k, v]) =>
                  v ? (
                    <div key={k} className="flex gap-3">
                      <dt className="w-36 shrink-0 text-zinc-500">{k}</dt>
                      <dd className="min-w-0 flex-1">{v}</dd>
                    </div>
                  ) : null,
              )}
            </dl>
          </div>
        </section>
      </div>

      <MeetingPrepPanel patientId={detail.id} />

      <section className="rounded-xl border border-zinc-200 p-6 text-sm dark:border-zinc-800">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-zinc-500">Patient journey (stored encounters)</p>
            <p className="mt-1 text-xs text-zinc-500">
              Chronological dots use each note session date + synopsis. This is the full stored history, not the
              capped prior window used for adaptation prompts.
            </p>
          </div>
        </div>
        <div className="mt-4 overflow-x-auto pb-2">
          <div className="flex min-w-max gap-3">
            {journeyNotes.map((n) => (
              <Link
                key={n.id}
                href={`/patients/${encodeURIComponent(detail.id)}/encounters/${encodeURIComponent(n.external_encounter_id)}`}
                className="w-44 shrink-0 rounded-lg border border-zinc-200 bg-zinc-50/70 p-3 text-xs hover:bg-zinc-100 dark:border-zinc-800 dark:bg-zinc-950/40 dark:hover:bg-zinc-900"
              >
                <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">{n.session_date ?? "—"}</p>
                <p className="mt-2 line-clamp-4 text-sm font-medium leading-snug text-zinc-900 dark:text-zinc-50">
                  {encounterTitle(n.summary)}
                </p>
                <p className="mt-2 text-[11px] text-zinc-500">{n.specialty ?? "Clinical"}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {(detail.longitudinal_medication_hints?.length ?? 0) ? (
        <section className="rounded-xl border border-zinc-200 p-6 text-sm dark:border-zinc-800">
          <p className="text-xs uppercase tracking-wide text-zinc-500">Medications (recent union)</p>
          <p className="mt-2 text-xs text-zinc-500">
            Pulled across recent longitudinal bundles for this synthetic patient — not a prescribing list.
          </p>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-zinc-900 dark:text-zinc-100">
            {(detail.longitudinal_medication_hints ?? []).slice(0, 48).map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="rounded-xl border border-zinc-200 p-6 text-sm dark:border-zinc-800">
        <p className="text-xs uppercase tracking-wide text-zinc-500">Curated prior context (model window)</p>

        {!longitudinal ? (
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">No longitudinal blob on disk.</p>
        ) : priorVisitsRaw && priorVisitsRaw.length > 0 ? (
          <div className="mt-3 space-y-3">
            <p className="text-xs text-zinc-500">
              Showing <span className="font-semibold text-zinc-700 dark:text-zinc-300">{priorVisitsRaw.length}</span>{" "}
              prior visit blocks from the longitudinal bundle (capped K priors for adaptation / richness). Raw JSON below.
            </p>
            <ol className="space-y-2">
              {priorVisitsRaw.map((pv, idx) => {
                const vis =
                  pv && typeof pv === "object" && !Array.isArray(pv) ? (pv as Record<string, unknown>) : null;
                if (!vis) return null;

                const when = strVal(vis.date) ?? strVal(vis.visit_date) ?? "—";
                const reason = strVal(vis.reason) ?? strVal(vis.reason_summary) ?? "Reason not documented";
                const cc = strVal(vis.chief_complaint) ?? strVal(vis.cc);
                const conds = Array.isArray(vis.conditions) ? (vis.conditions as unknown[]).slice(0, 5) : [];
                const eid = strVal(vis.encounter_id);

                return (
                  <li
                    key={`${when}-${idx}`}
                    className="rounded-lg border border-zinc-200 bg-zinc-50/80 p-3 text-xs text-zinc-900 dark:border-zinc-800 dark:bg-zinc-950/40 dark:text-zinc-100"
                  >
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">{when}</p>
                      {eid ? (
                        <p className="font-mono text-[10px] text-zinc-400" title={eid}>
                          {compactEncounterLabel(eid)}
                        </p>
                      ) : null}
                    </div>
                    <p className="mt-1 text-sm font-medium leading-snug">{reason}</p>
                    {cc ? <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-300">CC: {cc}</p> : null}
                    {conds.length ? (
                      <div className="mt-2">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">Conditions</p>
                        <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-zinc-700 dark:text-zinc-200">
                          {conds.map((c, j) => (
                            <li key={j}>{String(c)}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    {Array.isArray(vis.medications) && (vis.medications as unknown[]).length ? (
                      <div className="mt-2">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">Medications</p>
                        <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-zinc-700 dark:text-zinc-200">
                          {(vis.medications as unknown[]).slice(0, 8).map((m, j) => (
                            <li key={j}>{String(m)}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </li>
                );
              })}
            </ol>
            <details className="rounded-lg border border-dashed border-zinc-300 p-3 text-xs dark:border-zinc-700">
              <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-zinc-600">
                Raw longitudinal JSON
              </summary>
              <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap text-[11px] text-zinc-700 dark:text-zinc-200">
                {JSON.stringify(longitudinal, null, 2)}
              </pre>
            </details>
          </div>
        ) : (
          <pre className="mt-2 max-h-80 overflow-auto text-xs whitespace-pre-wrap text-zinc-800 dark:text-zinc-100">
            {JSON.stringify(longitudinal, null, 2)}
          </pre>
        )}
      </section>

      <GenerateNotePanel patientId={detail.id} />

      <details className="rounded-xl border border-dashed border-zinc-300 p-4 text-xs dark:border-zinc-700">
        <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-zinc-600">
          Full patient metadata payload (corpus loader)
        </summary>
        <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap text-[11px]">
          {JSON.stringify(meta, null, 2)}
        </pre>
      </details>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">All stored encounters ({detail.notes.length})</h2>

        <div className="space-y-3">
          {detail.notes.map((n) => (
            <div
              key={n.id}
              className="flex flex-col gap-3 rounded-xl border border-zinc-200 p-4 sm:flex-row sm:items-start sm:justify-between dark:border-zinc-800"
            >
              <div className="min-w-0 flex-1 space-y-1">
                <p className="text-base font-medium leading-snug text-zinc-900 dark:text-zinc-50">
                  {encounterTitle(n.summary)}
                </p>
                <p className="text-xs text-zinc-500">
                  {n.specialty ?? "Clinical"}
                  {" · "}
                  {n.session_date ?? "—"}
                </p>
                <p className="font-mono text-[11px] text-zinc-400 dark:text-zinc-500" title={n.external_encounter_id}>
                  Encounter ID:&nbsp;<span className="break-all">{compactEncounterLabel(n.external_encounter_id)}</span>
                </p>
              </div>
              <div className="shrink-0 self-start sm:self-center">
                <Link
                  className="text-sm whitespace-nowrap text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
                  href={`/patients/${encodeURIComponent(detail.id)}/encounters/${encodeURIComponent(n.external_encounter_id)}`}
                >
                  Encounter viewer →
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

