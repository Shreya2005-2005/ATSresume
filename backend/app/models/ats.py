from pydantic import BaseModel, Field


class MicroRewrite(BaseModel):
    bullet_id: str
    original_text: str
    rewritten_text: str
    reason: str


class ATSResult(BaseModel):
    ats_score: int = Field(ge=0, le=100)
    flagged_sections: list[str] = Field(
        default_factory=list, description="Sections/issues that would get skipped or mis-parsed"
    )
    keyword_density_notes: list[str] = Field(default_factory=list)
    micro_rewrites: list[MicroRewrite] = Field(default_factory=list)
