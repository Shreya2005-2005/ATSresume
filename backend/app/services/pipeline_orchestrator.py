"""Orchestrates Stages 4-6: recruiter evaluation -> XYZ rewrite -> fact-check
gate, looping Stage 5 <-> Stage 6 until every claim passes or the iteration
cap is hit (logged for human review, never silently accepted).
"""
from app.core.config import MAX_FACT_CHECK_ITERATIONS
from app.models.jd import ParsedJD
from app.models.matching import EvidenceMatchResult
from app.models.pipeline import RecruiterEvaluation, ResumeBullet, ResumeDraft, RewrittenBullet
from app.services.evidence_store import get_all_evidence
from app.services.fact_check import fact_check_bullets
from app.services.recruiter_eval import evaluate_draft
from app.services.xyz_rewrite import rewrite_bullets


def run_stages_4_to_6(draft_v1: ResumeDraft, jd: ParsedJD, match_result: EvidenceMatchResult) -> dict:
    evaluation = evaluate_draft(draft_v1, jd, match_result)

    weak_ids = set(evaluation.weak_bullet_ids)
    weak_bullets = [b for b in draft_v1.bullets if b.id in weak_ids]
    evidence_pool = get_all_evidence()

    finalized, remaining, iterations_log, needs_human_review = run_rewrite_fact_check_loop(
        weak_bullets, evidence_pool, jd, MAX_FACT_CHECK_ITERATIONS, evaluation.missing_keywords
    )

    final_bullets: list[ResumeBullet] = []
    citation_map: dict[str, list[str]] = {}
    revision_history: list[dict] = []

    for b in draft_v1.bullets:
        if b.id in finalized:
            rb = finalized[b.id]
            final_bullets.append(
                ResumeBullet(
                    id=b.id,
                    section=b.section,
                    title=b.title,
                    date_range=b.date_range,
                    text=rb.rewritten_text,
                    evidence_ids=rb.evidence_ids,
                )
            )
            citation_map[b.id] = rb.evidence_ids
            revision_history.append(
                {
                    "bullet_id": b.id,
                    "before": rb.original_text,
                    "after": rb.rewritten_text,
                    "reason": rb.reasoning,
                    "evidence_ids": rb.evidence_ids,
                }
            )
        elif b.id in remaining:
            # Exhausted retries without a passing claim: keep the original,
            # truthful-by-construction draft_v1 text rather than ship an
            # unverified rewrite.
            final_bullets.append(b)
            citation_map[b.id] = b.evidence_ids
            revision_history.append(
                {
                    "bullet_id": b.id,
                    "before": b.text,
                    "after": b.text,
                    "reason": "Fact-check gate could not verify a rewrite within "
                    f"{MAX_FACT_CHECK_ITERATIONS} attempts; kept original evidence-backed text for human review.",
                    "evidence_ids": b.evidence_ids,
                }
            )
        else:
            final_bullets.append(b)
            citation_map[b.id] = b.evidence_ids

    draft_v2 = ResumeDraft(version="v2", summary=draft_v1.summary, bullets=final_bullets)

    return {
        "evaluation_v1": evaluation.model_dump(),
        "draft_v2": draft_v2,
        "citation_map": citation_map,
        "fact_check_iterations": iterations_log,
        "revision_history": revision_history,
        "needs_human_review_bullet_ids": list(remaining.keys()),
        "final_status": "needs_human_review" if needs_human_review else "verified",
    }


def run_rewrite_fact_check_loop(
    weak_bullets: list[ResumeBullet],
    evidence_pool: list[dict],
    jd: ParsedJD,
    max_iterations: int,
    missing_keywords: list[str] | None = None,
) -> tuple[dict[str, RewrittenBullet], dict[str, ResumeBullet], list[dict], bool]:
    remaining: dict[str, ResumeBullet] = {b.id: b for b in weak_bullets}
    finalized: dict[str, RewrittenBullet] = {}
    feedback: dict[str, str] = {}
    iterations_log: list[dict] = []

    if not weak_bullets:
        return finalized, remaining, iterations_log, False

    for iteration in range(1, max_iterations + 1):
        current_bullets = list(remaining.values())
        rewrite_result = rewrite_bullets(current_bullets, evidence_pool, jd, feedback, missing_keywords)
        by_id = {rb.bullet_id: rb for rb in rewrite_result.rewritten_bullets}

        check_result = fact_check_bullets(rewrite_result.rewritten_bullets)
        checks_by_id = {c.bullet_id: c for c in check_result.checks}

        iterations_log.append(
            {
                "iteration": iteration,
                "rewrites": [rb.model_dump() for rb in rewrite_result.rewritten_bullets],
                "checks": [c.model_dump() for c in check_result.checks],
            }
        )

        new_feedback: dict[str, str] = {}
        for bullet_id, rb in by_id.items():
            check = checks_by_id.get(bullet_id)
            if check and check.status == "PASSED":
                finalized[bullet_id] = rb
                remaining.pop(bullet_id, None)
            else:
                reason = check.reason if check else "No fact-check result returned for this bullet."
                new_feedback[bullet_id] = reason
        feedback = new_feedback

        if not remaining:
            break

    needs_human_review = len(remaining) > 0
    return finalized, remaining, iterations_log, needs_human_review
