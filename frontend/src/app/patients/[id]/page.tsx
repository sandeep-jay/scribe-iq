import Link from "next/link";

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

      <PatientChartTabs
        patientId={detail.id}
        journeyNotes={detail.notes}
        longitudinal={longitudinalRec}
        priorVisits={priorVisitsRaw}
        meds={detail.longitudinal_medication_hints ?? []}
      />

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
