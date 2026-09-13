from pydantic import BaseModel, Field


class ReportEntry(BaseModel):
    bullet_id: str
    before: str
    after: str
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)


class ChangeReport(BaseModel):
    run_id: str
    company_name: str
    compatibility_score: int
    ats_score: int
    final_status: str
    gaps: list[str] = Field(description="JD requirements with no adequate evidence")
    red_flags: list[str] = Field(default_factory=list)
    entries: list[ReportEntry] = Field(default_factory=list, description="Every meaningful edit, Stage 4-7")
    needs_human_review_bullets: list[str] = Field(default_factory=list)
