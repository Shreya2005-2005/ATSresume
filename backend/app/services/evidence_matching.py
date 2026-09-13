"""Stage 3 — Evidence Matching (RAG retrieval + adequacy judgment).

For each JD requirement, retrieve the closest evidence from the Candidate
Evidence Store, then judge whether that evidence actually substantiates the
requirement's specifics (years of experience, employment vs. personal/
open-source work, production vs. non-production scope) rather than merely
overlapping on topic. Raw embedding cosine similarity alone cannot make
this distinction — "45+ merged PRs to a Kubernetes CLI tool" and "5+ years
production Kubernetes experience" score similarly high on pure topical
similarity, which would silently defeat the gap-flagging this stage exists
for. Requirements the evidence does not adequately support are flagged as
gaps — never silently dropped, never papered over with a guess.

Retrieval (vector search) still runs one query per requirement -- it's
free and local. The adequacy judgment, which needs an LLM call, is batched
into a single request covering every requirement at once rather than one
call per requirement: same judgment quality, ~12x fewer tokens/round-trips
against the model's rate limit.
"""
from app.core.config import EVIDENCE_MATCH_CONFIDENCE_THRESHOLD, GROQ_MODEL_LIGHT
from app.models.jd import ParsedJD
from app.models.matching import BatchAdequacyJudgment, EvidenceMatchResult, RequirementMatch
from app.services.evidence_store import query_evidence
from app.services.llm_client import call_llm_json

RETRIEVAL_TOP_K = 3
MAX_DOCUMENT_CHARS = 220

BATCH_ADEQUACY_SYSTEM_PROMPT = """You are a strict, evidence-only requirement-adequacy \
judge for a resume-tailoring pipeline. You will be given a numbered list of JOB \
REQUIREMENTS, each with a list of CANDIDATE EVIDENCE snippets retrieved because they \
are topically related. For EACH requirement, decide whether the evidence actually \
and directly substantiates it, not merely whether it shares keywords or topic.

Be strict about specifics that change whether a requirement is truly met:
- Years of experience: evidence must show enough real time/duration, not just presence of the skill
- Employment vs. personal/open-source work: production employment experience is NOT substantiated by personal projects or open-source contributions alone
- Production vs. non-production scope: operating something in production is NOT substantiated by using it in a personal project, a course, or a contribution to someone else's project
- Scale/scope claims: don't accept a claim that overstates scale beyond what the evidence shows

If the evidence only shows adjacent, partial, or weaker support (for example: \
open-source contributions to a tool, when the requirement demands years of \
production employment experience with that tool), you MUST score it as low \
adequacy and explain the gap in your rationale — do not round up.

Respond with a JSON object: judgments, an array with EXACTLY one entry per \
requirement given, in the same order, each with: requirement (string, echo the \
exact requirement text you were given), is_adequate (bool), adequacy_score (0.0 to \
1.0), rationale (one concise sentence, referencing the specific gap if inadequate)."""


def _judge_adequacy_batch(
    items: list[tuple[str, list[dict]]],
) -> dict[str, tuple[bool, float, str]]:
    """Returns requirement -> (is_adequate, adequacy_score, rationale)."""
    blocks = []
    for i, (requirement, docs) in enumerate(items):
        if docs:
            evidence_block = "\n".join(
                f"  {j + 1}. {d['document'][:MAX_DOCUMENT_CHARS]}" for j, d in enumerate(docs)
            )
        else:
            evidence_block = "  (no evidence retrieved at all)"
        blocks.append(f"Requirement {i + 1}: {requirement}\nCandidate evidence:\n{evidence_block}")
    user_prompt = "\n\n".join(blocks)

    result = call_llm_json(
        system_prompt=BATCH_ADEQUACY_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema_model=BatchAdequacyJudgment,
        model=GROQ_MODEL_LIGHT,
        temperature=0.0,
        max_tokens=2500,
    )

    by_requirement: dict[str, tuple[bool, float, str]] = {}
    for j in result.judgments:
        by_requirement[j.requirement.strip().lower()] = (j.is_adequate, j.adequacy_score, j.rationale)
    return by_requirement


def match_jd_to_evidence(jd: ParsedJD) -> EvidenceMatchResult:
    requirements = [(s, "required_skill") for s in jd.required_skills] + [
        (r, "responsibility") for r in jd.key_responsibilities
    ]

    retrieved = [query_evidence(req, top_k=RETRIEVAL_TOP_K) for req, _ in requirements]
    judgments = _judge_adequacy_batch(list(zip((r for r, _ in requirements), retrieved)))

    matches: list[RequirementMatch] = []
    for (requirement, kind), results in zip(requirements, retrieved):
        judgment = judgments.get(requirement.strip().lower())
        if judgment is None:
            # Fail-safe: if the batch response didn't clearly cover this
            # requirement, never assume it's fine -- treat as an honest gap.
            is_adequate, adequacy_score, rationale = (
                False,
                0.0,
                "No adequacy judgment was returned for this requirement; treated as a gap.",
            )
        else:
            is_adequate, adequacy_score, rationale = judgment

        is_gap = (not is_adequate) or adequacy_score < EVIDENCE_MATCH_CONFIDENCE_THRESHOLD
        matches.append(
            RequirementMatch(
                requirement=requirement,
                requirement_kind=kind,
                matched_evidence_ids=[r["evidence_id"] for r in results],
                confidence_score=adequacy_score,
                is_gap=is_gap,
                rationale=rationale,
            )
        )

    gaps = [m.requirement for m in matches if m.is_gap]
    return EvidenceMatchResult(matches=matches, gaps=gaps)
