"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ThemeToggle } from "@/components/ThemeToggle";

function navLinkClass(active: boolean) {
  return active
    ? "rounded-lg bg-zinc-800 px-3 py-2 text-sm font-medium text-white"
    : "rounded-lg px-3 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-800/80 hover:text-white";
}

function SearchAndUserRow({ compact }: { compact?: boolean }) {
  return (
    <div className={`flex min-w-0 items-center gap-2 ${compact ? "" : "flex-1"}`}>
      <label htmlFor={compact ? "global-search-sm" : "global-search"} className="sr-only">
        Search patients
      </label>
      <input
        id={compact ? "global-search-sm" : "global-search"}
        type="search"
        readOnly
        placeholder="Search patients…"
        title="Patient search is planned for Phase B; table search works on the Patients page today."
        className="min-w-0 flex-1 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:placeholder:text-zinc-500"
      />
      <div
        className="flex shrink-0 items-center gap-2 rounded-full border border-zinc-200 bg-zinc-50 py-1 pl-1 pr-3 dark:border-zinc-700 dark:bg-zinc-900"
        title="Demo only — no sign-in in this build"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-xs font-semibold text-white">
          SI
        </span>
        {!compact ? <span className="hidden text-xs text-zinc-600 sm:inline dark:text-zinc-300">Demo clinician</span> : null}
      </div>
    </div>
  );
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
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeMobile();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileOpen, closeMobile]);

  const patientsActive = pathname === "/patients" || pathname.startsWith("/patients/");
  const chatActive = pathname.startsWith("/chat");
  const docsActive = pathname.startsWith("/docs");

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
    </nav>
  );

  const sidebarToggle =
    "w-full border-zinc-700 bg-zinc-900 text-zinc-100 shadow-none hover:bg-zinc-800 dark:border-zinc-600 dark:bg-zinc-800 dark:hover:bg-zinc-700";

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-56 shrink-0 flex-col border-r border-zinc-800 bg-zinc-950 text-zinc-100 md:flex">
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

      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
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
            <SearchAndUserRow compact />
          </div>
        </div>

        <div className="sticky top-0 z-30 hidden border-b border-zinc-200 bg-white/95 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/95 md:block">
          <div className="mx-auto flex max-w-6xl items-center gap-4 px-6 py-2.5">
            <SearchAndUserRow />
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

        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">{children}</main>
      </div>
    </div>
  );
}
