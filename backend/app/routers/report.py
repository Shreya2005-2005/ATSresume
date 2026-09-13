from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.models.ats import ATSResult
from app.models.jd import ParsedJD
from app.models.matching import EvidenceMatchResult
from app.models.pipeline import ResumeDraft
from app.services.report_generator import build_change_report, render_report_markdown

router = APIRouter(prefix="/report", tags=["report"])


class ReportRequest(BaseModel):
    run_id: str
    jd: ParsedJD
    match_result: EvidenceMatchResult
    stage456_result: dict
    ats_result: ATSResult
    draft_v2: ResumeDraft


@router.post("")
def get_report(req: ReportRequest):
    return build_change_report(
        req.run_id, req.jd, req.match_result, req.stage456_result, req.ats_result, req.draft_v2
    )


@router.post("/markdown", response_class=PlainTextResponse)
def get_report_markdown(req: ReportRequest):
    report = build_change_report(
        req.run_id, req.jd, req.match_result, req.stage456_result, req.ats_result, req.draft_v2
    )
    return render_report_markdown(report)
