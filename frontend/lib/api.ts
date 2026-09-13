export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export interface ParsedJD {
  company_name: string;
  seniority_level: string;
  required_skills: string[];
  nice_to_have_skills: string[];
  key_responsibilities: string[];
}

export interface CompanyContext {
  company_name: string;
  facts: string[];
  source: "tavily" | "fallback_kb" | "generic_fallback";
}

export interface RequirementMatch {
  requirement: string;
  requirement_kind: string;
  matched_evidence_ids: string[];
  confidence_score: number;
  is_gap: boolean;
  rationale: string;
}

export interface EvidenceMatchResult {
  matches: RequirementMatch[];
  gaps: string[];
}

export interface ResumeBullet {
  id: string;
  section: string;
  title: string;
  date_range: string;
  text: string;
  evidence_ids: string[];
  skills: string[];
  source_link: string | null;
}

export interface ResumeDraft {
  version: string;
  summary: string;
  bullets: ResumeBullet[];
}

export interface RecruiterEvaluation {
  compatibility_score: number;
  missing_keywords: string[];
  red_flags: string[];
  weak_bullet_ids: string[];
}

export interface MicroRewrite {
  bullet_id: string;
  original_text: string;
  rewritten_text: string;
  reason: string;
}

export interface ATSResult {
  ats_score: number;
  flagged_sections: string[];
  keyword_density_notes: string[];
  micro_rewrites: MicroRewrite[];
}

export interface RevisionEntry {
  bullet_id: string;
  before: string;
  after: string;
  reason: string;
  evidence_ids: string[];
}

export type EvidenceType =
  | "work_experience"
  | "project"
  | "open_source_pr"
  | "education"
  | "certification"
  | "skill_note"
  | "achievement";

export interface EvidenceItem {
  evidence_id: string;
  document: string;
  metadata: {
    type: string;
    title: string;
    description: string;
    metrics: string;
    skills: string;
    source_link: string;
    date_range: string;
    has_metric: boolean;
  };
}

export interface CreateEvidenceInput {
  type: EvidenceType;
  title: string;
  description: string;
  metrics?: string;
  skills: string[];
  source_link?: string;
  date_range?: string;
}

export interface ExtractedEvidenceItem {
  type: EvidenceType;
  title: string;
  description: string;
  metrics: string | null;
  skills: string[];
  source_link: string | null;
  date_range: string | null;
}

export interface ProfileLink {
  label: string;
  url: string;
}

export interface Profile {
  name: string;
  email: string;
  phone: string;
  location: string;
  links: ProfileLink[];
}

export interface RunSummary {
  run_id: string;
  company_name: string | null;
  final_status: string | null;
  updated_at: number;
}

export interface RunState {
  run_id: string;
  jd_requirements: ParsedJD | Record<string, never>;
  company_context: CompanyContext | Record<string, never>;
  evidence_matches: EvidenceMatchResult | Record<string, never>;
  draft_versions: { v1: ResumeDraft | null; v2: ResumeDraft | null; final: ResumeDraft | null };
  evaluation_v1: RecruiterEvaluation | Record<string, never>;
  citation_map: Record<string, string[]>;
  fact_check_results: { iteration: number; passed: string[]; failed: string[] };
  fact_check_iterations: unknown[];
  ats_result: ATSResult | Record<string, never>;
  revision_history: RevisionEntry[];
  final_status: "in_progress" | "verified" | "needs_human_review" | "error";
}

export interface TraceEvent {
  type: string;
  message: string;
  [key: string]: unknown;
}

export async function fetchRuns(): Promise<RunSummary[]> {
  const res = await fetch(`${API_BASE}/runs`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load run history (${res.status})`);
  return res.json();
}

export async function renameRun(runId: string, label: string) {
  const res = await fetch(`${API_BASE}/runs/${runId}/label`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label }),
  });
  if (!res.ok) throw new Error(`Failed to rename run (${res.status})`);
  return res.json();
}

export function resumePdfUrl(runId: string): string {
  return `${API_BASE}/runs/${runId}/resume.pdf`;
}

export async function fetchState(runId: string): Promise<RunState> {
  const res = await fetch(`${API_BASE}/runs/${runId}/state`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load run state (${res.status})`);
  return res.json();
}

/** Persists edits to this run's final draft so they survive navigation/reload. */
export async function saveDraft(runId: string, draft: ResumeDraft): Promise<ResumeDraft> {
  const res = await fetch(`${API_BASE}/runs/${runId}/draft`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(draft),
  });
  if (!res.ok) throw new Error(`Failed to save resume changes (${res.status})`);
  return res.json();
}

export interface ChatEditResponse {
  draft: ResumeDraft;
  explanation: string;
  rejected_bullet_ids: string[];
}

/** Applies a plain-language editing instruction to the draft. The agent may
 * add real detail pulled from evidence, remove/reorder/rephrase freely, but
 * can't invent facts -- any change that fails fact-check is reverted
 * server-side and reflected in rejected_bullet_ids. */
export async function chatEditDraft(
  runId: string,
  instruction: string,
  draft: ResumeDraft
): Promise<ChatEditResponse> {
  const res = await fetch(`${API_BASE}/runs/${runId}/chat-edit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ instruction, draft }),
  });
  if (!res.ok) throw new Error(`Failed to apply edit (${res.status})`);
  return res.json();
}

/** Persists edits to the candidate profile (name/contact/links). */
export async function saveProfile(profile: Profile): Promise<Profile> {
  const res = await fetch(`${API_BASE}/profile`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  if (!res.ok) throw new Error(`Failed to save profile changes (${res.status})`);
  return res.json();
}

export async function fetchEvidenceList(): Promise<EvidenceItem[]> {
  const res = await fetch(`${API_BASE}/evidence`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load evidence (${res.status})`);
  return res.json();
}

export async function createEvidence(input: CreateEvidenceInput) {
  const res = await fetch(`${API_BASE}/evidence`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`Failed to add evidence (${res.status})`);
  return res.json();
}

export async function deleteEvidence(evidenceId: string) {
  const res = await fetch(`${API_BASE}/evidence/${evidenceId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete evidence (${res.status})`);
  return res.json();
}

/** Uploads a resume file and returns extracted evidence items for review —
 * nothing is saved to the Evidence Store until the user confirms each item. */
export async function extractResumeEvidence(file: File): Promise<{ items: ExtractedEvidenceItem[] }> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/evidence/extract-from-resume`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || `Failed to extract resume (${res.status})`);
  }
  return res.json();
}

export async function fetchSampleJD(): Promise<string> {
  const res = await fetch(`${API_BASE}/sample-jd`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load sample JD (${res.status})`);
  return res.text();
}

export async function fetchReportMarkdown(runId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/runs/${runId}/report.md`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load report (${res.status})`);
  return res.text();
}

export async function fetchProfile(): Promise<Profile> {
  const res = await fetch(`${API_BASE}/profile`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load profile (${res.status})`);
  return res.json();
}

/** Renders the given (possibly user-edited) draft to PDF and returns the bytes. */
export async function renderResumePdf(draft: ResumeDraft, runId: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/pdf/render`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft, run_id: runId }),
  });
  if (!res.ok) throw new Error(`Failed to render resume PDF (${res.status})`);
  return res.blob();
}

/** Returns standalone LaTeX source for the given draft, ready to paste into Overleaf. */
export async function fetchLatexResume(draft: ResumeDraft): Promise<string> {
  const res = await fetch(`${API_BASE}/pdf/latex`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft }),
  });
  if (!res.ok) throw new Error(`Failed to generate LaTeX (${res.status})`);
  const data = await res.json();
  return data.latex;
}

/** Streams the run pipeline via SSE (POST-based, so we parse the stream by hand). */
export async function streamRun(
  rawJd: string,
  onEvent: (event: TraceEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_BASE}/runs/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_jd: rawJd }),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`Failed to start run (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const line = chunk.trim();
      if (!line.startsWith("data:")) continue;
      const jsonStr = line.slice("data:".length).trim();
      if (!jsonStr) continue;
      try {
        onEvent(JSON.parse(jsonStr) as TraceEvent);
      } catch {
        // ignore malformed chunk
      }
    }
  }
}
