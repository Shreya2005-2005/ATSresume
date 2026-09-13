"""Stage 7 — ATS Filter Pass.

Persona: a strict ATS parser plus a tired hiring manager skimming 200
resumes. Scans the fact-checked draft for parsing/formatting risk and
keyword coverage, and proposes micro-rewrites for sections that would get
scrolled past. Micro-rewrites may only rephrase for clarity/keyword
placement — they must never add a claim, metric, or skill that wasn't
already in the fact-checked bullet, since nothing after Stage 6 is
re-verified against the Evidence Store.
"""
from app.core.config import GROQ_MODEL_LIGHT
from app.models.ats import ATSResult
from app.models.jd import ParsedJD
from app.models.pipeline import ResumeDraft, RewrittenBullet
from app.services.fact_check import fact_check_bullets
from app.services.llm_client import call_llm_json

SYSTEM_PROMPT = """You are simultaneously a strict ATS (Applicant Tracking System) \
parser and a tired hiring manager skimming 200 resumes for this role. Evaluate the \
resume draft below in JSON form.

Check for: sections/bullets that would be skipped or mis-parsed by an ATS (dense \
paragraphs instead of bullets, missing section structure, walls of text); keyword \
coverage against the job's required skills (are they present verbatim or as close \
synonyms somewhere in the resume?); overall scannability (would a tired human \
notice the relevant experience in the first 10 seconds?).

You may propose micro-rewrites for bullets that would get scrolled past — but a \
micro-rewrite may ONLY rephrase for clarity, structure, or keyword placement. It \
must NEVER add a claim, metric, skill, or achievement that is not already present \
in the original bullet text. If a bullet is weak because the underlying evidence \
is weak, that is not something this pass can fix — leave it and note it in \
flagged_sections instead.

Respond with a JSON object: ats_score (int 0-100), flagged_sections (array of \
strings describing specific sections/issues), keyword_density_notes (array of \
strings, e.g. "Kubernetes appears 1 time despite being a required skill"), \
micro_rewrites (array of objects: bullet_id, original_text, rewritten_text, \
reason)."""


def run_ats_filter(draft: ResumeDraft, jd: ParsedJD) -> ATSResult:
    bullets_block = "\n".join(f"[{b.id}] ({b.section}) {b.text}" for b in draft.bullets)
    user_prompt = (
        f"Job required skills: {', '.join(jd.required_skills)}\n"
        f"Job nice-to-have skills: {', '.join(jd.nice_to_have_skills)}\n\n"
        f"Resume draft:\n{bullets_block}"
    )
    result = call_llm_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema_model=ATSResult,
        model=GROQ_MODEL_LIGHT,
        temperature=0.2,
    )
    return _verify_micro_rewrites(result, draft)


def _verify_micro_rewrites(result: ATSResult, draft: ResumeDraft) -> ATSResult:
    """Re-run every micro-rewrite through the real fact-check gate against the
    original bullet's evidence. A formatting pass gets no exemption from the
    'never invent a claim' rule just because it's only supposed to rephrase."""
    evidence_by_bullet = {b.id: b.evidence_ids for b in draft.bullets}
    candidates = [
        (mr, evidence_by_bullet.get(mr.bullet_id, []))
        for mr in result.micro_rewrites
    ]
    if not candidates:
        return result

    checkable = [
        RewrittenBullet(
            bullet_id=mr.bullet_id,
            original_text=mr.original_text,
            rewritten_text=mr.rewritten_text,
            evidence_ids=evidence_ids,
            reasoning=mr.reason,
        )
        for mr, evidence_ids in candidates
    ]
    checks = {c.bullet_id: c for c in fact_check_bullets(checkable).checks}

    kept = []
    for mr in result.micro_rewrites:
        check = checks.get(mr.bullet_id)
        if check and check.status == "FAILED":
            result.flagged_sections.append(
                f"[{mr.bullet_id}] proposed micro-rewrite rejected by fact-check gate: {check.reason}"
            )
            continue
        kept.append(mr)
    result.micro_rewrites = kept
    return result
