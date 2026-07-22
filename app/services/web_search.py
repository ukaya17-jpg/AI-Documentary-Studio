"""Shared web search helper: a free, no-API-key search used to ground
research_planner's LLM output in real retrieved text.

Uses the DuckDuckGo Instant Answer API (https://duckduckgo.com/api), which is
free and requires no API key. It is NOT a general web search API: it mostly
returns a short "Abstract" for well-known entities/topics (similar to a
Wikipedia summary) and frequently returns nothing for niche, very specific,
or compound queries. A None result is the normal/expected case for many
topics, not an error -- callers must degrade gracefully.

A paid search API (Google Custom Search, Bing, Serper, Tavily, ...) would
return real ranked web results for arbitrary queries and could materially
improve research grounding. Not implemented here (see PROGRESS.md).
"""

import requests
from loguru import logger

from app.config import config
from app.models.web_search import WebSearchResult

_DUCKDUCKGO_URL = "https://api.duckduckgo.com/"
_TIMEOUT = (5, 10)  # (connect, read) seconds


def search_web(query: str) -> WebSearchResult | None:
    query = (query or "").strip()
    if not query:
        return None

    try:
        response = requests.get(
            _DUCKDUCKGO_URL,
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            proxies=config.proxy,
            verify=config.app.get("tls_verify", True),
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.warning(f"web_search: DuckDuckGo request failed for query={query!r}: {e}")
        return None

    abstract = str(data.get("AbstractText", "")).strip()
    if not abstract:
        logger.info(f"web_search: no instant-answer abstract for query={query!r}")
        return None

    return WebSearchResult(
        heading=str(data.get("Heading", "")).strip(),
        abstract=abstract,
        source_url=str(data.get("AbstractURL", "")).strip(),
    )
