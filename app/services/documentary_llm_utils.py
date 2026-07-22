"""Shared LLM JSON-generation helper for the documentary pipeline stages.

Wraps ``app.services.llm._generate_response`` (the same core call every other
LLM-backed feature in this app already goes through) with the retry-and-parse
pattern already used by ``generate_script``/``generate_social_metadata``, so
each pipeline stage doesn't reimplement it.
"""

import json
import re

from loguru import logger

from app.services.llm import _generate_response, _strip_code_fence

DEFAULT_MAX_RETRIES = 3


def parse_json_object(response: str) -> dict:
    text = _strip_code_fence(response)
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", response or "", re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


def generate_json(prompt: str, max_retries: int = DEFAULT_MAX_RETRIES) -> dict:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = _generate_response(prompt=prompt)
            data = parse_json_object(response)
            if not isinstance(data, dict):
                raise ValueError("response is not a JSON object")
            return data
        except Exception as e:
            last_error = e
            logger.warning(
                f"documentary pipeline: LLM JSON generation failed "
                f"(attempt {attempt + 1}/{max_retries}): {e}"
            )
    raise ValueError(f"failed to generate valid JSON after {max_retries} attempts: {last_error}")
