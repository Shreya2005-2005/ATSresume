"""Persists the per-run state schema to disk so the frontend can poll
progress and so a run's full history survives a server restart."""
import json
from pathlib import Path

from app.core.config import RUNS_DIR


def run_dir(run_id: str) -> Path:
    d = RUNS_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_state(run_id: str, state: dict) -> None:
    path = run_dir(run_id) / "state.json"
    path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def load_state(run_id: str) -> dict:
    path = run_dir(run_id) / "state.json"
    if not path.exists():
        raise FileNotFoundError(f"No state found for run_id={run_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_runs() -> list[dict]:
    """Lists past runs that produced a resume, newest first."""
    runs = []
    for d in RUNS_DIR.iterdir():
        if not d.is_dir():
            continue
        resume_path = d / "resume.pdf"
        if not resume_path.exists():
            continue
        company_name = None
        final_status = None
        custom_label = None
        state_path = d / "state.json"
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                company_name = (state.get("jd_requirements") or {}).get("company_name")
                final_status = state.get("final_status")
                custom_label = state.get("custom_label")
            except (json.JSONDecodeError, OSError):
                pass
        if final_status not in ("verified", "needs_human_review"):
            continue
        runs.append(
            {
                "run_id": d.name,
                "company_name": custom_label or company_name,
                "final_status": final_status,
                "updated_at": resume_path.stat().st_mtime,
            }
        )
    runs.sort(key=lambda r: r["updated_at"], reverse=True)
    return runs
