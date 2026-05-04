import type { PaginatedPatients } from "@/lib/backend";
import { fetchCorpusPatientStats, fetchPatients } from "@/lib/backend";
import { PatientsExplorer } from "@/components/PatientsExplorer";

export default async function PatientsPage() {
  let data: PaginatedPatients;
  let stats;
  try {
    [data, stats] = await Promise.all([fetchPatients({ limit: 200, offset: 0 }), fetchCorpusPatientStats()]);
  } catch (e) {
    return (
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">Patients</h1>
        <p className="text-sm text-red-600">
          Could not reach the backend: {(e as Error).message}. Start FastAPI (`uvicorn …`) on{" "}
          <code>NEXT_PUBLIC_SCRIBE_API_BASE</code>.
        </p>
      </div>
    );
  }

  return <PatientsExplorer patients={data.patients} stats={stats} />;
}
