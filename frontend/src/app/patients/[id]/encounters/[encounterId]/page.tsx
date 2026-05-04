import Link from "next/link";

import { GenerateNotePanel } from "@/components/GenerateNotePanel";
import { fetchNote, fetchPatient } from "@/lib/backend";

type Props = {
  params: Promise<{ id: string; encounterId: string }>;
};

function asRecord(val: unknown): Record<string, unknown> | null {
  if (val && typeof val === "object" && !Array.isArray(val)) {
    return val as Record<string, unknown>;
  }
  return null;
}

function soapLine(label: string, value: unknown) {
  const s = typeof value === "string" ? value.trim() : "";
  if (!s) return null;
  return (
    <div key={label} className="space-y-1">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="whitespace-pre-wrap text-sm text-zinc-900 dark:text-zinc-50">{s}</p>
    </div>
  );
}

function collectVitals(sn: Record<string, unknown>, entity: Record<string, unknown>): Array<{ label: string; value: string }> {
  const vit = asRecord(sn.vitals) ?? asRecord(entity.vitals);
  if (!vit) return [];
  const out: Array<{ label: string; value: string }> = [];
  for (const [k, raw] of Object.entries(vit)) {
    if (raw === null || raw === undefined) continue;
    const val = typeof raw === "string" ? raw.trim() : typeof raw === "number" && Number.isFinite(raw) ? String(raw) : "";
    if (!val) continue;
    out.push({ label: k.replace(/_/g, " "), value: val });
  }
  return out.slice(0, 24);
}

export default async function EncounterViewerPage({ params }: Props) {
  const raw = await params;
  const patientKey = decodeURIComponent(raw.id);
  const encounterRaw = decodeURIComponent(raw.encounterId);

  let patient;
  try {
    patient = await fetchPatient(patientKey);
  } catch (e) {
    return <p className="text-red-600">{(e as Error).message}</p>;
  }

  const preview =
    patient.notes.find((n) => n.id === encounterRaw) ??
    patient.notes.find((n) => n.external_encounter_id === encounterRaw);

  if (!preview) {
    return (
      <div className="space-y-2">
        <p>No encounter keyed <code>{encounterRaw}</code> found for patient.</p>
        <Link className="text-indigo-600" href={`/patients/${encodeURIComponent(patient.id)}`}>
          ← Back to patient
        </Link>
      </div>
    );
  }

  let note;
  try {
    note = await fetchNote(preview.id);
  } catch (e) {
    return <p className="text-red-600">{(e as Error).message}</p>;
  }

  const sn = note.structured_note ?? {};
  const entity = note.entity_payload ?? {};
  const syntheaEncounter = asRecord(entity.synthea_encounter);

  const chief = sn.chief_complaint;
  const history = sn.history;
  const exam = sn.examination;
  const assess = sn.assessment;
  const plan = sn.plan;
  const follow = sn.follow_up;
  const fullNote = sn.full_note;
  const summary = sn.summary;

  const vitals = collectVitals(sn as Record<string, unknown>, entity as Record<string, unknown>);
  const structuredKeys = new Set(
    ["chief_complaint", "history", "examination", "assessment", "plan", "follow_up", "full_note", "summary", "vitals"],
  );
  const extraStructured = Object.entries(sn).filter(([k, v]) => !structuredKeys.has(k) && v !== null && v !== undefined);

  return (
    <div className="min-w-0 max-w-full space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase text-zinc-500">Encounter viewer</p>
          <h1 className="text-2xl font-semibold">{note.external_encounter_id}</h1>
          <p className="text-sm text-zinc-600">{patient.name}</p>
          {preview.specialty ? (
            <p className="mt-1 text-sm font-semibold text-zinc-800 dark:text-zinc-100">
              <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">Specialty</span>{" "}
              {preview.specialty}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled
            title="Draft persistence requires auth + API (Phase D3). This control is a layout placeholder."
            className="rounded-lg border border-zinc-200 bg-zinc-100 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400"
          >
            Save draft
          </button>
          <Link className="text-sm text-indigo-600" href={`/chat?patient_id=${encodeURIComponent(patient.id)}`}>
            Chat about patient →
          </Link>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="flex min-h-[28rem] flex-col rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
          <header className="mb-3 flex items-center justify-between gap-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-600">Clinical dialogue</p>
            <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] font-semibold text-zinc-700 dark:bg-zinc-900 dark:text-zinc-200">
              Transcript
            </span>
          </header>
          <pre className="flex-1 overflow-auto whitespace-pre-wrap text-sm leading-relaxed text-zinc-800 dark:text-zinc-100">
            {(note.conversation_text || "").trim() || "No conversation text stored for this encounter."}
          </pre>
        </section>

        <section className="flex min-h-[28rem] flex-col rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
          <header className="mb-3 flex items-center justify-between gap-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-600">Structured note</p>
            <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-900 dark:bg-indigo-950/40 dark:text-indigo-100">
              Sectioned workspace (demo)
            </span>
          </header>
          <div className="flex-1 space-y-4 overflow-auto pr-1 text-sm">
            {vitals.length ? (
              <div className="rounded-lg border border-sky-200 bg-sky-50/60 p-3 dark:border-sky-900 dark:bg-sky-950/30">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-sky-900 dark:text-sky-100">
                  Vitals / quick facts
                </p>
                <p className="mt-1 text-[11px] text-sky-900/80 dark:text-sky-100/80">
                  Read-only chips parsed from <span className="font-mono">structured_note.vitals</span> (or entity) when present.
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {vitals.map((v) => (
                    <span
                      key={v.label}
                      className="rounded-full border border-sky-200 bg-white px-2.5 py-1 text-[11px] font-medium text-sky-950 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-50"
                      title={v.value}
                    >
                      {v.label}: {v.value.length > 48 ? `${v.value.slice(0, 48)}…` : v.value}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
            {soapLine("Chief complaint", chief)}
            {soapLine("History", history)}
            {soapLine("Examination", exam)}
            {soapLine("Assessment", assess)}
            {soapLine("Plan", plan)}
            {soapLine("Follow-up", follow)}
            {soapLine("Summary", summary)}
            {typeof fullNote === "string" && fullNote.trim() ? (
              <div className="space-y-1 border-t border-zinc-200 pt-3 dark:border-zinc-800">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">Full note</p>
                <p className="whitespace-pre-wrap text-sm text-zinc-900 dark:text-zinc-50">{fullNote.trim()}</p>
              </div>
            ) : null}
            {extraStructured.length ? (
              <details className="rounded-lg border border-dashed border-zinc-300 p-3 text-xs dark:border-zinc-700">
                <summary className="cursor-pointer font-semibold uppercase tracking-wide text-zinc-600">
                  Additional structured_note keys ({extraStructured.length})
                </summary>
                <div className="mt-3 space-y-3">
                  {extraStructured.map(([k, v]) => (
                    <div key={k} className="space-y-1">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">{k}</p>
                      <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded bg-zinc-50 p-2 text-[11px] text-zinc-800 dark:bg-zinc-950 dark:text-zinc-100">
                        {typeof v === "string" ? v : JSON.stringify(v, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              </details>
            ) : null}
          </div>
        </section>
      </div>

      {syntheaEncounter ? (
        <section className="rounded-xl border border-zinc-200 p-4 text-sm dark:border-zinc-800">
          <header className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-zinc-600">
            Synthea encounter spine (raw CSV joins where available)
          </header>
          <dl className="grid gap-3 text-xs text-zinc-800 dark:text-zinc-100 sm:grid-cols-2">
            {(
              [
                ["Facility", syntheaEncounter.organization_name],
                ["Facility location", syntheaEncounter.organization_location],
                ["Clinician", syntheaEncounter.provider_name],
                ["Clinician specialty", syntheaEncounter.provider_specialty],
                ["Payer", syntheaEncounter.payer_name],
                ["Payer type", syntheaEncounter.payer_ownership],
                ["Class", syntheaEncounter.encounter_class],
                ["Billing description", syntheaEncounter.encounter_description],
                ["Total claim", syntheaEncounter.total_claim_cost],
                ["Payer coverage", syntheaEncounter.payer_coverage],
                [
                  "Clinical window",
                  [syntheaEncounter.start, syntheaEncounter.stop].filter(Boolean).join(" → "),
                ],
              ] satisfies Array<[string, unknown]>
            ).map(([label, value]) =>
              value ? (
                <div key={String(label)} className="space-y-1">
                  <dt className="text-zinc-500">{label}</dt>
                  <dd className="whitespace-pre-wrap">{String(value)}</dd>
                </div>
              ) : null,
            )}
          </dl>

          <details className="mt-3 text-[11px] text-zinc-500 dark:text-zinc-400">
            <summary className="cursor-pointer">Technical encounter UUIDs</summary>
            <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-[10px] text-zinc-700 dark:text-zinc-300">
              {JSON.stringify(
                {
                  organization: syntheaEncounter.organization,
                  provider: syntheaEncounter.provider,
                  payer: syntheaEncounter.payer,
                  encounter_code: syntheaEncounter.encounter_code,
                  reason_code: syntheaEncounter.reason_code,
                  reason_description: syntheaEncounter.reason_description,
                },
                null,
                2,
              )}
            </pre>
          </details>
        </section>
      ) : null}

      <GenerateNotePanel patientId={patient.id} />

      <details className="rounded-xl border border-dashed border-zinc-300 p-4 text-xs dark:border-zinc-700">
        <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-zinc-600">
          Raw structured_note JSON
        </summary>
        <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap text-[11px] text-zinc-800 dark:text-zinc-100">
          {JSON.stringify(sn, null, 2)}
        </pre>
      </details>
    </div>
  );
}
