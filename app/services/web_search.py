"""Shared web search helper: free, no-API-key search used to ground
research_planner's LLM output in real retrieved text.

Tries two free sources, in order, and returns the first that finds anything:

1. DuckDuckGo Instant Answer API (https://duckduckgo.com/api) -- mostly
   returns a short "Abstract" for well-known entities/topics (similar to a
   Wikipedia summary) and frequently returns nothing for niche, very
   specific, or compound queries.
2. Wikipedia REST API (search + page summary, both free/keyless) -- broader
   coverage than DuckDuckGo's instant answers (anything with a Wikipedia
   article, not just "well-known enough for an instant answer"), tried only
   when DuckDuckGo finds nothing.

A None result from search_web() is still the normal/expected case for many
(very niche/invented/compound) topics, not an error -- callers must degrade
gracefully exactly as before this fallback was added.

A paid search API (Google Custom Search, Bing, Serper, Tavily, ...) would
return real ranked web results for arbitrary queries and could materially
improve research grounding further. Not implemented here (see PROGRESS.md).
"""

import requests
from loguru import logger

from app.config import config
from app.models.web_search import WebSearchResult

_DUCKDUCKGO_URL = "https://api.duckduckgo.com/"
_WIKIPEDIA_SEARCH_URL = "https://{lang}.wikipedia.org/w/rest.php/v1/search/page"
_WIKIPEDIA_SUMMARY_URL = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
_WIKIPEDIA_SUPPORTED_LANGUAGES = {"tr", "en"}
_TIMEOUT = (5, 10)  # (connect, read) seconds
# Wikimedia's API etiquette policy rejects requests with no/generic User-Agent
# (the default "python-requests/x.y" gets a real 403 Forbidden, confirmed with
# a live call during development -- this isn't a defensive guess).
_WIKIPEDIA_HEADERS = {
    "User-Agent": "AIDocumentaryStudio/1.0 (research-grounding fallback; "
    "https://github.com/ukaya17-jpg/AI-Documentary-Studio)"
}


def _search_duckduckgo(query: str) -> WebSearchResult | None:
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


def _search_wikipedia(query: str, language: str) -> WebSearchResult | None:
    lang = language if language in _WIKIPEDIA_SUPPORTED_LANGUAGES else "en"

    try:
        search_response = requests.get(
            _WIKIPEDIA_SEARCH_URL.format(lang=lang),
            params={"q": query, "limit": 1},
            headers=_WIKIPEDIA_HEADERS,
            proxies=config.proxy,
            verify=config.app.get("tls_verify", True),
            timeout=_TIMEOUT,
        )
        search_response.raise_for_status()
        pages = search_response.json().get("pages", [])
        if not pages:
            logger.info(f"web_search: no Wikipedia page match for query={query!r}")
            return None
        title = str(pages[0].get("key") or pages[0].get("title") or "").strip()
        if not title:
            return None

        summary_response = requests.get(
            _WIKIPEDIA_SUMMARY_URL.format(lang=lang, title=title),
            headers=_WIKIPEDIA_HEADERS,
            proxies=config.proxy,
            verify=config.app.get("tls_verify", True),
            timeout=_TIMEOUT,
        )
        summary_response.raise_for_status()
        data = summary_response.json()
    except Exception as e:
        logger.warning(f"web_search: Wikipedia request failed for query={query!r}: {e}")
        return None

    extract = str(data.get("extract", "")).strip()
    if not extract:
        return None

    source_url = str(data.get("content_urls", {}).get("desktop", {}).get("page", "")).strip()
    return WebSearchResult(
        heading=str(data.get("title", "")).strip(),
        abstract=extract,
        source_url=source_url,
    )


def search_web(query: str, language: str = "") -> WebSearchResult | None:
    query = (query or "").strip()
    if not query:
        return None

    result = _search_duckduckgo(query)
    if result:
        return result

    return _search_wikipedia(query, language)
