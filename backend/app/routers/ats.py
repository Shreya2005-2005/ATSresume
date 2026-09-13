from fastapi import APIRouter
from pydantic import BaseModel

from app.models.jd import ParsedJD
from app.models.pipeline import ResumeDraft
from app.services.ats_filter import run_ats_filter

router = APIRouter(prefix="/ats", tags=["ats"])


class ATSRequest(BaseModel):
    draft: ResumeDraft
    jd: ParsedJD


@router.post("/filter")
def filter_draft(req: ATSRequest):
    return run_ats_filter(req.draft, req.jd)
