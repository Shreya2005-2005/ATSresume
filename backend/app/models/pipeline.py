from typing import Literal, Optional
from pydantic import BaseModel, Field


class ResumeBullet(BaseModel):
    id: str = Field(description="Stable id for this bullet across draft versions")
    section: str = Field(description="e.g. 'Experience', 'Projects', 'Open Source'")
    title: str = Field(default="", description="Role/project title shown above the bullet")
    date_range: str = Field(default="", description="e.g. '2023-01 to 2025-06'")
    text: str
    evidence_ids: list[str] = Field(default_factory=list, description="Evidence backing this bullet")
    skills: list[str] = Field(default_factory=list, description="Tech stack shown next to the title")
    source_link: Optional[str] = Field(default=None, description="e.g. a GitHub/live-app URL for this entry")


class ResumeDraft(BaseModel):
    version: str
    summary: str = ""
    bullets: list[ResumeBullet]


class RecruiterEvaluation(BaseModel):
    compatibility_score: int = Field(ge=0, le=100)
    missing_keywords: list[str] = Field(default_factory=list, description="Up to 5 most critical missing keywords")
    red_flags: list[str] = Field(default_factory=list, description="Up to 3 red flags a hiring manager notices in 10 seconds")
    weak_bullet_ids: list[str] = Field(default_factory=list, description="Bullet ids that most need rewriting")


class RewrittenBullet(BaseModel):
    bullet_id: str
    original_text: str
    rewritten_text: str
    evidence_ids: list[str] = Field(description="Evidence ids that back every claim in rewritten_text")
    reasoning: str = Field(description="One sentence: what changed and why")


class RewriteResult(BaseModel):
    rewritten_bullets: list[RewrittenBullet]


class ClaimCheck(BaseModel):
    bullet_id: str
    status: Literal["PASSED", "FAILED"]
    reason: str = Field(description="Why it passed or failed, citing evidence ids or the missing support")


class FactCheckResult(BaseModel):
    checks: list[ClaimCheck]

    @property
    def all_passed(self) -> bool:
        return all(c.status == "PASSED" for c in self.checks)

    @property
    def failed(self) -> list[ClaimCheck]:
        return [c for c in self.checks if c.status == "FAILED"]
