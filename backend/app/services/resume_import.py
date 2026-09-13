"""Extracts candidate evidence units from an uploaded resume file.

This is an extraction step, not a generation step: the LLM is instructed to
pull out only what is explicitly stated in the resume text. Extracted items
are returned for human review (same as the manual Add Work form) — they are
never written straight into the Evidence Store, since an extraction mistake
here would otherwise silently become a "fact" the rest of the pipeline is
allowed to cite.
"""
import io

from pypdf import PdfReader

from app.core.config import GROQ_MODEL_HEAVY
from app.models.evidence import ExtractedEvidenceResult
from app.services.llm_client import call_llm_json

SYSTEM_PROMPT = """You extract structured evidence units from a candidate's resume \
text for a resume-tailoring pipeline whose strict rule is: never invent anything \
not explicitly stated in the source text.

For each distinct work experience entry, project, open-source contribution, \
education entry, certification, or notable achievement/award mentioned in the \
resume, produce one item with:
- type: one of "work_experience", "project", "open_source_pr", "education", \
"certification", "skill_note", "achievement"
- title: short label (role + company, project name, degree, award name, etc.) \
taken directly from the text
- description: the factual claim(s)/responsibilities/what-they-did, taken \
directly from the text
- metrics: a quantified outcome ONLY if one is explicitly stated (e.g. "reduced \
latency by 40%"); otherwise omit it
- skills: technologies/skills explicitly associated with this entry
- source_link: a URL ONLY if one is explicitly present in the text for this \
entry; otherwise omit it
- date_range: the date range or date exactly as stated; otherwise omit it

Do NOT invent, estimate, or infer any metric, date, skill, or link that is not \
explicitly present in the source text. If unsure, omit the field rather than \
guess. Do not merge unrelated experiences into one item.

Respond with a single JSON object: {"items": [...]}."""


def extract_text_from_upload(filename: str, content: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if lower.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")
    raise ValueError("Unsupported file type. Please upload a PDF or .txt file.")


def extract_evidence_from_resume(text: str) -> ExtractedEvidenceResult:
    text = text.strip()
    if not text:
        raise ValueError("Could not read any text from this file.")
    user_prompt = f"Resume text:\n\n{text[:12000]}"
    return call_llm_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema_model=ExtractedEvidenceResult,
        model=GROQ_MODEL_HEAVY,
        temperature=0.1,
        max_tokens=6000,
    )
