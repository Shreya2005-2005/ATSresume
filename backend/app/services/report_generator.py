"""Stage 9 — Evidence/Change Report.

A deterministic aggregation of everything Stages 3-7 already produced and
justified, not a fresh LLM narrative — every entry here already carries a
real reason and evidence citation from the stage that made the change, so
generating the report itself introduces no new fabrication risk.
"""
from app.models.ats import ATSResult
from app.models.jd import ParsedJD
from app.models.matching import EvidenceMatchResult
from app.models.pipeline import ResumeDraft
from app.models.report import ChangeReport, ReportEntry


def build_change_report(
    run_id: str,
    jd: ParsedJD,
    match_result: EvidenceMatchResult,
    stage456_result: dict,
    ats_result: ATSResult,
    draft_v2: ResumeDraft,
) -> ChangeReport:
    entries = [
        ReportEntry(
            bullet_id=r["bullet_id"],
            before=r["before"],
            after=r["after"],
            reason=r["reason"],
            evidence_ids=r["evidence_ids"],
        )
        for r in stage456_result["revision_history"]
        if r["before"] != r["after"]
    ]

    evidence_by_bullet = {b.id: b.evidence_ids for b in draft_v2.bullets}
    for mr in ats_result.micro_rewrites:
        entries.append(
            ReportEntry(
                bullet_id=mr.bullet_id,
                before=mr.original_text,
                after=mr.rewritten_text,
                reason=f"[ATS pass] {mr.reason}",
                evidence_ids=evidence_by_bullet.get(mr.bullet_id, []),
            )
        )

    evaluation = stage456_result["evaluation_v1"]

    return ChangeReport(
        run_id=run_id,
        company_name=jd.company_name,
        compatibility_score=evaluation["compatibility_score"],
        ats_score=ats_result.ats_score,
        final_status=stage456_result["final_status"],
        gaps=match_result.gaps,
        red_flags=evaluation["red_flags"],
        entries=entries,
        needs_human_review_bullets=stage456_result["needs_human_review_bullet_ids"],
    )


def render_report_markdown(report: ChangeReport) -> str:
    lines = [
        f"# Evidence & Change Report — {report.company_name}",
        "",
        f"**Run ID:** {report.run_id}  ",
        f"**Compatibility score:** {report.compatibility_score}/100  ",
        f"**ATS score:** {report.ats_score}/100  ",
        f"**Final status:** {report.final_status}",
        "",
    ]

    if report.red_flags:
        lines.append("## Red flags identified")
        lines.extend(f"- {rf}" for rf in report.red_flags)
        lines.append("")

    if report.gaps:
        lines.append("## Confirmed gaps (no adequate evidence exists)")
        lines.append(
            "These job requirements were never claimed on the resume because the "
            "Candidate Evidence Store does not adequately support them."
        )
        lines.extend(f"- {g}" for g in report.gaps)
        lines.append("")

    if report.entries:
        lines.append("## Changes made and why")
        for e in report.entries:
            lines.append(f"### Bullet `{e.bullet_id}`")
            lines.append(f"- **Before:** {e.before}")
            lines.append(f"- **After:** {e.after}")
            lines.append(f"- **Why:** {e.reason}")
            if e.evidence_ids:
                lines.append(f"- **Evidence:** {', '.join(e.evidence_ids)}")
            lines.append("")
    else:
        lines.append("## Changes made and why")
        lines.append("No bullets required rewriting; draft_v1 was already compatible.")
        lines.append("")

    if report.needs_human_review_bullets:
        lines.append("## Needs human review")
        lines.append(
            "The fact-check gate could not verify a truthful rewrite for these "
            "bullets within the retry limit. The original, evidence-backed text "
            "was kept instead of an unverified claim."
        )
        lines.extend(f"- `{b}`" for b in report.needs_human_review_bullets)
        lines.append("")

    return "\n".join(lines)
