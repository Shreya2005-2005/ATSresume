"""Interactive resume editing via plain-language instructions.

Lets the candidate ask for edits ("add more detail about X", "remove this
bullet", "shorten the summary") without bypassing the pipeline's core
guardrail: any claim added or expanded must still trace back to real
evidence. Removals, reordering, and rephrasing carry no fabrication risk
and are always honored; every bullet whose text changed is re-run through
the same fact-check gate Stage 6 uses before the edit is accepted.
"""
import logging

from pydantic import BaseModel, Field

from app.core.config import GROQ_MODEL_HEAVY
from app.models.pipeline import ResumeDraft, RewrittenBullet
from app.services.evidence_store import get_all_evidence
from app.services.fact_check import fact_check_bullets
from app.services.llm_client import LLMJSONError, call_gemini_json, call_llm_json


class ChatEditResult(BaseModel):
    draft: ResumeDraft
    explanation: str = Field(
        description="One or two sentences: what changed and why, or why a request couldn't be honestly fulfilled"
    )


SYSTEM_PROMPT = """You are editing a candidate's resume in response to their direct instruction, \
as part of a pipeline whose strict rule is: never invent a skill, project, credential, \
employment, metric, or achievement that isn't in the CANDIDATE EVIDENCE POOL below.

You may freely REMOVE, REORDER, SHORTEN, or REPHRASE existing bullets/summary when asked \
-- that carries no fabrication risk. You may ADD detail to a bullet or add a new bullet \
ONLY by pulling in real facts that are already in the evidence pool but not yet reflected \
in the resume (e.g. a metric or skill from the cited evidence that was left out). If the \
user's instruction would require inventing something not present in the evidence pool \
(a metric that doesn't exist, a skill never demonstrated, more depth than the evidence \
supports), do NOT invent it -- make the best honest change you can instead and say so \
plainly in your explanation.

IMPORTANT -- you only control the resume's CONTENT (the JSON fields below). You have NO \
control over its visual formatting: fonts, colors, margins, spacing, alignment, page breaks, \
and bullet styling are all fixed by the resume template's CSS and are NOT part of this JSON. \
A `text` field is always rendered as ONE continuous line -- inserting "\\n" or splitting a \
bullet into multiple sentences on separate lines has NO visual effect and is FORBIDDEN; never \
put a literal newline character inside any `text` or `summary` value.

If the user's instruction is actually about visual formatting/layout/spacing/appearance \
("fix the formatting", "make it look cleaner", "align this better", "less cramped", "too much \
whitespace") rather than about what the text says, you MUST leave every bullet's `text` and \
the `summary` byte-for-byte IDENTICAL to the input -- do not reword, split, re-punctuate, or \
"clean up" anything, and do not touch JSON key order or spacing either (that's invisible to \
the user and not a real fix). Say plainly in your explanation that layout/styling isn't \
something this chat can change, and point them to the "Edit resume" button (to shorten, \
reorder, or remove entries) if they want a more compact or spacious look. \
NEVER say things like "reformatted the JSON" or "made it more compact" when nothing the user \
can actually see has changed -- that is a dishonest answer.

The only exception: if shortening or removing content would *genuinely* reduce visual density \
(e.g. the user explicitly also asks to shorten, or a bullet is extremely long), you may make \
that content-level edit -- but describe it honestly as shortening/removing text, never as a \
"formatting" fix.

Every bullet keeps its original `id` unless it's a brand-new bullet, in which case give it \
a new id starting with "chat_". Every bullet's evidence_ids must list the real evidence ids \
that support it -- a bullet with no evidence_ids will be rejected.

Respond with a JSON object: draft (object with version, summary, bullets -- each bullet has \
id, section, title, date_range, text, evidence_ids, skills, source_link), explanation (one \
or two sentences: what you changed and why, or why you couldn't fully honor the request and \
what you did instead)."""


_FORMATTING_KEYWORDS = (
    "format", "formatting", "layout", "spacing", "space", "margin", "align",
    "alignment", "font", "style", "styling", "look", "clean", "compact",
    "crowded", "cramped", "cluttered", "page", "design", "visual",
)

_FORMATTING_NOTE = (
    "Layout, spacing, fonts, and margins come from the resume's fixed template design, "
    "not from this chat -- so there's nothing here for me to change. If you want a more "
    "compact or spacious look, use the \"Edit resume\" button to shorten, reorder, or "
    "remove entries; the PDF export also auto-shrinks to fit one page."
)


def apply_chat_edit(draft: ResumeDraft, instruction: str) -> tuple[ResumeDraft, str, list[str]]:
    """Returns (new_draft, explanation, rejected_bullet_ids). Rejected bullets
    are reverted to their pre-edit text (or dropped, if brand new) because
    they failed the fact-check gate -- the edit is never silently trusted
    just because the LLM attached evidence_ids to it."""
    evidence_pool = get_all_evidence()
    pool_block = "\n".join(f"[{e['evidence_id']}] {e['document'][:300]}" for e in evidence_pool)
    draft_block = draft.model_dump_json(indent=2)

    user_prompt = (
        f"CANDIDATE EVIDENCE POOL (the only source of new facts you may draw from):\n{pool_block}\n\n"
        f"Current resume draft:\n{draft_block}\n\n"
        f"User's instruction: {instruction}"
    )

    try:
        result = call_gemini_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema_model=ChatEditResult,
            temperature=0.3,
            max_tokens=4096,
        )
    except LLMJSONError as e:
        logging.warning("Gemini chat-edit call failed, falling back to Groq: %s", e)
        result = call_llm_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema_model=ChatEditResult,
            model=GROQ_MODEL_HEAVY,
            temperature=0.3,
            max_tokens=4096,
        )

    new_draft = result.draft
    # The resume renderer treats `text` as a single line; a literal newline
    # has no visual effect and would just be dead whitespace in the output,
    # so strip any the model inserts (it sometimes tries this as a fake
    # "formatting fix" despite being told not to).
    new_draft = new_draft.model_copy(
        update={
            "summary": " ".join(new_draft.summary.split()),
            "bullets": [
                b.model_copy(update={"text": " ".join(b.text.split())}) for b in new_draft.bullets
            ],
        }
    )
    original_by_id = {b.id: b for b in draft.bullets}

    def _norm(s: str) -> str:
        return " ".join(s.split())

    changed = [
        b
        for b in new_draft.bullets
        if b.id not in original_by_id or _norm(original_by_id[b.id].text) != _norm(b.text)
    ]
    summary_changed = _norm(new_draft.summary) != _norm(draft.summary)
    if not changed and not summary_changed:
        lowered = instruction.lower()
        if any(kw in lowered for kw in _FORMATTING_KEYWORDS):
            return new_draft, _FORMATTING_NOTE, []
        return new_draft, result.explanation, []

    checkable = [
        RewrittenBullet(
            bullet_id=b.id,
            original_text=original_by_id[b.id].text if b.id in original_by_id else "",
            rewritten_text=b.text,
            evidence_ids=b.evidence_ids,
            reasoning=result.explanation,
        )
        for b in changed
    ]
    checks = {c.bullet_id: c for c in fact_check_bullets(checkable).checks}

    rejected_ids: list[str] = []
    final_bullets = []
    for b in new_draft.bullets:
        check = checks.get(b.id)
        if check and check.status == "FAILED":
            rejected_ids.append(b.id)
            if b.id in original_by_id:
                final_bullets.append(original_by_id[b.id])
            continue  # a brand-new bullet that fails fact-check is dropped
        final_bullets.append(b)

    new_draft = new_draft.model_copy(update={"bullets": final_bullets})

    explanation = result.explanation
    if rejected_ids:
        explanation += (
            f" (Note: {len(rejected_ids)} proposed change(s) couldn't be verified against your "
            "evidence and were not applied.)"
        )

    return new_draft, explanation, rejected_ids
