"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE, EvidenceItem, TraceEvent, deleteEvidence, fetchEvidenceList, fetchSampleJD, streamRun } from "@/lib/api";
import { useRun } from "@/lib/RunContext";
import { Card, SectionTitle, EmptyState } from "@/components/ui";
import { AddEvidenceModal } from "@/components/AddEvidenceModal";

const TYPE_LABELS: Record<string, string> = {
  work_experience: "Work Experience",
  project: "Project",
  open_source_pr: "Open Source",
  education: "Education",
  certification: "Certification",
  skill_note: "Skill Note",
  achievement: "Achievement",
};

export default function InputPage() {
  const router = useRouter();
  const { setRunId } = useRun();
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [loadingEvidence, setLoadingEvidence] = useState(true);
  const [jdText, setJdText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [lastAddedId, setLastAddedId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const [selecting, setSelecting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const started = useRef(false);

  async function refreshEvidence(newId?: string) {
    try {
      const list = await fetchEvidenceList();
      setEvidence(list);
      if (newId) setLastAddedId(newId);
    } catch {
      setError("Could not refresh evidence from the backend.");
    }
  }

  function toggleSelecting() {
    setSelecting((s) => !s);
    setSelectedIds(new Set());
    setConfirmingDelete(false);
  }

  function toggleSelected(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function confirmDeleteSelected() {
    setDeleting(true);
    setError(null);
    try {
      await Promise.all([...selectedIds].map((id) => deleteEvidence(id)));
      await refreshEvidence();
      setSelecting(false);
      setSelectedIds(new Set());
      setConfirmingDelete(false);
    } catch {
      setError("Could not delete one or more selected items.");
    } finally {
      setDeleting(false);
    }
  }

  useEffect(() => {
    if (!lastAddedId) return;
    document.getElementById(`evidence-${lastAddedId}`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    const t = setTimeout(() => setLastAddedId(null), 2500);
    return () => clearTimeout(t);
  }, [lastAddedId, evidence]);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/evidence/ingest-default`, { method: "POST" });
        if (!res.ok) throw new Error(`ingest-default failed (${res.status})`);
        const list = await fetchEvidenceList();
        setEvidence(list);
      } catch {
        setError(
          "Could not reach the backend. Make sure the FastAPI server is running on " + API_BASE
        );
      } finally {
        setLoadingEvidence(false);
      }
    })();
  }, []);

  async function loadSample() {
    try {
      const text = await fetchSampleJD();
      setJdText(text);
    } catch {
      setError("Could not load the sample JD from the backend.");
    }
  }

  async function startPipeline() {
    if (!jdText.trim()) {
      setError("Paste a job description first.");
      return;
    }
    setError(null);
    setRunning(true);
    setRunMessage("Starting run...");
    try {
      await streamRun(jdText, (event: TraceEvent) => {
        setRunMessage(event.message);
        if (event.type === "run_started" && typeof event.run_id === "string") {
          setRunId(event.run_id);
        }
        if (event.type === "run_complete") {
          router.push("/report");
        }
        if (event.type === "error") {
          setRunning(false);
          setError(event.message);
        }
      });
    } catch (e) {
      setRunning(false);
      const message = e instanceof Error ? e.message : String(e);
      setError(
        `The pipeline run was interrupted before it could finish (${message}). This usually means the backend hit an error mid-run — check the backend logs, or try running again.`
      );
    }
  }

  const grouped: Record<string, EvidenceItem[]> = {};
  for (const e of evidence) {
    const t = e.metadata.type;
    grouped[t] = grouped[t] || [];
    grouped[t].push(e);
  }

  return (
    <div>
      {error && (
        <div className="mb-4 rounded-lg bg-rose-50 dark:bg-rose-900/20 text-rose-700 dark:text-rose-300 text-sm px-4 py-2">
          {error}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <Card photo>
          <SectionTitle>Job Description</SectionTitle>
          <textarea
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            placeholder="Paste the target job description here..."
            className="w-full h-64 rounded-lg border border-white/20 bg-black/20 text-white placeholder-white/50 p-3 text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-white/30"
          />
          <div className="flex gap-2 mt-3">
            <button
              onClick={loadSample}
              className="text-sm px-3 py-1.5 rounded-md border border-white/25 hover:bg-white/10"
            >
              Load sample JD
            </button>
            <button
              onClick={startPipeline}
              disabled={running}
              className="ml-auto text-sm px-4 py-1.5 rounded-md bg-white text-black font-medium hover:opacity-90 disabled:opacity-50"
            >
              {running ? "Running..." : "Run Pipeline →"}
            </button>
          </div>
          {running && runMessage && (
            <p className="mt-2 text-xs text-white/60 animate-pulse">{runMessage}</p>
          )}
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-3 gap-2">
            <h2 className="text-lg font-semibold">Candidate Evidence Store</h2>
            <div className="flex items-center gap-2">
              {selecting && confirmingDelete ? (
                <>
                  <span className="text-sm text-rose-600 font-medium">
                    Delete {selectedIds.size} item{selectedIds.size === 1 ? "" : "s"}?
                  </span>
                  <button
                    onClick={() => setConfirmingDelete(false)}
                    disabled={deleting}
                    className="text-base px-4 py-2 rounded-md border border-black/15 dark:border-white/20 font-semibold hover:bg-black/5 dark:hover:bg-white/10 disabled:opacity-50"
                  >
                    No
                  </button>
                  <button
                    onClick={confirmDeleteSelected}
                    disabled={deleting}
                    className="text-base px-4 py-2 rounded-md bg-rose-600 text-white font-semibold hover:opacity-90 disabled:opacity-50"
                  >
                    {deleting ? "Deleting..." : "Yes, delete"}
                  </button>
                </>
              ) : selecting ? (
                <>
                  <button
                    onClick={toggleSelecting}
                    className="text-base px-4 py-2 rounded-md border border-black/15 dark:border-white/20 font-semibold hover:bg-black/5 dark:hover:bg-white/10"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => setConfirmingDelete(true)}
                    disabled={selectedIds.size === 0}
                    className="text-base px-4 py-2 rounded-md bg-rose-600 text-white font-semibold hover:opacity-90 disabled:opacity-50"
                  >
                    {`Delete (${selectedIds.size})`}
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={toggleSelecting}
                    className="text-base px-4 py-2 rounded-md bg-rose-600 text-white font-semibold hover:opacity-90"
                  >
                    Delete work
                  </button>
                  <button
                    onClick={() => setShowAddModal(true)}
                    className="text-base px-4 py-2 rounded-md bg-black text-white dark:bg-white dark:text-black font-semibold hover:opacity-90"
                  >
                    + Add work
                  </button>
                </>
              )}
            </div>
          </div>
          {loadingEvidence ? (
            <p className="text-sm text-black/50 dark:text-white/50">Loading evidence...</p>
          ) : evidence.length === 0 ? (
            <EmptyState>No evidence loaded yet.</EmptyState>
          ) : (
            <div className="max-h-72 overflow-y-auto space-y-4 pr-1">
              {Object.entries(grouped).map(([type, items]) => (
                <div key={type}>
                  <div className="text-xs font-semibold uppercase tracking-wide text-black/40 dark:text-white/40 mb-1.5">
                    {TYPE_LABELS[type] || type}
                  </div>
                  <ul className="space-y-1.5">
                    {items.map((item, i) => (
                      <li
                        key={item.evidence_id}
                        id={`evidence-${item.evidence_id}`}
                        onClick={selecting ? () => toggleSelected(item.evidence_id) : undefined}
                        className={`text-sm flex items-start gap-2 rounded px-1 -mx-1 transition-colors duration-1000 ${
                          selecting ? "cursor-pointer hover:bg-black/5 dark:hover:bg-white/10" : ""
                        } ${
                          item.evidence_id === lastAddedId
                            ? "bg-emerald-500/20"
                            : selectedIds.has(item.evidence_id)
                            ? "bg-rose-500/10"
                            : ""
                        }`}
                      >
                        {selecting ? (
                          <input
                            type="checkbox"
                            checked={selectedIds.has(item.evidence_id)}
                            onChange={() => toggleSelected(item.evidence_id)}
                            onClick={(e) => e.stopPropagation()}
                            className="mt-0.5"
                          />
                        ) : (
                          <span className="text-black/40 dark:text-white/40 tabular-nums">{i + 1}.</span>
                        )}
                        <span className="text-black/80 dark:text-white/80 flex-1">{item.metadata.title}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {showAddModal && (
        <AddEvidenceModal onClose={() => setShowAddModal(false)} onAdded={refreshEvidence} />
      )}
    </div>
  );
}
