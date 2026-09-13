from fastapi import APIRouter
from pydantic import BaseModel

from app.services.research import research_company

router = APIRouter(prefix="/research", tags=["research"])


class ResearchRequest(BaseModel):
    company_name: str
    role_context: str = ""


@router.post("/company")
def company(req: ResearchRequest):
    return research_company(req.company_name, req.role_context)
