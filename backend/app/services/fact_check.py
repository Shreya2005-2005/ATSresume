"""Stage 6 — Fact-Check Gate.

The critical guardrail: independently verifies every rewritten claim
against the ACTUAL text of its cited evidence — never trusts that a
citation is valid just because the rewrite step attached an evidence_id.
A bullet fails if it claims anything (metric, scope, duration, employment
type, production status) beyond what the cited evidence actually says.
"""
from app.core.config import GROQ_MODEL_LIGHT
from app.models.pipeline import ClaimCheck, FactCheckResult, RewrittenBullet
from app.services.evidence_store import get_by_ids
from app.services.llm_client import call_llm_json

SYSTEM_PROMPT = """You are a strict fact-checker for a resume-tailoring pipeline. \
For each resume bullet, you are given the rewritten bullet text, the evidence_ids \
the writer claims support it, and the ACTUAL text of that cited evidence.

Determine whether EVERY factual claim in the bullet is directly and specifically \
supported by the cited evidence text — skills, metrics, numbers, duration, scope, \
employment type, and production-vs-personal/open-source status all count. Do not \
give credit for claims that are merely plausible or in the same topic area; they \
must be actually stated or clearly and directly implied by the cited evidence.

Common failure patterns to catch: a metric that doesn't appear in the evidence; \
years of experience beyond what evidence supports; open-source or personal-project \
work reframed as production employment experience; scope/scale inflated beyond \
what evidence states; a skill attributed to the wrong context.

If a bullet cites NO evidence_ids, or cites evidence that doesn't actually contain \
the claim, mark it FAILED with a precise reason naming the unsupported part. \
Otherwise mark it PASSED.

Respond with a JSON object: checks, an array where each item has: bullet_id \
(string), status ("PASSED" or "FAILED"), reason (one concise sentence)."""


def fact_check_bullets(rewritten: list[RewrittenBullet]) -> FactCheckResult:
    if not rewritten:
        return FactCheckResult(checks=[])

    blocks = []
    for b in rewritten:
        cited = get_by_ids(b.evidence_ids)
        if cited:
            evidence_block = "\n".join(f"  [{e['evidence_id']}] {e['document']}" for e in cited)
        else:
            evidence_block = "  (no valid evidence_ids were cited)"
        blocks.append(
            f"Bullet [{b.bullet_id}]\n"
            f"Rewritten text: {b.rewritten_text}\n"
            f"Cited evidence:\n{evidence_block}"
        )
    user_prompt = "\n\n".join(blocks)

    return call_llm_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema_model=FactCheckResult,
        model=GROQ_MODEL_LIGHT,
        temperature=0.0,
    )
