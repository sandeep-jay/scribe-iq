"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { GlobalSearchHeader, GlobalSearchHeaderSkeleton } from "@/components/GlobalSearchHeader";
import { ThemeToggle } from "@/components/ThemeToggle";

function navLinkClass(active: boolean) {
  return active
    ? "rounded-lg bg-zinc-800 px-3 py-2 text-sm font-medium text-white"
    : "rounded-lg px-3 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-800/80 hover:text-white";
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const closeMobile = useCallback(() => setMobileOpen(false), []);

  useEffect(() => {
    closeMobile();
  }, [pathname, closeMobile]);

  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") closeMobile();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileOpen, closeMobile]);

  const patientsActive = pathname === "/patients" || pathname.startsWith("/patients/");
  const chatActive = pathname.startsWith("/chat");
  const docsActive = pathname.startsWith("/docs");
  const adminRaActive = pathname.startsWith("/admin/responsible-ai");
  const showResponsibleAiAdmin = process.env.NEXT_PUBLIC_SCRIBE_ADMIN_UI === "true";

  const sidebarNav = (
    <nav className="flex flex-col gap-1">
      <Link href="/patients" className={navLinkClass(patientsActive)} onClick={closeMobile}>
        Patients
      </Link>
      <Link href="/chat" className={navLinkClass(chatActive)} onClick={closeMobile}>
        Chat
      </Link>
      <Link href="/docs" className={navLinkClass(docsActive)} onClick={closeMobile}>
        Docs
      </Link>
      {showResponsibleAiAdmin ? (
        <Link
          href="/admin/responsible-ai"
          className={navLinkClass(adminRaActive)}
          onClick={closeMobile}
        >
          Responsible AI
        </Link>
      ) : null}
    </nav>
  );

  const sidebarToggle =
    "w-full border-zinc-700 bg-zinc-900 text-zinc-100 shadow-none hover:bg-zinc-800 dark:border-zinc-600 dark:bg-zinc-800 dark:hover:bg-zinc-700";

  return (
    <div className="flex min-h-screen flex-col md:h-screen md:flex-row md:overflow-hidden">
      <aside className="hidden w-56 shrink-0 flex-col border-r border-zinc-800 bg-zinc-950 text-zinc-100 md:flex md:h-full md:overflow-y-auto">
        <div className="flex flex-col gap-6 p-4">
          <Link href="/patients" className="font-semibold tracking-tight text-white" onClick={closeMobile}>
            Scribe-IQ
          </Link>
          {sidebarNav}
        </div>
        <div className="mt-auto border-t border-zinc-800 p-4">
          <ThemeToggle className={sidebarToggle} />
        </div>
      </aside>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col md:h-full md:overflow-hidden">
        <div className="sticky top-0 z-40 border-b border-zinc-200 bg-white/95 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/95 md:hidden">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
            <button
              type="button"
              aria-expanded={mobileOpen}
              aria-controls="mobile-nav"
              className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs font-semibold uppercase tracking-wide text-zinc-800 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
              onClick={() => setMobileOpen((o) => !o)}
            >
              Menu
            </button>
            <Link href="/patients" className="font-semibold tracking-tight text-zinc-900 dark:text-white">
              Scribe-IQ
            </Link>
            <ThemeToggle />
          </div>
          <div className="mx-auto flex max-w-6xl items-center gap-2 border-t border-zinc-100 px-4 py-2 dark:border-zinc-800">
            <Suspense fallback={<GlobalSearchHeaderSkeleton compact />}>
              <GlobalSearchHeader compact />
            </Suspense>
          </div>
        </div>

        <div className="sticky top-0 z-30 hidden border-b border-zinc-200 bg-white/95 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/95 md:block">
          <div className="mx-auto flex max-w-6xl items-center gap-4 px-6 py-2.5">
            <Suspense fallback={<GlobalSearchHeaderSkeleton />}>
              <GlobalSearchHeader />
            </Suspense>
          </div>
        </div>

        {mobileOpen ? (
          <>
            <button
              type="button"
              aria-label="Close menu"
              className="fixed inset-0 z-40 bg-black/40 md:hidden"
              onClick={closeMobile}
            />
            <div
              id="mobile-nav"
              className="fixed inset-y-0 left-0 z-50 flex w-64 max-w-[85vw] flex-col border-r border-zinc-800 bg-zinc-950 p-4 text-zinc-100 shadow-xl md:hidden"
            >
              <div className="mb-4 flex items-center justify-between gap-2">
                <span className="text-xs font-semibold uppercase tracking-wide text-zinc-400">Navigate</span>
                <button
                  type="button"
                  className="rounded-lg px-2 py-1 text-xs text-zinc-300 hover:bg-zinc-800 hover:text-white"
                  onClick={closeMobile}
                >
                  Close
                </button>
              </div>
              {sidebarNav}
              <div className="mt-auto border-t border-zinc-800 pt-4">
                <ThemeToggle className={sidebarToggle} />
              </div>
            </div>
          </>
        ) : null}

        <main className="mx-auto w-full min-w-0 max-w-6xl flex-1 px-6 py-10 md:min-h-0 md:overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
