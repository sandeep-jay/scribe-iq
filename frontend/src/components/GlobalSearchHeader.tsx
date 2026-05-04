"use client";

import { useCallback, type KeyboardEvent as ReactKeyboardEvent } from "react";

import { usePatientsListSearchQuery } from "@/lib/usePatientsListSearchQuery";

function SearchAndUserRow({
  compact,
  searchValue,
  onSearchChange,
  onSearchKeyDown,
}: {
  compact?: boolean;
  searchValue: string;
  onSearchChange: (value: string) => void;
  onSearchKeyDown: (e: ReactKeyboardEvent<HTMLInputElement>) => void;
}) {
  return (
    <div className={`flex min-w-0 items-center gap-2 ${compact ? "" : "flex-1"}`}>
      <label htmlFor={compact ? "global-search-sm" : "global-search"} className="sr-only">
        Search patients by name or external id
      </label>
      <input
        id={compact ? "global-search-sm" : "global-search"}
        type="search"
        value={searchValue}
        onChange={(e) => onSearchChange(e.target.value)}
        onKeyDown={onSearchKeyDown}
        placeholder="Name or external id…"
        title="On the Patients list this filters the table (also in the URL as ?q=). On other pages press Enter to open Patients with this query. Specialty, chips, and advanced filters stay on the Patients page."
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

export function GlobalSearchHeaderSkeleton({ compact }: { compact?: boolean }) {
  return (
    <div className={`flex min-w-0 items-center gap-2 ${compact ? "" : "flex-1"}`} aria-hidden>
      <div className="h-9 min-w-0 flex-1 animate-pulse rounded-lg bg-zinc-100 dark:bg-zinc-800" />
      <div className="h-9 w-[5.5rem] shrink-0 animate-pulse rounded-full bg-zinc-100 dark:bg-zinc-800" />
    </div>
  );
}

export function GlobalSearchHeader({ compact }: { compact?: boolean }) {
  const { displayValue, setQuery, commitAwaySearch, onListPage } = usePatientsListSearchQuery();

  const onSearchKeyDown = useCallback(
    (e: ReactKeyboardEvent<HTMLInputElement>) => {
      if (e.key !== "Enter") return;
      if (onListPage) {
        e.preventDefault();
        return;
      }
      e.preventDefault();
      commitAwaySearch();
    },
    [commitAwaySearch, onListPage],
  );

  return (
    <SearchAndUserRow
      compact={compact}
      searchValue={displayValue}
      onSearchChange={setQuery}
      onSearchKeyDown={onSearchKeyDown}
    />
  );
}
