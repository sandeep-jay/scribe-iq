"use client";

import { useEffect, useRef, useState } from "react";

import { MeetingPrepPanel } from "@/components/MeetingPrepPanel";

/**
 * Defers meeting-prep (DB + optional Groq) until near viewport or explicit user action,
 * so the chart shell renders without blocking on AI.
 */
export function DeferredMeetingPrepPanel({ patientId }: { patientId: string }) {
  const anchorRef = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const h = window.location.hash.replace(/^#/, "");
      if (h === "chart-prep") {
        setActive(true);
        return;
      }
    }

    const el = anchorRef.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      setActive(true);
      return;
    }

    const obs = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) setActive(true);
      },
      { root: null, rootMargin: "280px 0px 160px 0px", threshold: 0.01 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    const onHash = () => {
      const h = window.location.hash.replace(/^#/, "");
      if (h === "chart-prep") setActive(true);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  return (
    <div ref={anchorRef} className="min-h-[9rem]">
      {active ? (
        <MeetingPrepPanel patientId={patientId} />
      ) : (
        <div className="rounded-xl border border-dashed border-indigo-200 bg-white/60 p-4 text-sm text-indigo-900/80 dark:border-indigo-900 dark:bg-indigo-950/20 dark:text-indigo-100">
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-800/80 dark:text-indigo-200/90">
            Pre-meeting summary
          </p>
          <p className="mt-2 text-xs leading-relaxed text-indigo-900/70 dark:text-indigo-200/70">
            Loads when this section comes into view — keeps the chart responsive while Groq prepares the narrative.
          </p>
          <p className="mt-3 text-[11px] text-indigo-800/60 dark:text-indigo-200/60">
            <button
              type="button"
              className="font-medium underline decoration-indigo-300 underline-offset-2"
              onClick={() => setActive(true)}
            >
              Load now
            </button>
          </p>
        </div>
      )}
    </div>
  );
}
