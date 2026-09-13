from fastapi import APIRouter

from app.models.jd import ParsedJD
from app.services.evidence_matching import match_jd_to_evidence

router = APIRouter(prefix="/matching", tags=["matching"])


@router.post("/evidence")
def evidence_matching(jd: ParsedJD):
    return match_jd_to_evidence(jd)
