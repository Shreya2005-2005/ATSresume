"use client";

import { ChangeEvent, useRef, useState } from "react";
import Link from "next/link";
import { EvidenceType, ExtractedEvidenceItem, createEvidence, extractResumeEvidence } from "@/lib/api";
import { Card, PageTitle } from "@/components/ui";

const TYPE_OPTIONS: { value: EvidenceType; label: string }[] = [
  { value: "work_experience", label: "Work Experience" },
  { value: "project", label: "Project" },
  { value: "open_source_pr", label: "Open Source (Merged PR)" },
  { value: "achievement", label: "Hackathon / Achievement" },
  { value: "certification", label: "Certification" },
  { value: "education", label: "Education" },
  { value: "skill_note", label: "Skill Note" },
];

interface ReviewItem extends ExtractedEvidenceItem {
  include: boolean;
}

export default function AddResumePage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [items, setItems] = useState<ReviewItem[] | null>(null);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedCount, setSavedCount] = useState<number | null>(null);

  async function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setExtracting(true);
    setExtractError(null);
    setItems(null);
    setSavedCount(null);
    try {
      const result = await extractResumeEvidence(file);
      setItems(result.items.map((it) => ({ ...it, include: true })));
    } catch (e) {
      setExtractError(String(e));
    } finally {
      setExtracting(false);
    }
  }

  function updateItem(index: number, patch: Partial<ReviewItem>) {
    setItems((prev) => (prev ? prev.map((it, i) => (i === index ? { ...it, ...patch } : it)) : prev));
  }

  function removeItem(index: number) {
    setItems((prev) => (prev ? prev.filter((_, i) => i !== index) : prev));
  }

  async function handleAddSelected() {
    if (!items) return;
    const selected = items.filter((it) => it.include);
    if (selected.length === 0) return;
    setSaving(true);
    setSaveError(null);
    try {
      for (const it of selected) {
        await createEvidence({
          type: it.type,
          title: it.title,
          description: it.description,
          metrics: it.metrics || undefined,
          skills: it.skills,
          source_link: it.source_link || undefined,
          date_range: it.date_range || undefined,
        });
      }
      setSavedCount(selected.length);
      setItems(null);
      setFileName(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (e) {
      setSaveError(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <PageTitle subtitle="Upload an existing resume and the agent will pull out your work experience, projects, and skills as evidence reviewed by you before anything is saved.">
        Add Resume
      </PageTitle>

      <Card className="mb-6">
        <div className="flex items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt"
            onChange={handleFileChange}
            className="text-sm"
          />
          {extracting && <span className="text-sm text-black/50 dark:text-white/50 animate-pulse">Reading {fileName}...</span>}
        </div>
        <p className="text-xs text-black/40 dark:text-white/40 mt-2">Accepts PDF or plain text (.txt) resumes.</p>
        {extractError && <p className="text-sm text-rose-600 mt-2">{extractError}</p>}
      </Card>

      {savedCount !== null && (
        <div className="mb-6 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 text-sm px-4 py-3">
          Added {savedCount} item{savedCount === 1 ? "" : "s"} to your Candidate Evidence Store.{" "}
          <Link href="/input" className="underline font-medium">
            View it on the Input page
          </Link>{" "}
          or upload another resume above.
        </div>
      )}

      {items && items.length === 0 && (
        <p className="text-sm text-black/50 dark:text-white/50">No items left to add.</p>
      )}

      {items && items.length > 0 && (
        <div>
          <p className="text-sm text-black/60 dark:text-white/60 mb-3">
            Found {items.length} item{items.length === 1 ? "" : "s"}. Review and edit before adding — uncheck
            anything that isn&apos;t accurate.
          </p>
          <div className="space-y-3 mb-4">
            {items.map((it, i) => (
              <Card key={i}>
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={it.include}
                    onChange={(e) => updateItem(i, { include: e.target.checked })}
                    className="mt-1.5"
                  />
                  <div className="flex-1 space-y-2">
                    <div className="flex gap-2">
                      <select
                        value={it.type}
                        onChange={(e) => updateItem(i, { type: e.target.value as EvidenceType })}
                        className="text-sm rounded-md border border-black/15 dark:border-white/20 bg-transparent px-2 py-1"
                      >
                        {TYPE_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                      <input
                        value={it.title}
                        onChange={(e) => updateItem(i, { title: e.target.value })}
                        placeholder="Title"
                        className="flex-1 text-sm font-medium rounded-md border border-black/15 dark:border-white/20 bg-transparent px-2 py-1"
                      />
                      <input
                        value={it.date_range || ""}
                        onChange={(e) => updateItem(i, { date_range: e.target.value })}
                        placeholder="Date range"
                        className="w-40 text-sm rounded-md border border-black/15 dark:border-white/20 bg-transparent px-2 py-1"
                      />
                      <button
                        onClick={() => removeItem(i)}
                        title="Remove"
                        className="text-rose-600 text-sm px-2 rounded hover:bg-rose-50 dark:hover:bg-rose-900/20"
                      >
                        ✕
                      </button>
                    </div>
                    <textarea
                      value={it.description}
                      onChange={(e) => updateItem(i, { description: e.target.value })}
                      rows={2}
                      className="w-full text-sm rounded-md border border-black/15 dark:border-white/20 bg-transparent px-2 py-1"
                    />
                    <div className="flex gap-2">
                      <input
                        value={it.skills.join(", ")}
                        onChange={(e) =>
                          updateItem(i, {
                            skills: e.target.value
                              .split(",")
                              .map((s) => s.trim())
                              .filter(Boolean),
                          })
                        }
                        placeholder="Skills (comma separated)"
                        className="flex-1 text-sm rounded-md border border-black/15 dark:border-white/20 bg-transparent px-2 py-1"
                      />
                      <input
                        value={it.source_link || ""}
                        onChange={(e) => updateItem(i, { source_link: e.target.value })}
                        placeholder="Link (optional)"
                        className="flex-1 text-sm rounded-md border border-black/15 dark:border-white/20 bg-transparent px-2 py-1"
                      />
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>

          {saveError && <p className="text-sm text-rose-600 mb-3">{saveError}</p>}

          <button
            onClick={handleAddSelected}
            disabled={saving || items.filter((it) => it.include).length === 0}
            className="text-sm px-4 py-2 rounded-md bg-black text-white dark:bg-white dark:text-black font-medium hover:opacity-90 disabled:opacity-50"
          >
            {saving
              ? "Adding..."
              : `Add ${items.filter((it) => it.include).length} item${
                  items.filter((it) => it.include).length === 1 ? "" : "s"
                } to Evidence Store`}
          </button>
        </div>
      )}
    </div>
  );
}
