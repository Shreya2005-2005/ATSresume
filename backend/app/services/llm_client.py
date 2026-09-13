"""Shared LLM clients: JSON-mode calls validated against a Pydantic schema.

Used by every LLM-backed stage (JD parsing, recruiter scoring, XYZ rewrite,
fact-check gate, ATS filter). Centralizing this keeps the "always request
structured JSON, always validate before trusting it" rule in one place.

Groq (call_llm_json) is the default for the pipeline's bulk stages -- fast
and free-tier friendly. call_gemini_json is a second, stronger option for
stages where instruction-following quality matters more than speed (e.g.
the chat-based resume editor).
"""
import json
import time

import requests
from groq import BadRequestError, Groq, RateLimitError
from pydantic import BaseModel, ValidationError

from app.core.config import GEMINI_API_KEY, GEMINI_MODEL, GROQ_API_KEY, GROQ_MODEL_HEAVY

_client = None
_RATE_LIMIT_MAX_RETRIES = 5
_RATE_LIMIT_DEFAULT_BACKOFF = 2.0
_GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def get_client() -> Groq:
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Get a free key from "
                "https://console.groq.com and add it to backend/.env"
            )
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


class LLMJSONError(Exception):
    pass


def _create_with_rate_limit_retry(client: Groq, model: str, fallback_model: str | None, **kwargs):
    """Groq's free tier has a low tokens-per-minute/per-day budget shared
    across a whole pipeline run; a 429 mid-run is an expected, recoverable
    condition, not a fatal error.

    If a fallback_model is given and different from the primary, the very
    first rate-limit hit switches to it immediately (no point sleeping and
    retrying the same exhausted per-model quota). Only once the fallback is
    also rate-limited does this fall back to sleep-and-retry backoff
    (honoring Retry-After when the API provides it)."""
    current_model = model
    switched = False
    for attempt in range(_RATE_LIMIT_MAX_RETRIES):
        try:
            return client.chat.completions.create(model=current_model, **kwargs)
        except RateLimitError as e:
            if fallback_model and not switched and current_model != fallback_model:
                current_model = fallback_model
                switched = True
                continue
            if attempt == _RATE_LIMIT_MAX_RETRIES - 1:
                raise
            retry_after = e.response.headers.get("retry-after")
            try:
                wait = float(retry_after) if retry_after else _RATE_LIMIT_DEFAULT_BACKOFF * (attempt + 1)
            except ValueError:
                wait = _RATE_LIMIT_DEFAULT_BACKOFF * (attempt + 1)
            time.sleep(min(wait, 30) + 0.25)


def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    schema_model: type[BaseModel],
    model: str = GROQ_MODEL_HEAVY,
    temperature: float = 0.2,
    max_retries: int = 2,
    max_tokens: int = 4096,
    fallback_model: str | None = GROQ_MODEL_HEAVY,
) -> BaseModel:
    client = get_client()
    last_err = None

    # Groq's json_object mode requires the literal word "json" to appear
    # somewhere in the messages, regardless of the caller's prompt wording.
    if "json" not in system_prompt.lower() and "json" not in user_prompt.lower():
        system_prompt = system_prompt + "\n\nRespond with a single valid JSON object."

    # gpt-oss models reason before answering; on a low token budget that
    # reasoning can consume the whole completion and leave nothing for the
    # actual JSON. Keep reasoning effort low and leave headroom for output.
    extra_body = {"reasoning_effort": "low"} if "gpt-oss" in model else {}

    for attempt in range(max_retries + 1):
        prompt = user_prompt
        if attempt > 0:
            prompt += (
                f"\n\nYour previous response failed validation with this error: "
                f"{last_err}\nReturn ONLY a single valid JSON object matching the "
                f"required schema. No markdown, no commentary."
            )
        try:
            resp = _create_with_rate_limit_retry(
                client,
                model=model,
                fallback_model=fallback_model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                extra_body=extra_body,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
        except BadRequestError as e:
            last_err = str(e)
            continue

        raw = resp.choices[0].message.content
        try:
            data = json.loads(raw)
            return schema_model.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            last_err = str(e)
            continue

    raise LLMJSONError(
        f"Failed to get valid JSON matching {schema_model.__name__} after "
        f"{max_retries + 1} attempts: {last_err}"
    )


def call_gemini_json(
    system_prompt: str,
    user_prompt: str,
    schema_model: type[BaseModel],
    model: str = GEMINI_MODEL,
    temperature: float = 0.3,
    max_retries: int = 2,
    max_tokens: int = 4096,
) -> BaseModel:
    """Same contract as call_llm_json but against Google's Gemini API
    (free tier via https://aistudio.google.com/apikey). Raises LLMJSONError
    on any failure -- callers that want a Groq fallback should catch it."""
    if not GEMINI_API_KEY:
        raise LLMJSONError(
            "GEMINI_API_KEY is not set. Get a free key from "
            "https://aistudio.google.com/apikey and add it to backend/.env"
        )

    last_err = None
    for attempt in range(max_retries + 1):
        prompt = user_prompt
        if attempt > 0:
            prompt += (
                f"\n\nYour previous response failed validation with this error: "
                f"{last_err}\nReturn ONLY a single valid JSON object matching the "
                f"required schema. No markdown, no commentary."
            )
        try:
            resp = requests.post(
                _GEMINI_ENDPOINT.format(model=model),
                params={"key": GEMINI_API_KEY},
                json={
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens,
                        "responseMimeType": "application/json",
                    },
                },
                timeout=60,
            )
        except requests.RequestException as e:
            last_err = str(e)
            continue

        if resp.status_code != 200:
            last_err = f"Gemini API returned {resp.status_code}: {resp.text[:500]}"
            continue

        try:
            data = resp.json()
            raw = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw)
            return schema_model.model_validate(parsed)
        except (KeyError, IndexError, json.JSONDecodeError, ValidationError) as e:
            last_err = str(e)
            continue

    raise LLMJSONError(
        f"Failed to get valid JSON from Gemini matching {schema_model.__name__} after "
        f"{max_retries + 1} attempts: {last_err}"
    )
