import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from app.models.pipeline import ResumeDraft
from app.services.chat_edit import apply_chat_edit
from app.services.run_orchestrator import run_pipeline_stream
from app.services.state_store import list_runs, run_dir, load_state, save_state

router = APIRouter(prefix="/runs", tags=["runs"])


class RunRequest(BaseModel):
    raw_jd: str


@router.post("/stream")
def stream_run(req: RunRequest):
    def event_stream():
        for event in run_pipeline_stream(req.raw_jd):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("")
def list_runs_endpoint():
    return list_runs()


@router.get("/{run_id}/state")
def get_state(run_id: str):
    try:
        return load_state(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found")


@router.put("/{run_id}/draft")
def update_draft(run_id: str, draft: ResumeDraft):
    try:
        state = load_state(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found")
    state["draft_versions"]["final"] = draft.model_dump()
    save_state(run_id, state)
    return draft.model_dump()


class ChatEditRequest(BaseModel):
    instruction: str
    draft: ResumeDraft


class ChatEditResponse(BaseModel):
    draft: ResumeDraft
    explanation: str
    rejected_bullet_ids: list[str] = []


@router.post("/{run_id}/chat-edit")
def chat_edit(run_id: str, req: ChatEditRequest):
    try:
        state = load_state(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found")

    new_draft, explanation, rejected = apply_chat_edit(req.draft, req.instruction)

    state["draft_versions"]["final"] = new_draft.model_dump()
    save_state(run_id, state)

    return ChatEditResponse(draft=new_draft, explanation=explanation, rejected_bullet_ids=rejected)


class LabelRequest(BaseModel):
    label: str


@router.put("/{run_id}/label")
def set_run_label(run_id: str, req: LabelRequest):
    try:
        state = load_state(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found")
    state["custom_label"] = req.label.strip()
    save_state(run_id, state)
    return {"label": state["custom_label"]}


@router.get("/{run_id}/resume.pdf")
def get_resume_pdf(run_id: str):
    path = run_dir(run_id) / "resume.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF not yet rendered for this run")
    return FileResponse(path, media_type="application/pdf", filename="resume.pdf")


@router.get("/{run_id}/report.md", response_class=PlainTextResponse)
def get_report_md(run_id: str):
    path = run_dir(run_id) / "report.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not yet generated for this run")
    return path.read_text(encoding="utf-8")
