"use client";

import { useEffect, useState } from "react";
import { fetchState, RunState } from "@/lib/api";
import { useRun } from "@/lib/RunContext";

export function useRunState() {
  const { runId } = useRun();
  const [state, setState] = useState<RunState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    fetchState(runId)
      .then(setState)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [runId]);

  return { runId, state, loading, error };
}
