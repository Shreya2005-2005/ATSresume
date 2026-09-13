from fastapi import APIRouter
from pydantic import BaseModel

from app.services.jd_parser import parse_job_description

router = APIRouter(prefix="/jd", tags=["jd"])


class ParseRequest(BaseModel):
    raw_text: str


@router.post("/parse")
def parse(req: ParseRequest):
    return parse_job_description(req.raw_text)
