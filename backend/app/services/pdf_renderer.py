"""Stage 8 — PDF Rendering.

No LaTeX toolchain is available (no pdflatex), so this renders the
fact-checked draft to HTML via Jinja2 and converts it to PDF using
Playwright's bundled headless Chromium. Playwright downloads its own
browser binary at install time (`playwright install chromium`), so this
works identically on Windows, macOS, and Linux/container deployments --
unlike relying on a system-installed browser (e.g. Microsoft Edge, which
only exists on Windows) or WeasyPrint (which needs native GTK/Pango
libraries that aren't installed by default anywhere).
"""
import json
import tempfile
import threading
import uuid
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from app.core.config import BASE_DIR, DATA_DIR
from app.models.pipeline import ResumeDraft
from app.services.evidence_store import get_all_evidence

TEMPLATE_DIR = BASE_DIR / "app" / "templates"
SECTION_ORDER = ["Experience", "Projects", "Open Source", "Achievements"]

_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

# A fresh Chromium launch is the most memory- and CPU-expensive part of
# rendering a PDF -- on a memory-constrained host, launching a brand-new
# browser process per request (and never quite reclaiming it before the
# next spikes on top) is what pushes total container memory over the
# limit. Keeping one browser instance alive across back-to-back renders
# and only opening/closing a page per render avoids that repeated launch
# cost. But staying alive *forever* trades a temporary spike for a
# permanent memory floor, which on a tight cap can be worse, not better --
# so it's closed again after a stretch of no use, releasing that memory
# back until the next render needs it. Playwright's sync API isn't safe to
# share across threads, so _lock also serializes renders -- one at a time,
# which is fine at this usage scale.
_IDLE_CLOSE_S = 120

_lock = threading.Lock()
_playwright = None
_browser = None
_idle_timer: threading.Timer | None = None


def _close_idle_browser():
    global _playwright, _browser, _idle_timer
    with _lock:
        if _browser is not None:
            try:
                _browser.close()
            except Exception:
                pass
            _browser = None
        if _playwright is not None:
            try:
                _playwright.stop()
            except Exception:
                pass
            _playwright = None
        _idle_timer = None


def _arm_idle_timer():
    global _idle_timer
    if _idle_timer is not None:
        _idle_timer.cancel()
    _idle_timer = threading.Timer(_IDLE_CLOSE_S, _close_idle_browser)
    _idle_timer.daemon = True
    _idle_timer.start()


def _get_browser():
    global _playwright, _browser, _idle_timer
    if _idle_timer is not None:
        _idle_timer.cancel()
        _idle_timer = None
    # is_connected() catches the case where the cached browser process died
    # out from under us (e.g. an OOM kill on a memory-constrained host) --
    # without this check, every render after that would keep failing
    # against a reference to a browser that no longer exists.
    if _browser is not None and not _browser.is_connected():
        _browser = None
    if _browser is None:
        if _playwright is None:
            _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(
            args=["--disable-dev-shm-usage", "--disable-gpu"]
        )
    return _browser


def _load_profile() -> dict:
    path = DATA_DIR / "candidate_profile.json"
    return json.loads(path.read_text(encoding="utf-8"))


# Education and certifications get their own dedicated block (pulled
# straight from the evidence store, below) with a cleaner one-line-per-entry
# layout. A bullet whose section falls in here would otherwise also render
# through the generic per-bullet loop and show up twice -- once cleanly,
# once as a near-duplicate with a dangling empty bullet point wherever the
# bullet's own `text` is blank (which it usually is for a certification).
_DEDICATED_SECTIONS = {"certifications", "education"}


def assemble_resume_data(draft: ResumeDraft) -> dict:
    """Shared data assembly for every resume export format (HTML/PDF, LaTeX,
    ...): groups bullets into sections and pulls skills/education/
    certifications out of the evidence store."""
    profile = _load_profile()

    sections: dict[str, list] = {name: [] for name in SECTION_ORDER}
    for b in draft.bullets:
        if b.section.strip().lower() in _DEDICATED_SECTIONS:
            continue
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

        try:
            with _lock:
                browser = _get_browser()
                page = browser.new_page()
                try:
                    # The template's inline <script> synchronously shrinks
                    # the page to fit one sheet during parsing, so by the
                    # time goto() resolves (page 'load') it has already run.
                    page.goto(html_path.as_uri())
                    page.pdf(path=str(output_path))
                finally:
                    page.close()
                _arm_idle_timer()
        except Exception as e:
            raise RuntimeError(
                f"Chromium PDF rendering failed: {e}. If this is a fresh "
                "environment, make sure `playwright install chromium --with-deps` "
                "has been run."
            ) from e

    return output_path
