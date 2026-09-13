from typing import Literal, Optional
from pydantic import BaseModel, Field

EvidenceType = Literal[
    "work_experience",
    "project",
    "open_source_pr",
    "education",
    "certification",
    "skill_note",
    "achievement",
]


class EvidenceUnit(BaseModel):
    """One atomic, real, sourced fact about the candidate.

    This is the ONLY unit of truth the agent pipeline may cite. Every
    claim in a generated resume must trace back to an evidence_id.
    """

    id: str
    type: EvidenceType
    title: str = Field(description="Short label, e.g. role or project name")
    description: str = Field(description="The factual bullet/claim text")
    metrics: Optional[str] = Field(
        default=None, description="Real quantified outcome, if one exists"
    )
    skills: list[str] = Field(default_factory=list)
    source_link: Optional[str] = Field(
        default=None, description="URL or file reference backing this claim"
    )
    date_range: Optional[str] = None

    def to_document(self) -> str:
        parts = [self.title, self.description]
        if self.metrics:
            parts.append(f"Metric: {self.metrics}")
        if self.skills:
            parts.append("Skills: " + ", ".join(self.skills))
        return ". ".join(parts)

    def to_metadata(self) -> dict:
        return {
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "metrics": self.metrics or "",
            "skills": ", ".join(self.skills),
            "source_link": self.source_link or "",
            "date_range": self.date_range or "",
            "has_metric": bool(self.metrics),
        }


class ExtractedEvidenceItem(BaseModel):
    """One evidence unit as pulled from an uploaded resume — unverified until
    a human reviews and confirms it, same as anything typed into the manual
    Add Work form."""

    type: EvidenceType
    title: str
    description: str
    metrics: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    source_link: Optional[str] = None
    date_range: Optional[str] = None


class ExtractedEvidenceResult(BaseModel):
    items: list[ExtractedEvidenceItem] = Field(default_factory=list)
