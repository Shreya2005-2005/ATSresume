from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.config import RUNS_DIR
from app.models.pipeline import ResumeDraft
from app.services.latex_export import build_latex_resume
from app.services.pdf_renderer import render_pdf

router = APIRouter(prefix="/pdf", tags=["pdf"])


class RenderRequest(BaseModel):
    draft: ResumeDraft
    run_id: str = "test-run"


@router.post("/render")
def render(req: RenderRequest):
    output_path = RUNS_DIR / req.run_id / "resume.pdf"
    render_pdf(req.draft, output_path)
    return FileResponse(output_path, media_type="application/pdf", filename="resume.pdf")


class LatexRequest(BaseModel):
    draft: ResumeDraft


@router.post("/latex")
def render_latex(req: LatexRequest):
    return {"latex": build_latex_resume(req.draft)}
