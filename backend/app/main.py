import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.core.config import DATA_DIR, FRONTEND_ORIGINS
from app.routers import ats, evidence, jd, matching, pdf, pipeline, report, research, runs

app = FastAPI(title="Autonomous Resume & Application Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(evidence.router)
app.include_router(jd.router)
app.include_router(research.router)
app.include_router(matching.router)
app.include_router(pipeline.router)
app.include_router(ats.router)
app.include_router(pdf.router)
app.include_router(report.router)
app.include_router(runs.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/sample-jd", response_class=PlainTextResponse)
def sample_jd():
    return (DATA_DIR / "sample_jd.txt").read_text(encoding="utf-8")


@app.get("/profile")
def profile():
    return json.loads((DATA_DIR / "candidate_profile.json").read_text(encoding="utf-8"))


class ProfileLink(BaseModel):
    label: str
    url: str


class ProfileUpdate(BaseModel):
    name: str
    email: str
    phone: str
    location: str
    links: list[ProfileLink] = []


@app.put("/profile")
def update_profile(profile: ProfileUpdate):
    path = DATA_DIR / "candidate_profile.json"
    path.write_text(json.dumps(profile.model_dump(), indent=2), encoding="utf-8")
    return profile.model_dump()
