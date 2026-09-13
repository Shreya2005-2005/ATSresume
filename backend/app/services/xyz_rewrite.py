"""Stage 5 — Targeted XYZ Rewrite.

Rewrites weak bullets using the Google XYZ framework ("Achieved X, measured
by Y, by doing Z"). This stage runs in two modes:

- FIRST PASS (no fact-check feedback yet): optimizes purely for
  competitiveness against the JD, the way an eager resume writer would —
  drawing on the evidence pool but free to frame adjacent evidence in the
  job posting's own terms. This is deliberately NOT constrained by the
  anti-fabrication rule; verification is Stage 6's job, not Stage 5's.
- RETRY PASS (a previous attempt failed fact-check): switches to the
  strict hard rule — every claim must trace to real evidence, with actual
  fact-check failure reasons fed back so the correction is targeted.

This split is what makes the fact-check gate a real, load-bearing
guardrail rather than a formality: Stage 5 is allowed to overreach on the
first attempt, and Stage 6 is the actual boundary nothing false can cross.
"""
from app.core.config import GROQ_MODEL_HEAVY
from app.models.jd import ParsedJD
from app.models.pipeline import ResumeBullet, RewriteResult
from app.services.llm_client import call_llm_json

FIRST_PASS_SYSTEM_PROMPT = """You are a lead recruiter at {company_name}, ghost-writing \
the most competitive possible resume bullets to help this candidate win the role, \
using the Google XYZ framework: "Achieved X, measured by Y, by doing Z".

Your only goal on this pass is to make each bullet as aligned with the job \
description as possible. Draw on the CANDIDATE EVIDENCE POOL below for the \
underlying facts, but prioritize making a strong impression over hedging: if a \
piece of evidence is adjacent to what the job wants (related technology, a \
personal or open-source project rather than employment, a smaller scale than \
what's being asked for), feel free to frame it using the job posting's own \
language and terms rather than qualifying it. Reach for the job's required \
skills and responsibilities directly in your phrasing wherever the evidence gives \
you any opening to do so. Don't worry about being over-cautious here — write the \
version of this bullet that would score highest with an ATS and a recruiter \
skimming for keyword matches.

{missing_keywords_block}

Respond with a JSON object: rewritten_bullets, an array where each item has: \
bullet_id (string), original_text (string, copy of the original), rewritten_text \
(string, the new XYZ-style bullet), evidence_ids (array of evidence id strings \
from the pool that relate to this bullet), reasoning (one sentence: what changed \
and why)."""

RETRY_SYSTEM_PROMPT = """You are a lead recruiter at {company_name}, correcting resume \
bullets that failed fact-checking, using the Google XYZ framework: "Achieved X, \
measured by Y, by doing Z".

HARD RULE — this is non-negotiable: every fact in X, Y, and Z (skills, metrics, \
scope, duration, employment type, production vs. personal/open-source status) \
MUST be directly traceable to one of the evidence units in the CANDIDATE EVIDENCE \
POOL below. You may ONLY cite evidence_ids that are in that pool. Never invent a \
skill, project, metric, employment period, or achievement that isn't backed by \
that evidence. If no real metric (Y) exists for a bullet, do not invent one — \
either omit the metric and use honest qualitative phrasing, or state the honest, \
real, possibly weaker claim (e.g. "contributed 45+ merged pull requests to an \
open-source Kubernetes CLI tool" instead of implying production Kubernetes \
employment experience that doesn't exist). Each bullet below failed fact-check \
for a specific stated reason — fix exactly that problem.

Respond with a JSON object: rewritten_bullets, an array where each item has: \
bullet_id (string), original_text (string, copy of the original), rewritten_text \
(string, the new XYZ-style bullet), evidence_ids (array of evidence id strings \
from the pool that back every claim in rewritten_text), reasoning (one sentence: \
what changed and why)."""


def rewrite_bullets(
    weak_bullets: list[ResumeBullet],
    evidence_pool: list[dict],
    jd: ParsedJD,
    feedback: dict[str, str] | None = None,
    missing_keywords: list[str] | None = None,
) -> RewriteResult:
    feedback = feedback or {}
    is_retry = bool(feedback)
    pool_block = "\n".join(f"[{e['evidence_id']}] {e['document'][:300]}" for e in evidence_pool)

    bullets_block_parts = []
    for b in weak_bullets:
        part = f"[{b.id}] {b.text}"
        if b.id in feedback:
            part += (
                f"\n  PREVIOUS ATTEMPT FAILED FACT-CHECK: {feedback[b.id]}\n"
                f"  Rewrite this honestly without the unsupported claim, or replace "
                f"it with a real, weaker-but-true claim instead."
            )
        bullets_block_parts.append(part)
    bullets_block = "\n".join(bullets_block_parts)

    user_prompt = (
        f"Job required skills: {', '.join(jd.required_skills)}\n"
        f"Job key responsibilities: {', '.join(jd.key_responsibilities)}\n\n"
        f"CANDIDATE EVIDENCE POOL (the only source you may cite):\n{pool_block}\n\n"
        f"Weak bullets to rewrite:\n{bullets_block}"
    )

    if is_retry:
        system_prompt = RETRY_SYSTEM_PROMPT.format(company_name=jd.company_name)
    else:
        if missing_keywords:
            missing_keywords_block = (
                "The recruiter scoring this resume flagged these as the top keywords "
                f"missing relative to the job: {', '.join(missing_keywords)}. Work as many "
                "of these in as you can, using their exact wording, wherever a bullet's "
                "evidence gives you any plausible opening — even a loose or indirect "
                "connection is worth taking."
            )
        else:
            missing_keywords_block = ""
        system_prompt = FIRST_PASS_SYSTEM_PROMPT.format(
            company_name=jd.company_name, missing_keywords_block=missing_keywords_block
        )

    return call_llm_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        schema_model=RewriteResult,
        model=GROQ_MODEL_HEAVY,
        temperature=0.2 if is_retry else 0.6,
    )
