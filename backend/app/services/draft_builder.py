"""Builds the initial resume draft (draft_v1) directly from evidence.

This is a mechanical assembly step, not generation: every bullet is a
1:1 rendering of one evidence unit, so draft_v1 is trivially truthful by
construction. Stage 4 evaluates this draft; Stages 5-6 tailor it.
"""
from app.models.pipeline import ResumeBullet, ResumeDraft
from app.services.evidence_store import get_all_evidence

BULLET_TYPES = {"work_experience", "project", "open_source_pr", "achievement"}
SECTION_NAMES = {
    "work_experience": "Experience",
    "project": "Projects",
    "open_source_pr": "Open Source",
    "achievement": "Achievements",
}


def build_initial_draft() -> ResumeDraft:
    evidence = get_all_evidence()
    bullets = []
    for e in evidence:
        meta = e["metadata"]
        if meta["type"] not in BULLET_TYPES:
            continue
        text = meta["description"]
        if meta.get("metrics"):
            text = f"{text}. {meta['metrics']}."
        skills = [s.strip() for s in meta.get("skills", "").split(",") if s.strip()]
        bullets.append(
            ResumeBullet(
                id=e["evidence_id"],
                section=SECTION_NAMES[meta["type"]],
                title=meta["title"],
                date_range=meta.get("date_range", ""),
                text=text,
                evidence_ids=[e["evidence_id"]],
                skills=skills,
                source_link=meta.get("source_link") or None,
            )
        )
    return ResumeDraft(version="v1", summary="", bullets=bullets)
