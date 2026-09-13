from pydantic import BaseModel, Field


class ParsedJD(BaseModel):
    company_name: str = Field(description="Company name, or 'Unknown' if not stated")
    seniority_level: str = Field(
        description="e.g. Intern, Junior, Mid, Senior, Staff, Lead"
    )
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    key_responsibilities: list[str] = Field(default_factory=list)
