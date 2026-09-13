"""Full pipeline orchestrator (Stages 0-9), streaming as it goes.

This is the live-trace version of the pipeline: every stage transition,
persona switch, gap flag, and fact-check verdict is yielded as an event
the moment it happens (not narrated after the fact), so a Server-Sent
Events endpoint can forward these directly to the frontend's Live Agent
Trace panel. State is persisted to disk after every stage per the run's
state schema, so a run's full history survives independent of the stream.
"""
import logging
import uuid
from typing import Generator

from app.core.config import MAX_FACT_CHECK_ITERATIONS, RUNS_DIR
from app.models.jd import ParsedJD
from app.models.pipeline import ResumeDraft
from app.services.ats_filter import run_ats_filter
from app.services.draft_builder import build_initial_draft
from app.services.evidence_matching import match_jd_to_evidence
from app.services.evidence_store import get_all_evidence, ingest_default_evidence
from app.services.fact_check import fact_check_bullets
from app.services.jd_parser import parse_job_description
from app.services.pdf_renderer import render_pdf
from app.services.recruiter_eval import evaluate_draft
from app.services.report_generator import build_change_report, render_report_markdown
from app.services.research import research_company
from app.services.state_store import run_dir, save_state
from app.services.xyz_rewrite import rewrite_bullets


def _event(type_: str, message: str, **extra) -> dict:
    return {"type": type_, "message": message, **extra}


def run_pipeline_stream(raw_jd: str) -> Generator[dict, None, None]:
    run_id = uuid.uuid4().hex[:12]
    state = {
        "run_id": run_id,
        "jd_requirements": {},
        "company_context": {},
        "evidence_matches": {},
        "draft_versions": {"v1": None, "v2": None, "final": None},
        "evaluation_v1": {},
        "citation_map": {},
        "fact_check_results": {"iteration": 0, "passed": [], "failed": []},
        "fact_check_iterations": [],
        "ats_result": {},
        "revision_history": [],
        "final_status": "in_progress",
    }
    save_state(run_id, state)

    try:
        yield _event("run_started", f"Starting run {run_id}...", run_id=run_id)

        # --- Stage 0: Candidate Evidence Store ---
        yield _event("stage_start", "Loading Candidate Evidence Store...", stage="stage0")
        count = ingest_default_evidence(reset=True)
        yield _event("stage_done", f"Loaded {count} evidence units.", stage="stage0")

        # --- Stage 1: JD Parser ---
        yield _event("stage_start", "Stage 1: Parsing job description...", stage="stage1")
        jd: ParsedJD = parse_job_description(raw_jd)
        state["jd_requirements"] = jd.model_dump()
        save_state(run_id, state)
        yield _event(
            "stage_done",
            f"Parsed JD for {jd.company_name} ({jd.seniority_level}): "
            f"{len(jd.required_skills)} required skills.",
            stage="stage1",
            payload=jd.model_dump(),
        )

        # --- Stage 2: Company/Role Research ---
        yield _event("stage_start", f"Stage 2: Researching {jd.company_name}...", stage="stage2")
        context = research_company(jd.company_name, role_context=", ".join(jd.key_responsibilities))
        state["company_context"] = context.model_dump()
        save_state(run_id, state)
        yield _event(
            "stage_done",
            f"Research complete (source: {context.source}), {len(context.facts)} facts.",
            stage="stage2",
            payload=context.model_dump(),
        )

        # --- Stage 3: Evidence Matching ---
        yield _event("stage_start", "Stage 3: Matching evidence against JD requirements...", stage="stage3")
        match_result = match_jd_to_evidence(jd)
        state["evidence_matches"] = match_result.model_dump()
        save_state(run_id, state)
        for m in match_result.matches:
            if m.is_gap:
                yield _event(
                    "gap_flagged",
                    f"Gap: \"{m.requirement}\" — {m.rationale}",
                    requirement=m.requirement,
                )
            else:
                yield _event(
                    "match_found",
                    f"Matched: \"{m.requirement}\" (confidence {m.confidence_score:.2f})",
                    requirement=m.requirement,
                )
        yield _event(
            "stage_done",
            f"Evidence matching complete: {len(match_result.gaps)} gap(s) found.",
            stage="stage3",
        )

        # --- Stage 4: Draft Generation / Recruiter Evaluation ---
        draft_v1 = build_initial_draft()
        state["draft_versions"]["v1"] = draft_v1.model_dump()
        save_state(run_id, state)
        yield _event("persona", "Recruiter persona: scoring draft against the JD...", stage="stage4")
        evaluation = evaluate_draft(draft_v1, jd, match_result)
        state["evaluation_v1"] = evaluation.model_dump()
        save_state(run_id, state)
        yield _event(
            "stage_done",
            f"Compatibility score: {evaluation.compatibility_score}/100. "
            f"{len(evaluation.weak_bullet_ids)} bullet(s) flagged weak.",
            stage="stage4",
            payload=evaluation.model_dump(),
        )

        # --- Stages 5-6: XYZ Rewrite <-> Fact-Check Gate loop ---
        weak_ids = set(evaluation.weak_bullet_ids)
        weak_bullets = [b for b in draft_v1.bullets if b.id in weak_ids]
        evidence_pool = get_all_evidence()

        remaining = {b.id: b for b in weak_bullets}
        finalized = {}
        feedback: dict[str, str] = {}

        if weak_bullets:
            yield _event(
                "loop_start",
                f"{len(weak_bullets)} bullet(s) need rewriting (max {MAX_FACT_CHECK_ITERATIONS} attempts each).",
            )

        for iteration in range(1, MAX_FACT_CHECK_ITERATIONS + 1):
            if not remaining:
                break
            current_bullets = list(remaining.values())

            yield _event(
                "persona",
                f"Recruiter persona (rewrite): XYZ rewrite attempt {iteration} for "
                f"{len(current_bullets)} bullet(s)...",
                stage="stage5",
                iteration=iteration,
            )
            rewrite_result = rewrite_bullets(
                current_bullets, evidence_pool, jd, feedback, evaluation.missing_keywords
            )
            by_id = {rb.bullet_id: rb for rb in rewrite_result.rewritten_bullets}

            yield _event(
                "persona",
                "Fact-check gate: verifying every claim against cited evidence...",
                stage="stage6",
                iteration=iteration,
            )
            check_result = fact_check_bullets(rewrite_result.rewritten_bullets)
            checks_by_id = {c.bullet_id: c for c in check_result.checks}

            state["fact_check_iterations"].append(
                {
                    "iteration": iteration,
                    "rewrites": [rb.model_dump() for rb in rewrite_result.rewritten_bullets],
                    "checks": [c.model_dump() for c in check_result.checks],
                }
            )

            passed_ids, failed_ids = [], []
            new_feedback: dict[str, str] = {}
            for bullet_id, rb in by_id.items():
                check = checks_by_id.get(bullet_id)
                if check and check.status == "PASSED":
                    finalized[bullet_id] = rb
                    remaining.pop(bullet_id, None)
                    passed_ids.append(bullet_id)
                    yield _event(
                        "fact_check_passed",
                        f"[{bullet_id}] PASSED fact-check: {check.reason}",
                        bullet_id=bullet_id,
                        iteration=iteration,
                    )
                else:
                    reason = check.reason if check else "No fact-check result returned for this bullet."
                    new_feedback[bullet_id] = reason
                    failed_ids.append(bullet_id)
                    yield _event(
                        "fact_check_failed",
                        f"[{bullet_id}] FAILED fact-check: {reason} — sending back to rewrite.",
                        bullet_id=bullet_id,
                        iteration=iteration,
                        reason=reason,
                    )
            feedback = new_feedback
            state["fact_check_results"] = {"iteration": iteration, "passed": passed_ids, "failed": failed_ids}
            save_state(run_id, state)

        needs_human_review = len(remaining) > 0
        if weak_bullets:
            yield _event(
                "loop_done",
                "All rewritten claims verified." if not needs_human_review
                else f"{len(remaining)} bullet(s) still unresolved after {MAX_FACT_CHECK_ITERATIONS} attempts — needs human review.",
            )

        final_bullets = []
        citation_map: dict[str, list[str]] = {}
        revision_history: list[dict] = []
        for b in draft_v1.bullets:
            if b.id in finalized:
                rb = finalized[b.id]
                final_bullets.append(
                    b.model_copy(update={"text": rb.rewritten_text, "evidence_ids": rb.evidence_ids})
                )
                citation_map[b.id] = rb.evidence_ids
                revision_history.append(
                    {
                        "bullet_id": b.id,
                        "before": rb.original_text,
                        "after": rb.rewritten_text,
                        "reason": rb.reasoning,
                        "evidence_ids": rb.evidence_ids,
                    }
                )
            elif b.id in remaining:
                final_bullets.append(b)
                citation_map[b.id] = b.evidence_ids
                revision_history.append(
                    {
                        "bullet_id": b.id,
                        "before": b.text,
                        "after": b.text,
                        "reason": "Fact-check gate could not verify a rewrite within "
                        f"{MAX_FACT_CHECK_ITERATIONS} attempts; kept original evidence-backed text for human review.",
                        "evidence_ids": b.evidence_ids,
                    }
                )
            else:
                final_bullets.append(b)
                citation_map[b.id] = b.evidence_ids

        draft_v2 = ResumeDraft(version="v2", summary=draft_v1.summary, bullets=final_bullets)
        state["draft_versions"]["v2"] = draft_v2.model_dump()
        state["citation_map"] = citation_map
        state["revision_history"] = revision_history
        needs_human_review_bullet_ids = list(remaining.keys())
        save_state(run_id, state)

        # --- Stage 7: ATS Filter Pass ---
        yield _event("persona", "ATS parser + tired hiring manager: scanning for scannability and keyword coverage...", stage="stage7")
        ats_result = run_ats_filter(draft_v2, jd)
        state["ats_result"] = ats_result.model_dump()
        save_state(run_id, state)
        yield _event(
            "stage_done",
            f"ATS score: {ats_result.ats_score}/100. {len(ats_result.micro_rewrites)} micro-rewrite(s) applied.",
            stage="stage7",
            payload=ats_result.model_dump(),
        )

        micro_by_id = {mr.bullet_id: mr.rewritten_text for mr in ats_result.micro_rewrites}
        final_bullets_v3 = [
            b.model_copy(update={"text": micro_by_id[b.id]}) if b.id in micro_by_id else b
            for b in draft_v2.bullets
        ]
        draft_final = ResumeDraft(version="final", summary=draft_v2.summary, bullets=final_bullets_v3)
        state["draft_versions"]["final"] = draft_final.model_dump()

        final_status = "needs_human_review" if needs_human_review else "verified"
        state["final_status"] = final_status
        save_state(run_id, state)

        # --- Stage 8: PDF Rendering ---
        yield _event("stage_start", "Stage 8: Rendering PDF...", stage="stage8")
        pdf_path = run_dir(run_id) / "resume.pdf"
        render_pdf(draft_final, pdf_path)
        yield _event("stage_done", f"PDF rendered to {pdf_path.name}.", stage="stage8")

        # --- Stage 9: Evidence/Change Report ---
        yield _event("stage_start", "Stage 9: Generating evidence/change report...", stage="stage9")
        stage456_like = {
            "evaluation_v1": evaluation.model_dump(),
            "revision_history": revision_history,
            "needs_human_review_bullet_ids": needs_human_review_bullet_ids,
            "final_status": final_status,
        }
        report = build_change_report(run_id, jd, match_result, stage456_like, ats_result, draft_final)
        md = render_report_markdown(report)
        (run_dir(run_id) / "report.md").write_text(md, encoding="utf-8")
        yield _event("stage_done", "Report generated.", stage="stage9", payload=report.model_dump())

        yield _event(
            "run_complete",
            f"Run complete — status: {final_status}.",
            run_id=run_id,
            final_status=final_status,
        )

    except Exception as e:
        state["final_status"] = "error"
        save_state(run_id, state)
        # Yield the graceful error event and let the generator end normally
        # (no re-raise): raising here would abort the SSE response mid-chunk,
        # which the browser reports as an opaque network error instead of
        # ever showing this message. The full traceback is still logged
        # server-side for debugging.
        logging.exception("Pipeline run %s failed", run_id)
        yield _event("error", f"Pipeline failed: {e}", run_id=run_id)
