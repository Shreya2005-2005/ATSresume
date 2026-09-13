"""Stage 4 — Draft Generation / Evaluation (Recruiter Test persona).

A lead-recruiter persona scores the current draft against the JD, using
only the draft text and the Stage 3 evidence-match results (never
inventing missing keywords outside what the JD actually asked for).
"""
from app.core.config import GROQ_MODEL_HEAVY
from app.models.jd import ParsedJD
from app.models.matching import EvidenceMatchResult
from app.models.pipeline import RecruiterEvaluation, ResumeDraft
from app.services.llm_client import call_llm_json

SYSTEM_PROMPT = """You are a lead recruiter at {company_name} reviewing this \
candidate's resume against the job description below. Be honest and critical, \
the way a real recruiter skimming resumes would be.

Score compatibility 0-100. List up to 5 of the most critical missing keywords — \
these MUST come from the job's required skills or the confirmed gaps you are \
given; do not invent keywords that are not part of the job requirements. List up \
to 3 red flags a hiring manager would notice in the first 10 seconds (e.g. vague \
bullets with no outcome, no quantification, unclear scope, unexplained gaps). \
Identify which bullet ids (by the ids given) are weakest and most need rewriting \
to better match the job — prioritize bullets that touch a required skill or \
responsibility, especially ones tied to a confirmed gap, since those need the \
most careful, honest treatment.

Respond with a JSON object: compatibility_score (int 0-100), missing_keywords \
(array of strings, max 5), red_flags (array of strings, max 3), weak_bullet_ids \
(array of bullet id strings)."""


def evaluate_draft(
    draft: ResumeDraft, jd: ParsedJD, match_result: EvidenceMatchResult
) -> RecruiterEvaluation:
    bullets_block = "\n".join(f"[{b.id}] {b.text}" for b in draft.bullets)
    gaps_block = "\n".join(f"- {g}" for g in match_result.gaps) or "(none)"

    user_prompt = (
        f"Job required skills: {', '.join(jd.required_skills)}\n"
        f"Job key responsibilities: {', '.join(jd.key_responsibilities)}\n\n"
        f"Confirmed gaps (no adequate supporting evidence exists for these):\n{gaps_block}\n\n"
        f"Current resume draft bullets:\n{bullets_block}"
    )

    return call_llm_json(
        system_prompt=SYSTEM_PROMPT.format(company_name=jd.company_name),
        user_prompt=user_prompt,
        schema_model=RecruiterEvaluation,
        model=GROQ_MODEL_HEAVY,
        temperature=0.3,
    )
