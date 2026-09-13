from pydantic import BaseModel, Field


class RequirementMatch(BaseModel):
    requirement: str
    requirement_kind: str = Field(description="'required_skill' or 'responsibility'")
    matched_evidence_ids: list[str] = Field(
        default_factory=list, description="Evidence retrieved as topically relevant, whether or not it's adequate"
    )
    confidence_score: float = Field(description="Adequacy score, 0-1 (not raw cosine similarity)")
    is_gap: bool = Field(description="True if the retrieved evidence does not adequately substantiate the requirement")
    rationale: str = Field(default="", description="Why this evidence does/doesn't substantiate the requirement")


class EvidenceMatchResult(BaseModel):
    matches: list[RequirementMatch]
    gaps: list[str] = Field(description="Requirements with no adequate evidence")


class AdequacyJudgment(BaseModel):
    is_adequate: bool
    adequacy_score: float = Field(description="0.0-1.0, strict about specifics like years/employment/production scope")
    rationale: str


class SingleAdequacyJudgment(AdequacyJudgment):
    requirement: str = Field(description="Echo back the exact requirement text this judgment is for")


class BatchAdequacyJudgment(BaseModel):
    judgments: list[SingleAdequacyJudgment]
