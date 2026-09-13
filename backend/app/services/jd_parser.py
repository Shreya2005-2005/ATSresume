from app.core.config import GROQ_MODEL_HEAVY
from app.models.jd import ParsedJD
from app.services.llm_client import call_llm_json

SYSTEM_PROMPT = """You are a precise job-description parser. Extract structured \
requirements from the raw job posting text you are given. Do not invent \
requirements that are not stated or clearly implied in the text. Respond with a \
single JSON object with EXACTLY these keys: company_name (string), \
seniority_level (string, one of: Intern, Junior, Mid, Senior, Staff, Lead, \
Unknown), required_skills (array of strings), nice_to_have_skills (array of \
strings), key_responsibilities (array of strings, each a short phrase). If the \
company name is not stated, use "Unknown". Keep skills as short canonical \
terms (e.g. "Kubernetes", not "experience with Kubernetes")."""


def parse_job_description(raw_text: str) -> ParsedJD:
    user_prompt = f"Job description:\n\n{raw_text.strip()}"
    result = call_llm_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema_model=ParsedJD,
        model=GROQ_MODEL_HEAVY,
        temperature=0.1,
    )
    return result
