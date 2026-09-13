from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.models.evidence import EvidenceType, EvidenceUnit
from app.services import evidence_store, resume_import

router = APIRouter(prefix="/evidence", tags=["evidence"])


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


class CreateEvidenceRequest(BaseModel):
    type: EvidenceType
    title: str
    description: str
    metrics: str | None = None
    skills: list[str] = []
    source_link: str | None = None
    date_range: str | None = None


@router.post("/ingest-default")
def ingest_default():
    count = evidence_store.ingest_default_evidence(reset=True)
    return {"ingested": count}


@router.get("")
def list_evidence():
    return evidence_store.get_all_evidence()


@router.post("/query")
def query(req: QueryRequest):
    return evidence_store.query_evidence(req.query, top_k=req.top_k)


@router.post("")
def add_evidence(req: CreateEvidenceRequest):
    unit = EvidenceUnit(id=evidence_store.next_evidence_id(req.type), **req.model_dump(exclude={"type"}), type=req.type)
    evidence_store.add_evidence_unit(unit)
    return unit.model_dump()


@router.delete("/{evidence_id}")
def delete_evidence(evidence_id: str):
    deleted = evidence_store.delete_evidence_unit(evidence_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Evidence item not found")
    return {"deleted": evidence_id}


@router.post("/extract-from-resume")
async def extract_from_resume(file: UploadFile = File(...)):
    content = await file.read()
    try:
        text = resume_import.extract_text_from_upload(file.filename or "", content)
        result = resume_import.extract_evidence_from_resume(text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result.model_dump()
