from typing import Literal
from pydantic import BaseModel, Field


class CompanyContext(BaseModel):
    company_name: str
    facts: list[str] = Field(default_factory=list)
    source: Literal["tavily", "fallback_kb", "generic_fallback"]


class DistilledFacts(BaseModel):
    facts: list[str]
