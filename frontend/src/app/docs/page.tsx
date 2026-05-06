import Link from "next/link";

export default function DocsPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Documentation</h1>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">
          In-repo specs (Markdown) live under <code className="rounded bg-zinc-100 px-1 py-0.5 text-xs dark:bg-zinc-800">docs/roadmap/</code> and{" "}
          <code className="rounded bg-zinc-100 px-1 py-0.5 text-xs dark:bg-zinc-800">docs/reference/</code> in the Scribe-IQ repository. Open them in your editor or
          viewer alongside this demo. A consolidated map lives under{" "}
          <code className="rounded bg-zinc-100 px-1 py-0.5 text-xs dark:bg-zinc-800">docs/README.md</code>.
        </p>
      </div>

      <section className="rounded-xl border border-zinc-200 p-5 text-sm dark:border-zinc-800">
        <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">App</p>
        <ul className="mt-3 space-y-2 text-zinc-800 dark:text-zinc-100">
          <li>
            <Link className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400" href="/patients">
              Patients
            </Link>{" "}
            — corpus list and chart entry.
          </li>
          <li>
            <Link className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400" href="/chat">
              Chat
            </Link>{" "}
            — grounded RAG demo (when embeddings are configured).
          </li>
        </ul>
      </section>

      <section className="rounded-xl border border-zinc-200 p-5 text-sm dark:border-zinc-800">
        <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">UI roadmap (Phase A–D)</p>
        <p className="mt-2 text-zinc-600 dark:text-zinc-300">
          See <code className="rounded bg-zinc-100 px-1 text-xs dark:bg-zinc-800">docs/architecture/IMPLEMENTED_BASELINE.md</code> for a concise inventory of <strong>implemented</strong> API, UI, and database behavior.
        </p>
        <p className="mt-2 text-zinc-600 dark:text-zinc-300">
          See <code className="rounded bg-zinc-100 px-1 text-xs dark:bg-zinc-800">docs/architecture/CURRENT.md</code> for a short narrative of the current system (with pointers into roadmaps and references).
        </p>
        <p className="mt-2 text-zinc-600 dark:text-zinc-300">
          See <code className="rounded bg-zinc-100 px-1 text-xs dark:bg-zinc-800">docs/roadmap/SCRIBE_IQ_UI_ROADMAP.md</code> for shell, discoverability, patients index, chart depth, and encounter workspace plans.
        </p>
      </section>
    </div>
  );
}
