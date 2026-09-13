"use client";

import { FormEvent, useState } from "react";
import { CreateEvidenceInput, EvidenceType, createEvidence } from "@/lib/api";

const TYPE_OPTIONS: { value: EvidenceType; label: string }[] = [
  { value: "work_experience", label: "Work Experience" },
  { value: "project", label: "Project" },
  { value: "open_source_pr", label: "Open Source (Merged PR)" },
  { value: "achievement", label: "Hackathon" },
  { value: "certification", label: "Certification" },
];

export function AddEvidenceModal({
  onClose,
  onAdded,
}: {
  onClose: () => void;
  onAdded: (newId: string) => void;
}) {
  const [type, setType] = useState<EvidenceType>("project");
  const [description, setDescription] = useState("");
  const [sourceLink, setSourceLink] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function deriveTitle(desc: string): string {
    const trimmed = desc.trim().replace(/\s+/g, " ");
    if (trimmed.length <= 60) return trimmed.replace(/[.,;:]+$/, "");
    const cut = trimmed.slice(0, 60);
    const lastSpace = cut.lastIndexOf(" ");
    return (lastSpace > 20 ? cut.slice(0, lastSpace) : cut) + "…";
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!description.trim()) {
      setError("Description is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const input: CreateEvidenceInput = {
        type,
        title: deriveTitle(description),
        description: description.trim(),
        skills: [],
        source_link: sourceLink.trim() || undefined,
      };
      const created = await createEvidence(input);
      onAdded(created.id);
      onClose();
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-xl bg-white dark:bg-neutral-900 border border-black/10 dark:border-white/10 shadow-xl max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <form onSubmit={handleSubmit} className="p-5 space-y-3">
          <h2 className="text-lg font-semibold">Add work / evidence</h2>
          <p className="text-xs text-black/50 dark:text-white/50">
            This becomes a fact the resume agent is allowed to cite. Only add things you can back up.
          </p>

          <div>
            <label className="block text-xs font-medium text-black/60 dark:text-white/60 mb-1">Type</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value as EvidenceType)}
              className="w-full rounded-md border border-black/15 dark:border-white/20 bg-transparent px-3 py-1.5 text-sm"
            >
              {TYPE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-black/60 dark:text-white/60 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              placeholder="Mention everything: what it was, what you did, dates, outcomes/metrics..."
              className="w-full rounded-md border border-black/15 dark:border-white/20 bg-transparent px-3 py-1.5 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-black/60 dark:text-white/60 mb-1">GitHub link</label>
            <input
              value={sourceLink}
              onChange={(e) => setSourceLink(e.target.value)}
              placeholder="https://github.com/you/project"
              className="w-full rounded-md border border-black/15 dark:border-white/20 bg-transparent px-3 py-1.5 text-sm"
            />
          </div>

          {error && <p className="text-sm text-rose-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="text-sm px-4 py-2 rounded-md border border-black/15 dark:border-white/20 hover:bg-black/5 dark:hover:bg-white/10"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="text-sm px-4 py-2 rounded-md bg-black text-white dark:bg-white dark:text-black font-medium hover:opacity-90 disabled:opacity-50"
            >
              {submitting ? "Adding..." : "Add"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
