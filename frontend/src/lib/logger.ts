/**
 * Minimal structured client logging (no PHI payloads).
 *
 * Levels follow a simple threshold model: when ``NEXT_PUBLIC_LOG_LEVEL`` is ``info``, you will see
 * ``info``, ``warn``, and ``error`` events, but not ``debug``. Use ``debug`` locally while tracing UI flows.
 *
 * Output is JSON lines to the browser console so you can copy/paste single events into tickets.
 */

export type LogLevel = "debug" | "info" | "warn" | "error";

const ORDER: LogLevel[] = ["debug", "info", "warn", "error"];

function configuredLevel(): LogLevel {
  const raw = (process.env.NEXT_PUBLIC_LOG_LEVEL ?? "info").toLowerCase();
  if (raw === "debug" || raw === "info" || raw === "warn" || raw === "error") return raw;
  return "info";
}

function shouldEmit(at: LogLevel): boolean {
  return ORDER.indexOf(at) >= ORDER.indexOf(configuredLevel());
}

function emit(level: LogLevel, event: string, fields: Record<string, unknown>): void {
  if (!shouldEmit(level)) return;
  const line = JSON.stringify({
    level,
    event,
    ts: new Date().toISOString(),
    ...fields,
  });
  if (level === "error") console.error(line);
  else if (level === "warn") console.warn(line);
  else console.log(line);
}

export function logDebug(event: string, fields: Record<string, unknown> = {}): void {
  emit("debug", event, fields);
}

export function logInfo(event: string, fields: Record<string, unknown> = {}): void {
  emit("info", event, fields);
}

export function logWarn(event: string, fields: Record<string, unknown> = {}): void {
  emit("warn", event, fields);
}

export function logError(event: string, fields: Record<string, unknown> = {}): void {
  emit("error", event, fields);
}
