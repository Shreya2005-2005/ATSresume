"""Stage 8 — PDF Rendering.

No LaTeX toolchain is available in this Windows/PowerShell environment
(no pdflatex), so this renders the fact-checked draft to HTML via Jinja2
and converts it to PDF using headless Microsoft Edge's built-in
print-to-pdf, which ships with Windows and needs no extra native
dependencies (unlike WeasyPrint, which requires GTK/Pango libraries that
aren't installed by default on Windows).
"""
import json
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.core.config import BASE_DIR, DATA_DIR
from app.models.pipeline import ResumeDraft
from app.services.evidence_store import get_all_evidence

TEMPLATE_DIR = BASE_DIR / "app" / "templates"
SECTION_ORDER = ["Experience", "Projects", "Open Source", "Achievements"]

_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

_EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def _find_edge() -> str:
    for path in _EDGE_CANDIDATES:
        if Path(path).exists():
            return path
    raise RuntimeError(
        "Could not find msedge.exe in the expected install locations. "
        "PDF rendering requires Microsoft Edge."
    )


def _load_profile() -> dict:
    path = DATA_DIR / "candidate_profile.json"
    return json.loads(path.read_text(encoding="utf-8"))


def assemble_resume_data(draft: ResumeDraft) -> dict:
    """Shared data assembly for every resume export format (HTML/PDF, LaTeX,
    ...): groups bullets into sections and pulls skills/education/
    certifications out of the evidence store."""
    profile = _load_profile()

    sections: dict[str, list] = {name: [] for name in SECTION_ORDER}
    for b in draft.bullets:
        sections.setdefault(b.section, []).append(b)

    evidence = get_all_evidence()
    skills: set[str] = set()
    education = []
    certifications = []
    for e in evidence:
        meta = e["metadata"]
        if meta["type"] == "skill_note" and meta.get("skills"):
            skills.update(s.strip() for s in meta["skills"].split(",") if s.strip())
        elif meta["type"] == "education":
            education.append(meta)
        elif meta["type"] == "certification":
            certifications.append(meta)

    return {
        "profile": profile,
        "summary": draft.summary,
        "sections": {k: v for k, v in sections.items() if v},
        "skills": sorted(skills),
        "education": education,
        "certifications": certifications,
    }


def render_resume_html(draft: ResumeDraft) -> str:
    data = assemble_resume_data(draft)
    template = _env.get_template("resume.html.jinja")
    return template.render(**data)


def render_pdf(draft: ResumeDraft, output_path: Path) -> Path:
    html = render_resume_html(draft)
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        html_path = Path(tmp_dir) / f"resume_{uuid.uuid4().hex}.html"
        html_path.write_text(html, encoding="utf-8")

        edge = _find_edge()
        cmd = [
            edge,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={output_path}",
            html_path.as_uri(),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        # Edge's headless print-to-pdf process can exit before the file is
        # fully flushed to disk, so give it a grace period before treating a
        # missing file as a real failure. Larger resumes (more evidence ->
        # more content -> the fit-to-page script doing more shrink
        # iterations) take longer, so this needs real headroom, not just a
        # couple hundred ms.
        for _ in range(100):
            if output_path.exists() and output_path.stat().st_size > 0:
                break
            time.sleep(0.1)

        if result.returncode != 0 or not output_path.exists():
            raise RuntimeError(
                f"Edge headless PDF rendering failed (exit {result.returncode}): "
                f"{result.stderr or result.stdout}"
            )

    return output_path
