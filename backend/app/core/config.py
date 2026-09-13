import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

# Candidate evidence, profile, and run history are mutable application data
# (not just static seed content) -- they get written to at runtime whenever
# someone adds evidence, edits their profile, or runs the pipeline. On a
# host that provides a persistent disk/volume, point DATA_DIR at its mount
# path via the DATA_DIR env var so this survives restarts and redeploys;
# it defaults to a folder inside the repo for local development, where the
# working directory itself is already persistent.
_BUNDLED_DATA_DIR = BASE_DIR / "data"
DATA_DIR = Path(os.getenv("DATA_DIR", str(_BUNDLED_DATA_DIR)))
EVIDENCE_DIR = DATA_DIR / "evidence"
CHROMA_DIR = DATA_DIR / "chroma_db"
RUNS_DIR = DATA_DIR / "runs"

for d in (DATA_DIR, EVIDENCE_DIR, CHROMA_DIR, RUNS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# First boot against a fresh/empty persistent volume: seed it from the
# bundled defaults checked into the repo (sample evidence, sample JD, a
# placeholder profile) so the app isn't missing files it expects to read.
# A no-op once those files exist, so later restarts never overwrite
# whatever the user has since edited.
if DATA_DIR != _BUNDLED_DATA_DIR:
    for name in ("candidate_profile.json", "sample_jd.txt"):
        dest = DATA_DIR / name
        src = _BUNDLED_DATA_DIR / name
        if not dest.exists() and src.exists():
            shutil.copy(src, dest)
    evidence_dest = EVIDENCE_DIR / "candidate_evidence.json"
    evidence_src = _BUNDLED_DATA_DIR / "evidence" / "candidate_evidence.json"
    if not evidence_dest.exists() and evidence_src.exists():
        shutil.copy(evidence_src, evidence_dest)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL_HEAVY = os.getenv("GROQ_MODEL_HEAVY", "openai/gpt-oss-120b")
GROQ_MODEL_LIGHT = os.getenv("GROQ_MODEL_LIGHT", "openai/gpt-oss-20b")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

EVIDENCE_MATCH_CONFIDENCE_THRESHOLD = float(
    os.getenv("EVIDENCE_MATCH_CONFIDENCE_THRESHOLD", "0.5")
)
MAX_FACT_CHECK_ITERATIONS = int(os.getenv("MAX_FACT_CHECK_ITERATIONS", "3"))

# Comma-separated list of allowed frontend origins for CORS. Defaults to
# the local Next.js dev server; set this to the deployed frontend's real
# URL(s) (e.g. "https://your-app.vercel.app") once hosted, or requests
# from that domain will be rejected by the browser.
FRONTEND_ORIGINS = [
    o.strip() for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",") if o.strip()
]
