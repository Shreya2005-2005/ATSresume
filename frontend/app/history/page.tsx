"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RunSummary, fetchRuns, renameRun, resumePdfUrl } from "@/lib/api";
import { useRun } from "@/lib/RunContext";
import { Chip, PageTitle, EmptyState } from "@/components/ui";

const STATUS_TONE: Record<string, "good" | "warn"> = {
  verified: "good",
  needs_human_review: "warn",
};

export default function HistoryPage() {
  const router = useRouter();
  const { runId, setRunId } = useRun();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [renaming, setRenaming] = useState(false);

  useEffect(() => {
    fetchRuns()
      .then(setRuns)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  function viewRun(id: string) {
    setRunId(id);
    router.push("/report");
  }

  function startEditing(run: RunSummary) {
    setEditingId(run.run_id);
    setEditValue(run.company_name || "");
  }

  async function saveRename(id: string) {
    const label = editValue.trim();
    if (!label) return;
    setRenaming(true);
    try {
      await renameRun(id, label);
      setRuns((prev) => prev.map((r) => (r.run_id === id ? { ...r, company_name: label } : r)));
      setEditingId(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setRenaming(false);
    }
  }

  return (
    <div>
      <PageTitle subtitle="Every past run that produced a resume. Pick one up to view or re-download it.">
        Resume History
      </PageTitle>

      {loading && <p className="text-sm text-black/50 dark:text-white/50">Loading history...</p>}
      {error && <p className="text-sm text-rose-600">{error}</p>}

      {!loading && !error && runs.length === 0 && (
        <EmptyState>No saved resumes yet. Run the pipeline from the Input page to create one.</EmptyState>
      )}

      {runs.length > 0 && (
        <div className="rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-white/5 shadow-sm overflow-hidden">
          <ul className="divide-y divide-black/10 dark:divide-white/10">
            {runs.map((run) => (
              <li
                key={run.run_id}
                className={`flex items-center justify-between gap-4 px-5 py-3 ${
                  run.run_id === runId ? "bg-black/5 dark:bg-white/5" : ""
                }`}
              >
                <div className="min-w-0 flex-1">
                  {editingId === run.run_id ? (
                    <div className="flex items-center gap-2">
                      <input
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") saveRename(run.run_id);
                          if (e.key === "Escape") setEditingId(null);
                        }}
                        placeholder="Name this resume..."
                        className="text-sm font-medium rounded-md border border-black/15 dark:border-white/20 bg-transparent px-2 py-1 flex-1"
                      />
                      <button
                        onClick={() => saveRename(run.run_id)}
                        disabled={renaming || !editValue.trim()}
                        className="text-xs px-2.5 py-1 rounded-md bg-black text-white dark:bg-white dark:text-black font-medium hover:opacity-90 disabled:opacity-50"
                      >
                        {renaming ? "Saving..." : "Save"}
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="text-xs px-2.5 py-1 rounded-md border border-black/15 dark:border-white/20 hover:bg-black/5 dark:hover:bg-white/10"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm truncate">{run.company_name || "Untitled run"}</span>
                      {run.final_status && (
                        <Chip tone={STATUS_TONE[run.final_status] || "neutral"}>{run.final_status}</Chip>
                      )}
                      <button
                        onClick={() => startEditing(run)}
                        title="Rename"
                        className="text-xs text-black/40 dark:text-white/40 hover:text-black/70 dark:hover:text-white/70"
                      >
                        ✎ Rename
                      </button>
                    </div>
                  )}
                  <div className="text-xs text-black/40 dark:text-white/40 mt-0.5">
                    {new Date(run.updated_at * 1000).toLocaleString()}
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => viewRun(run.run_id)}
                    className="text-sm px-3 py-1.5 rounded-md border border-black/15 dark:border-white/20 hover:bg-black/5 dark:hover:bg-white/10"
                  >
                    View
                  </button>
                  <a
                    href={resumePdfUrl(run.run_id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm px-3 py-1.5 rounded-md bg-black text-white dark:bg-white dark:text-black font-medium hover:opacity-90"
                  >
                    Download PDF
                  </a>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
