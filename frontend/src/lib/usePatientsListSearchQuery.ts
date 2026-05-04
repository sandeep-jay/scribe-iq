"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

export const PATIENTS_LIST_PATH = "/patients";

/**
 * Shared name / external-id filter for the Patients list, backed by `?q=` on `/patients`.
 * Elsewhere the same input is a draft until Enter navigates to the list.
 */
export function usePatientsListSearchQuery() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const onListPage = pathname === PATIENTS_LIST_PATH;
  const fromUrl = onListPage ? (searchParams.get("q") ?? "") : "";
  const [awayDraft, setAwayDraft] = useState("");

  useEffect(() => {
    if (onListPage) setAwayDraft("");
  }, [onListPage]);

  const displayValue = onListPage ? fromUrl : awayDraft;

  const setQuery = useCallback(
    (next: string) => {
      if (onListPage) {
        const p = new URLSearchParams(searchParams.toString());
        const t = next.trim();
        if (t) p.set("q", next);
        else p.delete("q");
        const qs = p.toString();
        router.replace(qs ? `${PATIENTS_LIST_PATH}?${qs}` : PATIENTS_LIST_PATH);
      } else {
        setAwayDraft(next);
      }
    },
    [onListPage, router, searchParams],
  );

  const commitAwaySearch = useCallback(() => {
    const t = awayDraft.trim();
    if (t) router.push(`${PATIENTS_LIST_PATH}?q=${encodeURIComponent(t)}`);
    else router.push(PATIENTS_LIST_PATH);
  }, [awayDraft, router]);

  return { displayValue, setQuery, commitAwaySearch, onListPage };
}
