import Link from "next/link";

import { GenerateNotePanel } from "@/components/GenerateNotePanel";
import { PatientChartTabs } from "@/components/PatientChartTabs";
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

  const chatHref = `/chat?patient_id=${encodeURIComponent(detail.id)}`;
  const jumpClass =
    "inline-flex items-center rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 text-xs font-medium text-zinc-700 shadow-sm hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800";

  return (
    <div className="mx-auto flex w-full min-w-0 max-w-6xl flex-col gap-8">
      <section className="min-w-0 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/40">
        <p className="text-xs uppercase tracking-wide text-zinc-500">Patient context</p>
        <h1 className="mt-1 text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{detail.name}</h1>
        <p className="mt-1 break-all text-sm text-zinc-600 dark:text-zinc-400">{detail.external_id}</p>
        <p className="mt-0.5 font-mono text-xs text-zinc-500">{detail.id}</p>
        {line2 ? <p className="mt-2 text-sm text-zinc-700 dark:text-zinc-200">{line2}</p> : null}
        {cityState ? <p className="mt-1 text-xs text-zinc-500">{cityState}</p> : null}

        <div className="mt-4 flex flex-wrap gap-2">
          <Link className={jumpClass} href={chatHref}>
            Chat
          </Link>
          <a className={jumpClass} href="#chart-prep">
            Meeting prep
          </a>
          <a className={jumpClass} href="#care-timeline">
            Care timeline
          </a>
          <a className={jumpClass} href="#encounters-list">
            Encounters
          </a>
          <a className={jumpClass} href="#generate-note">
            Generate note
          </a>
        </div>
      </section>

      <details className="min-w-0 rounded-xl border border-zinc-200 p-4 text-sm dark:border-zinc-800">
        <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-zinc-600 dark:text-zinc-400">
          Synthea profile (demographics & synthetic economics)
        </summary>
        <div className="mt-4 grid gap-6 lg:grid-cols-2">
          <div>
            <p className="text-xs uppercase tracking-wide text-zinc-500">Demographics</p>
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

          <div className="border-t border-zinc-200 pt-4 lg:border-t-0 lg:border-l lg:pl-6 lg:pt-0 dark:border-zinc-800">
            <p className="text-xs uppercase tracking-wide text-zinc-500">Synthetic economics</p>
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
        </div>
      </details>

      <PatientChartTabs
        patientId={detail.id}
        journeyNotes={detail.notes}
        longitudinal={longitudinalRec}
        priorVisits={priorVisitsRaw}
        meds={detail.longitudinal_medication_hints ?? []}
      />

      <div id="generate-note" className="scroll-mt-28 min-w-0">
        <GenerateNotePanel patientId={detail.id} />
      </div>

      <details className="rounded-xl border border-dashed border-zinc-300 p-4 text-xs dark:border-zinc-700">
        <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-zinc-600">
          Full patient metadata payload (corpus loader)
        </summary>
        <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap text-[11px]">
          {JSON.stringify(meta, null, 2)}
        </pre>
      </details>
    </div>
  );
}
