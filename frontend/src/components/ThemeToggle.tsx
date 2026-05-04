"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "scribe-iq-theme";

type ThemeMode = "light" | "dark";

function readStored(): ThemeMode | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === "light" || raw === "dark") return raw;
  } catch {
    /* ignore */
  }
  return null;
}

function systemPrefersDark(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function applyDom(mode: ThemeMode) {
  document.documentElement.classList.toggle("dark", mode === "dark");
}

export function ThemeToggle({ className }: { className?: string }) {
  const [mode, setMode] = useState<ThemeMode>("light");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const stored = readStored();
    const initial: ThemeMode = stored ?? (systemPrefersDark() ? "dark" : "light");
    setMode(initial);
    applyDom(initial);
    setReady(true);

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (readStored() !== null) return;
      const next: ThemeMode = mq.matches ? "dark" : "light";
      setMode(next);
      applyDom(next);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const toggle = useCallback(() => {
    const next: ThemeMode = mode === "dark" ? "light" : "dark";
    setMode(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
    applyDom(next);
  }, [mode]);

  const label = mode === "dark" ? "Switch to light theme" : "Switch to dark theme";

  const base =
    "rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-800 shadow-sm hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800";

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      title={ready ? label : "Theme"}
      className={className ? `${base} ${className}` : base}
    >
      {ready ? (mode === "dark" ? "Light" : "Dark") : "…"}
    </button>
  );
}
