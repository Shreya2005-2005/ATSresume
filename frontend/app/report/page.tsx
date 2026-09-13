"use client";

import { useEffect, useMemo, useState } from "react";
import {
  EvidenceItem,
  Profile,
  ResumeBullet,
  ResumeDraft,
  chatEditDraft,
  fetchEvidenceList,
  fetchLatexResume,
  fetchProfile,
  renderResumePdf,
  saveDraft,
  saveProfile,
} from "@/lib/api";
import { useRunState } from "@/lib/useRunState";
import { Card, PageTitle, NoRunNotice } from "@/components/ui";

const SECTION_ORDER = ["Experience", "Projects", "Open Source", "Achievements"];

function newBulletId(): string {
  return `bullet-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

interface ChatMessage {
  role: "user" | "agent" | "error";
  text: string;
}

export default function ReportPage() {
  const { runId, state, loading: stateLoading } = useRunState();

  const [profile, setProfile] = useState<Profile | null>(null);
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [draft, setDraft] = useState<ResumeDraft | null>(null);

  const [editing, setEditing] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedJustNow, setSavedJustNow] = useState(false);

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  const [showLatexModal, setShowLatexModal] = useState(false);
  const [latexCode, setLatexCode] = useState("");
  const [latexLoading, setLatexLoading] = useState(false);
  const [latexError, setLatexError] = useState<string | null>(null);
  const [latexCopied, setLatexCopied] = useState(false);

  useEffect(() => {
    fetchProfile().then(setProfile).catch(() => {});
    fetchEvidenceList().then(setEvidenceList).catch(() => {});
  }, []);

  useEffect(() => {
    if (draft || !state) return;
    const source = state.draft_versions.final ?? state.draft_versions.v2 ?? state.draft_versions.v1;
    if (source) setDraft(structuredClone(source));
  }, [state, draft]);

  const sections = useMemo(() => {
    if (!draft) return [] as { name: string; bullets: ResumeBullet[] }[];
    const map = new Map<string, ResumeBullet[]>();
    for (const b of draft.bullets) {
      if (!map.has(b.section)) map.set(b.section, []);
      map.get(b.section)!.push(b);
    }
    const ordered = SECTION_ORDER.filter((s) => map.has(s));
    const extras = [...map.keys()].filter((s) => !SECTION_ORDER.includes(s));
    return [...ordered, ...extras].map((name) => ({ name, bullets: map.get(name)! }));
  }, [draft]);

  const { skills, education, certifications } = useMemo(() => {
    const skillSet = new Set<string>();
    const edu: EvidenceItem["metadata"][] = [];
    const certs: EvidenceItem["metadata"][] = [];
    for (const e of evidenceList) {
      const meta = e.metadata;
      if (meta.type === "skill_note" && meta.skills) {
        meta.skills
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
          .forEach((s) => skillSet.add(s));
      } else if (meta.type === "education") {
        edu.push(meta);
      } else if (meta.type === "certification") {
        certs.push(meta);
      }
    }
    return { skills: [...skillSet].sort(), education: edu, certifications: certs };
  }, [evidenceList]);

  function updateBullet(id: string, patch: Partial<ResumeBullet>) {
    setDraft((d) => (d ? { ...d, bullets: d.bullets.map((b) => (b.id === id ? { ...b, ...patch } : b)) } : d));
  }

  function removeBullet(id: string) {
    setDraft((d) => (d ? { ...d, bullets: d.bullets.filter((b) => b.id !== id) } : d));
  }

  function addBullet(section: string) {
    setDraft((d) =>
      d
        ? {
            ...d,
            bullets: [
              ...d.bullets,
              { id: newBulletId(), section, title: "", date_range: "", text: "", evidence_ids: [], skills: [], source_link: null },
            ],
          }
        : d
    );
  }

  function resetDraft() {
    const source = state?.draft_versions.final ?? state?.draft_versions.v2 ?? state?.draft_versions.v1;
    if (source) setDraft(structuredClone(source));
  }

  async function handleDoneEditing() {
    if (!draft || !runId || !profile) {
      setEditing(false);
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      await Promise.all([saveDraft(runId, draft), saveProfile(profile)]);
      setEditing(false);
      setSavedJustNow(true);
      setTimeout(() => setSavedJustNow(false), 2500);
    } catch (e) {
      setSaveError(String(e));
    } finally {
      setSaving(false);
    }
  }

  async function handleSave() {
    if (!draft || !runId || !profile) return;
    setSaving(true);
    setSaveError(null);
    try {
      await Promise.all([saveDraft(runId, draft), saveProfile(profile)]);
      // Regenerate the persisted PDF too, so this run's file (and its
      // timestamp in History) reflects the latest saved draft, not just
      // whatever was on disk from the original pipeline run.
      await renderResumePdf(draft, runId);
      setSavedJustNow(true);
      setTimeout(() => setSavedJustNow(false), 2500);
    } catch (e) {
      setSaveError(String(e));
    } finally {
      setSaving(false);
    }
  }

  async function handleGetLatex() {
    if (!draft) return;
    setLatexLoading(true);
    setLatexError(null);
    setLatexCopied(false);
    try {
      const code = await fetchLatexResume(draft);
      setLatexCode(code);
      setShowLatexModal(true);
    } catch (e) {
      setLatexError(String(e));
    } finally {
      setLatexLoading(false);
    }
  }

  async function handleCopyLatex() {
    try {
      await navigator.clipboard.writeText(latexCode);
      setLatexCopied(true);
      setTimeout(() => setLatexCopied(false), 2000);
    } catch {
      // clipboard API may be blocked; the textarea is still selectable/copyable by hand
    }
  }

  async function handleSendChat() {
    const instruction = chatInput.trim();
    if (!instruction || !draft || !runId || chatLoading) return;
    setChatMessages((m) => [...m, { role: "user", text: instruction }]);
    setChatInput("");
    setChatLoading(true);
    try {
      const res = await chatEditDraft(runId, instruction, draft);
      setDraft(res.draft);
      let text = res.explanation;
      if (res.rejected_bullet_ids.length > 0) {
        text += ` (Bullet id(s) ${res.rejected_bullet_ids.join(", ")} couldn't be verified and were reverted.)`;
      }
      setChatMessages((m) => [...m, { role: "agent", text }]);
    } catch (e) {
      setChatMessages((m) => [...m, { role: "error", text: String(e) }]);
    } finally {
      setChatLoading(false);
    }
  }

  async function handleDownload() {
    if (!draft || !runId) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      const blob = await renderResumePdf(draft, runId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "resume.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setDownloadError(String(e));
    } finally {
      setDownloading(false);
    }
  }

  if (!runId) return <NoRunNotice />;

  return (
    <div>
      <PageTitle>Final Report</PageTitle>

      {stateLoading && <p className="text-sm text-black/50 dark:text-white/50 mb-4">Loading resume...</p>}

      {!stateLoading && !draft && (
        <p className="text-sm text-black/50 dark:text-white/50 mb-6">Resume draft not available for this run yet.</p>
      )}

      {draft && (
        <div className="mb-8 grid lg:grid-cols-[minmax(0,1fr)_360px] gap-6 items-start">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <button
              onClick={() => (editing ? handleDoneEditing() : setEditing(true))}
              disabled={saving}
              className="text-sm px-4 py-2 rounded-md border border-black/15 dark:border-white/20 font-medium hover:bg-black/5 dark:hover:bg-white/10 disabled:opacity-50"
            >
              {saving ? "Saving..." : editing ? "Save & done editing" : "Edit resume"}
            </button>
            {editing && (
              <button
                onClick={resetDraft}
                className="text-sm px-4 py-2 rounded-md border border-black/15 dark:border-white/20 font-medium hover:bg-black/5 dark:hover:bg-white/10"
              >
                Reset changes
              </button>
            )}
            {savedJustNow && <span className="text-sm text-emerald-600 font-medium">Saved ✓</span>}
            <button
              onClick={handleSave}
              disabled={saving}
              className="text-sm px-4 py-2 rounded-md border border-black/15 dark:border-white/20 font-medium hover:bg-black/5 dark:hover:bg-white/10 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save"}
            </button>
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="text-sm px-4 py-2 rounded-md bg-black text-white dark:bg-white dark:text-black font-medium hover:opacity-90 disabled:opacity-50"
            >
              {downloading ? "Preparing PDF..." : "Download Resume PDF ↓"}
            </button>
            <button
              onClick={handleGetLatex}
              disabled={latexLoading}
              className="text-sm px-4 py-2 rounded-md border border-black/15 dark:border-white/20 font-medium hover:bg-black/5 dark:hover:bg-white/10 disabled:opacity-50"
            >
              {latexLoading ? "Generating..." : "Get Overleaf Code"}
            </button>
          </div>
          {downloadError && <p className="text-sm text-rose-600 mb-3">{downloadError}</p>}
          {saveError && <p className="text-sm text-rose-600 mb-3">{saveError}</p>}
          {latexError && <p className="text-sm text-rose-600 mb-3">{latexError}</p>}

          <div
            className="rounded-xl border border-black/10 shadow-sm bg-white text-neutral-900 p-8 max-w-3xl mx-auto"
            style={{ fontFamily: "'Times New Roman', Times, Georgia, serif" }}
          >
            <header className="text-center mb-4">
              {editing ? (
                <div className="space-y-1.5 max-w-md mx-auto">
                  <input
                    value={profile?.name ?? ""}
                    onChange={(e) => setProfile((p) => (p ? { ...p, name: e.target.value } : p))}
                    placeholder="Name"
                    className="w-full text-center text-xl font-bold border-b border-neutral-300 focus:outline-none focus:border-neutral-500 bg-transparent"
                  />
                  <div className="flex gap-1.5">
                    <input
                      value={profile?.email ?? ""}
                      onChange={(e) => setProfile((p) => (p ? { ...p, email: e.target.value } : p))}
                      placeholder="Email"
                      className="flex-1 text-center text-xs border-b border-neutral-300 focus:outline-none focus:border-neutral-500 bg-transparent"
                    />
                    <input
                      value={profile?.phone ?? ""}
                      onChange={(e) => setProfile((p) => (p ? { ...p, phone: e.target.value } : p))}
                      placeholder="Phone"
                      className="flex-1 text-center text-xs border-b border-neutral-300 focus:outline-none focus:border-neutral-500 bg-transparent"
                    />
                    <input
                      value={profile?.location ?? ""}
                      onChange={(e) => setProfile((p) => (p ? { ...p, location: e.target.value } : p))}
                      placeholder="Location"
                      className="flex-1 text-center text-xs border-b border-neutral-300 focus:outline-none focus:border-neutral-500 bg-transparent"
                    />
                  </div>
                </div>
              ) : (
                <>
                  <h2 className="text-xl font-bold uppercase tracking-wide">{profile?.name}</h2>
                  <p className="text-xs text-neutral-600 mt-1">
                    {[profile?.location, profile?.email, profile?.phone].filter(Boolean).join(" | ")}
                    {profile?.links.map((l) => (
                      <span key={l.label}>
                        {" | "}
                        <a href={l.url} target="_blank" rel="noopener noreferrer" className="text-blue-700 hover:underline">
                          {l.label}
                        </a>
                      </span>
                    ))}
                  </p>
                </>
              )}
            </header>

            {(editing || draft.summary) && (
              <h3 className="text-sm font-bold border-b border-neutral-800 pb-0.5 mb-1.5">Summary</h3>
            )}
            {editing ? (
              <textarea
                value={draft.summary}
                onChange={(e) => setDraft((d) => (d ? { ...d, summary: e.target.value } : d))}
                placeholder="Professional summary"
                rows={2}
                className="w-full text-sm text-left border border-dashed border-neutral-300 rounded p-2 mb-4 focus:outline-none focus:border-neutral-500"
              />
            ) : (
              draft.summary && <p className="text-sm text-left text-neutral-700 mb-4">{draft.summary}</p>
            )}

            {sections.map((section) => (
              <div key={section.name} className="mb-3">
                <h3 className="text-sm font-bold border-b border-neutral-800 pb-0.5 mb-2">{section.name}</h3>
                <div className="space-y-2.5">
                  {section.bullets.map((b) => (
                    <div key={b.id} className="group relative">
                      {editing ? (
                        <div className="border border-dashed border-neutral-300 rounded p-2 space-y-1">
                          <div className="flex gap-1.5">
                            <input
                              value={b.title}
                              onChange={(e) => updateBullet(b.id, { title: e.target.value })}
                              placeholder="Title"
                              className="flex-1 text-sm font-semibold border-b border-neutral-300 focus:outline-none focus:border-neutral-500"
                            />
                            <input
                              value={b.date_range}
                              onChange={(e) => updateBullet(b.id, { date_range: e.target.value })}
                              placeholder="Date range"
                              className="w-40 text-xs text-right border-b border-neutral-300 focus:outline-none focus:border-neutral-500"
                            />
                            <button
                              onClick={() => removeBullet(b.id)}
                              title="Remove entry"
                              className="text-rose-600 text-xs px-1.5 rounded hover:bg-rose-50"
                            >
                              ✕
                            </button>
                          </div>
                          <textarea
                            value={b.text}
                            onChange={(e) => updateBullet(b.id, { text: e.target.value })}
                            rows={2}
                            className="w-full text-sm border-b border-neutral-300 focus:outline-none focus:border-neutral-500"
                          />
                        </div>
                      ) : (
                        <div>
                          <div className="flex justify-between items-baseline gap-2 flex-wrap">
                            <span className="text-sm font-bold min-w-[40%]">{b.title}</span>
                            <span className="flex items-baseline gap-2.5 flex-wrap justify-end">
                              {b.skills.length > 0 && (
                                <span className="text-xs italic text-neutral-600">{b.skills.join(", ")}</span>
                              )}
                              {b.date_range && (
                                <span className="text-xs text-neutral-500 whitespace-nowrap">{b.date_range}</span>
                              )}
                            </span>
                          </div>
                          {b.source_link && (
                            <div className="text-xs">
                              <a
                                href={b.source_link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-700 hover:underline"
                              >
                                {b.source_link.includes("github.com") ? "GitHub" : "Link"}
                              </a>
                            </div>
                          )}
                          <ul className="list-disc list-inside text-sm text-neutral-800 mt-0.5">
                            <li>{b.text}</li>
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                {editing && (
                  <button
                    onClick={() => addBullet(section.name)}
                    className="mt-1.5 text-xs px-2 py-1 rounded border border-dashed border-neutral-400 text-neutral-600 hover:bg-neutral-50"
                  >
                    + Add entry
                  </button>
                )}
              </div>
            ))}

            {editing && sections.length === 0 && (
              <button
                onClick={() => addBullet("Experience")}
                className="text-xs px-2 py-1 rounded border border-dashed border-neutral-400 text-neutral-600 hover:bg-neutral-50"
              >
                + Add entry
              </button>
            )}

            {skills.length > 0 && (
              <div className="mb-3">
                <h3 className="text-sm font-bold border-b border-neutral-800 pb-0.5 mb-2">Skills</h3>
                <p className="text-sm text-neutral-800">{skills.join(", ")}</p>
              </div>
            )}

            {education.length > 0 && (
              <div className="mb-3">
                <h3 className="text-sm font-bold border-b border-neutral-800 pb-0.5 mb-2">Education</h3>
                {education.map((e, i) => (
                  <p key={i} className="text-sm text-neutral-800">
                    <span className="font-semibold">{e.title}</span>
                    {e.date_range && <> &mdash; {e.date_range}</>}
                    {e.metrics && <>, {e.metrics}</>}
                  </p>
                ))}
              </div>
            )}

            {certifications.length > 0 && (
              <div>
                <h3 className="text-sm font-bold border-b border-neutral-800 pb-0.5 mb-2">Certifications</h3>
                {certifications.map((c, i) => (
                  <p key={i} className="text-sm text-neutral-800">
                    <span className="font-semibold">{c.title}</span>
                    {c.date_range && <> &mdash; {c.date_range}</>}
                  </p>
                ))}
              </div>
            )}
          </div>
        </div>

        <Card className="lg:sticky lg:top-4 flex flex-col max-h-[calc(100vh-2rem)]">
          <h3 className="text-sm font-semibold mb-3">Ask the agent to edit this resume</h3>

          {chatMessages.length > 0 && (
            <div className="flex-1 overflow-y-auto space-y-2 mb-3 pr-1 min-h-[100px]">
              {chatMessages.map((m, i) => (
                <div
                  key={i}
                  className={`text-sm rounded-lg px-3 py-2 ${
                    m.role === "user"
                      ? "bg-black/5 dark:bg-white/10"
                      : m.role === "error"
                      ? "bg-rose-50 dark:bg-rose-900/20 text-rose-700 dark:text-rose-300"
                      : "bg-emerald-50 dark:bg-emerald-900/10 text-emerald-800 dark:text-emerald-300"
                  }`}
                >
                  {m.text}
                </div>
              ))}
            </div>
          )}

          <div className="flex flex-col gap-2">
            <textarea
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendChat();
                }
              }}
              placeholder="Tell the agent what to change..."
              disabled={chatLoading}
              rows={2}
              className="w-full rounded-md border border-black/15 dark:border-white/20 bg-transparent px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-black/20 dark:focus:ring-white/20 disabled:opacity-50"
            />
            <button
              onClick={handleSendChat}
              disabled={chatLoading || !chatInput.trim()}
              className="text-sm px-4 py-2 rounded-md bg-black text-white dark:bg-white dark:text-black font-medium hover:opacity-90 disabled:opacity-50 self-end"
            >
              {chatLoading ? "Thinking..." : "Send"}
            </button>
          </div>
        </Card>
        </div>
      )}

      {showLatexModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setShowLatexModal(false)}
        >
          <div
            className="w-full max-w-2xl rounded-xl bg-white dark:bg-neutral-900 border border-black/10 dark:border-white/10 shadow-xl max-h-[85vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-5 pb-3">
              <h2 className="text-lg font-semibold">LaTeX source for Overleaf</h2>
              <p className="text-xs text-black/50 dark:text-white/50 mt-1">
                Copy this and paste it into a new Overleaf project (create a blank project, replace{" "}
                <code>main.tex</code>&apos;s contents, then Recompile).
              </p>
            </div>
            <textarea
              readOnly
              value={latexCode}
              className="flex-1 mx-5 rounded-md border border-black/15 dark:border-white/20 bg-black/5 dark:bg-white/5 px-3 py-2 text-xs font-mono resize-none focus:outline-none"
              onFocus={(e) => e.target.select()}
            />
            <div className="flex justify-end gap-2 p-5 pt-3">
              <button
                onClick={() => setShowLatexModal(false)}
                className="text-sm px-4 py-2 rounded-md border border-black/15 dark:border-white/20 hover:bg-black/5 dark:hover:bg-white/10"
              >
                Close
              </button>
              <button
                onClick={handleCopyLatex}
                className="text-sm px-4 py-2 rounded-md bg-black text-white dark:bg-white dark:text-black font-medium hover:opacity-90"
              >
                {latexCopied ? "Copied ✓" : "Copy to clipboard"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
