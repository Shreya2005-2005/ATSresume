"""Stage 2 — Company/Role Research.

Pulls a handful of real, short facts about the target company to inform
tone/emphasis in later drafting. This never touches candidate claims —
it is purely context about the employer, sourced from Tavily when
available, a static fallback KB otherwise, and a clearly-labeled generic
fallback as a last resort.
"""
import json
import logging

from tavily import TavilyClient

from app.core.config import DATA_DIR, GROQ_MODEL_LIGHT, TAVILY_API_KEY
from app.models.company import CompanyContext, DistilledFacts
from app.services.llm_client import call_llm_json

KB_PATH = DATA_DIR / "company_kb.json"
logger = logging.getLogger(__name__)

DISTILL_SYSTEM_PROMPT = """You distill raw web search results into short, \
factual bullet points about a company. Use ONLY information present in the \
search results provided — never add outside knowledge or invented facts. \
Return 3 to 5 short bullet points (each one sentence). If the search results \
contain no usable information about the company, return an empty list."""


def _load_kb() -> dict:
    if not KB_PATH.exists():
        return {}
    return json.loads(KB_PATH.read_text(encoding="utf-8"))


def _kb_lookup(company_name: str) -> list[str] | None:
    kb = _load_kb()
    key = company_name.strip().lower()
    if key in kb:
        return kb[key]
    for k, v in kb.items():
        if k in key or key in k:
            return v
    return None


def _tavily_research(company_name: str, role_context: str) -> list[str]:
    client = TavilyClient(api_key=TAVILY_API_KEY)
    query = f"{company_name} company mission product tech stack news"
    response = client.search(query=query, search_depth="basic", max_results=5)
    results = response.get("results", [])
    if not results:
        return []

    snippets = "\n\n".join(
        f"Title: {r.get('title', '')}\nContent: {r.get('content', '')[:500]}"
        for r in results
    )
    user_prompt = (
        f"Company: {company_name}\nRole context: {role_context}\n\n"
        f"Search results:\n\n{snippets}"
    )
    distilled = call_llm_json(
        system_prompt=DISTILL_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema_model=DistilledFacts,
        model=GROQ_MODEL_LIGHT,
        temperature=0.1,
    )
    return distilled.facts


def research_company(company_name: str, role_context: str = "") -> CompanyContext:
    # Curated KB entries are checked first and take precedence over a live
    # Tavily search: a name we've explicitly pinned facts for (e.g. a demo
    # company, or any name that happens to collide with an unrelated real
    # company/product) should return deterministic, vetted facts rather than
    # whatever a broad web search happens to match on the same string.
    kb_facts = _kb_lookup(company_name) if company_name else None
    if kb_facts:
        return CompanyContext(
            company_name=company_name, facts=kb_facts, source="fallback_kb"
        )

    if company_name and company_name.lower() != "unknown" and TAVILY_API_KEY:
        try:
            facts = _tavily_research(company_name, role_context)
            if facts:
                return CompanyContext(
                    company_name=company_name, facts=facts, source="tavily"
                )
        except Exception:
            logger.warning("Tavily research failed for %s", company_name, exc_info=True)
            # fall through to generic fallback

    return CompanyContext(
        company_name=company_name or "Unknown",
        facts=[
            "No independent research is available for this company "
            "(no Tavily API key configured and no matching fallback KB entry). "
            "Context below is inferred only from the job description."
        ],
        source="generic_fallback",
    )
