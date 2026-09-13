import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
EVIDENCE_DIR = DATA_DIR / "evidence"
CHROMA_DIR = DATA_DIR / "chroma_db"
RUNS_DIR = DATA_DIR / "runs"

for d in (DATA_DIR, EVIDENCE_DIR, CHROMA_DIR, RUNS_DIR):
    d.mkdir(parents=True, exist_ok=True)

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
