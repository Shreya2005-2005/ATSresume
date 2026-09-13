from fastapi import APIRouter
from pydantic import BaseModel

from app.models.jd import ParsedJD
from app.models.matching import EvidenceMatchResult
from app.services.draft_builder import build_initial_draft
from app.services.pipeline_orchestrator import run_stages_4_to_6

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.get("/initial-draft")
def initial_draft():
    return build_initial_draft()


class RefineRequest(BaseModel):
    jd: ParsedJD
    match_result: EvidenceMatchResult


@router.post("/refine")
def refine(req: RefineRequest):
    draft_v1 = build_initial_draft()
    return run_stages_4_to_6(draft_v1, req.jd, req.match_result)
