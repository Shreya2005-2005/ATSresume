"""Exports the resume draft as standalone LaTeX source, ready to paste into
Overleaf (or compile locally with pdflatex). Uses only packages available in
Overleaf's default TeX Live install -- no exotic dependencies.

Unlike the PDF export, there's no LaTeX toolchain available in this
environment to actually compile-and-measure the result (see
pdf_renderer.py's docstring), so this can't shrink itself iteratively the
way the PDF's fit-to-page script does. Instead it estimates how much
content there is up front and picks a font size/spacing tier accordingly --
the same idea, computed ahead of time instead of measured live. For very
dense resumes this gets much closer to one page than a fixed template
would, but isn't a hard guarantee the way the PDF export's actual
measurement is.
"""
from app.models.pipeline import ResumeDraft
from app.services.pdf_renderer import assemble_resume_data

_SPECIAL_CHARS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def esc(text: str | None) -> str:
    """Escapes LaTeX special characters so arbitrary evidence/resume text
    can never break compilation."""
    if not text:
        return ""
    out = text.replace("\\", "\x00")  # placeholder so later replacements don't double-escape it
    for ch, repl in _SPECIAL_CHARS.items():
        if ch == "\\":
            continue
        out = out.replace(ch, repl)
    return out.replace("\x00", r"\textbackslash{}")


_TIERS = [
    # (max_score, fontsize, margin, linespread, sec_before, sec_after, item_opts)
    (800, 11, "0.75in", "1.0", "10pt", "4pt", "itemsep=2pt,topsep=2pt"),
    (1500, 10, "0.65in", "0.96", "8pt", "3pt", "itemsep=1pt,topsep=1pt"),
    (2200, 10, "0.55in", "0.92", "6pt", "2pt", "itemsep=0pt,topsep=0pt,partopsep=0pt,parsep=0pt"),
    (3000, 9, "0.45in", "0.88", "5pt", "2pt", "itemsep=0pt,topsep=0pt,partopsep=0pt,parsep=0pt"),
    (float("inf"), 8, "0.35in", "0.82", "3pt", "0pt", "itemsep=0pt,topsep=0pt,partopsep=0pt,parsep=0pt"),
]


def _pick_tier(data: dict) -> dict:
    all_bullets = [b for entries in data["sections"].values() for b in entries]
    entry_count = len(all_bullets) + len(data["education"]) + len(data["certifications"])
    total_chars = sum(len(b.text) for b in all_bullets) + sum(
        len(e.get("metrics") or "") for e in data["education"]
    )
    # Each entry carries fixed vertical overhead (title/date row, optional
    # meta/link rows) regardless of bullet length, so weight entry count
    # more heavily than raw character count.
    score = entry_count * 30 + total_chars

    for max_score, fontsize, margin, linespread, sec_before, sec_after, item_opts in _TIERS:
        if score < max_score:
            return {
                "fontsize": fontsize,
                "margin": margin,
                "linespread": linespread,
                "sec_before": sec_before,
                "sec_after": sec_after,
                "item_opts": item_opts,
            }
    return _TIERS[-1]  # unreachable (last tier's max_score is inf) but keeps type-checkers happy


_COMPACT_BODY_CHARS = 70


def _entry_block(title: str, date_range: str, meta_line: str | None, link: tuple[str, str] | None, body: str, item_opts: str) -> str:
    # A short claim doesn't need a separate bulleted-item row -- folding it
    # into the title row saves a full line per entry, which adds up fast
    # across sections with several minor entries (small PRs, one-off
    # achievements). Only substantial write-ups keep the fuller
    # title/meta/link/bullet block, matching how a hand-written resume
    # gives real weight to what matters and a single line to what doesn't.
    compact = len(body) <= _COMPACT_BODY_CHARS
    lines = [
        r"\noindent\textbf{%s} --- %s \hfill %s\\" % (esc(title), esc(body), esc(date_range))
        if compact
        else r"\noindent\textbf{%s} \hfill %s\\" % (esc(title), esc(date_range))
    ]
    if meta_line:
        lines.append(r"\textit{%s}\\" % esc(meta_line))
    if link:
        url, label = link
        lines.append(r"\href{%s}{%s}\\" % (url, esc(label)))
    if not compact:
        lines.append(r"\begin{itemize}[leftmargin=*,%s]" % item_opts)
        lines.append(r"\item %s" % esc(body))
        lines.append(r"\end{itemize}")
    return "\n".join(lines)


def build_latex_resume(draft: ResumeDraft) -> str:
    data = assemble_resume_data(draft)
    profile = data["profile"]
    tier = _pick_tier(data)
    item_opts = tier["item_opts"]

    lines: list[str] = [
        r"\documentclass[%dpt,letterpaper]{extarticle}" % tier["fontsize"],
        r"\usepackage[margin=%s]{geometry}" % tier["margin"],
        r"\usepackage{enumitem}",
        r"\usepackage{titlesec}",
        r"\usepackage[hidelinks]{hyperref}",
        r"\linespread{%s}" % tier["linespread"],
        r"\pagestyle{empty}",
        r"\setlength{\parindent}{0pt}",
        r"\titleformat{\section}{\large\bfseries}{}{0em}{}[\titlerule]",
        r"\titlespacing{\section}{0pt}{%s}{%s}" % (tier["sec_before"], tier["sec_after"]),
        r"\begin{document}",
        r"\begin{center}",
        r"{\LARGE \textbf{%s}}\\[2pt]" % esc(profile.get("name", "")).upper(),
    ]

    contact_parts = [esc(p) for p in (profile.get("location"), profile.get("email"), profile.get("phone")) if p]
    contact_line = r" $\vert$ ".join(contact_parts)
    for link in profile.get("links", []):
        contact_line += r" $\vert$ \href{%s}{%s}" % (link["url"], esc(link["label"]))
    lines.append(contact_line + r"\\")
    lines.append(r"\end{center}")

    if data["summary"]:
        lines.append(r"\section*{Summary}")
        lines.append(esc(data["summary"]))

    for section_name, entries in data["sections"].items():
        lines.append(r"\section*{%s}" % esc(section_name))
        for b in entries:
            link = None
            if b.source_link and "://" in b.source_link:
                link = (b.source_link, "GitHub" if "github.com" in b.source_link else "Link")
            meta_line = ", ".join(b.skills) if b.skills else None
            lines.append(_entry_block(b.title, b.date_range, meta_line, link, b.text, item_opts))

    if data["skills"]:
        lines.append(r"\section*{Skills}")
        lines.append(esc(", ".join(data["skills"])))

    if data["education"]:
        lines.append(r"\section*{Education}")
        for e in data["education"]:
            lines.append(r"\noindent\textbf{%s} \hfill %s\\" % (esc(e.get("title", "")), esc(e.get("date_range", ""))))
            if e.get("metrics"):
                lines.append(r"\begin{itemize}[leftmargin=*,%s]" % item_opts)
                lines.append(r"\item %s" % esc(e["metrics"]))
                lines.append(r"\end{itemize}")

    if data["certifications"]:
        # One row per certification burns a line each for what's usually a
        # short title -- list them as a single comma-separated line instead,
        # the same way Skills is handled, since that's most of a whole
        # section's worth of vertical space back for free.
        lines.append(r"\section*{Certifications}")
        cert_parts = []
        for c in data["certifications"]:
            title = esc(c.get("title", ""))
            date_range = c.get("date_range")
            cert_parts.append(r"\textbf{%s} (%s)" % (title, esc(date_range)) if date_range else r"\textbf{%s}" % title)
        lines.append(", ".join(cert_parts))

    lines.append(r"\end{document}")
    return "\n".join(lines)
