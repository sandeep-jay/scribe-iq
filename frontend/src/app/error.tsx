"use client";

/**
 * App Router error boundary for uncaught render/runtime errors in this subtree.
 * Logs a single structured line; user-facing copy stays generic.
 */

import { useEffect } from "react";

import { logError } from "@/lib/logger";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    logError("next_app_error_boundary", {
      message: error.message,
      digest: error.digest,
    });
  }, [error]);

  return (
    <div style={{ fontFamily: "system-ui", padding: 24 }}>
      <h2>Something went wrong</h2>
      <p>{error.message}</p>
      <button type="button" onClick={() => reset()}>
        Try again
      </button>
    </div>
  );
}
