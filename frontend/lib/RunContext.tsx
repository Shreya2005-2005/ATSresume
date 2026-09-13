"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";

interface RunContextValue {
  runId: string | null;
  setRunId: (id: string | null) => void;
}

const RunContext = createContext<RunContextValue>({ runId: null, setRunId: () => {} });

const STORAGE_KEY = "ats.currentRunId";

export function RunProvider({ children }: { children: ReactNode }) {
  const [runId, setRunIdState] = useState<string | null>(null);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) setRunIdState(stored);
  }, []);

  function setRunId(id: string | null) {
    setRunIdState(id);
    if (id) window.localStorage.setItem(STORAGE_KEY, id);
    else window.localStorage.removeItem(STORAGE_KEY);
  }

  return <RunContext.Provider value={{ runId, setRunId }}>{children}</RunContext.Provider>;
}

export function useRun() {
  return useContext(RunContext);
}
