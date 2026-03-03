# lib/tavily_tool.py
"""Tavily web-lookup tool. Used ONLY as a strict, controller-triggered fallback.

Allowlisted domains: hasil.gov.my only.
Allowlisted URLs per topic:
  - DTA_COUNTRY_LIST      → comprehensive DTAs page
  - PUBLIC_RULING_UPDATE  → public rulings page
  - FILING_DEADLINE_CHANGE → both pages
"""
from __future__ import annotations

import os
from typing import Any

from tavily import TavilyClient

ALLOWED_DOMAIN = "hasil.gov.my"

TAVILY_URLS: dict[str, list[str]] = {
    "DTA_COUNTRY_LIST": [
        "https://www.hasil.gov.my/en/international/double-taxation-avoidance-agreement-dtadtaa/comprehensive-dtas/",
    ],
    "PUBLIC_RULING_UPDATE": [
        "https://www.hasil.gov.my/en/legislation/public-rulings/",
    ],
    "FILING_DEADLINE_CHANGE": [
        "https://www.hasil.gov.my/en/legislation/public-rulings/",
        "https://www.hasil.gov.my/en/international/double-taxation-avoidance-agreement-dtadtaa/comprehensive-dtas/",
    ],
}

ALLOWED_TOPICS = frozenset(TAVILY_URLS.keys())
MAX_RESULTS = 5


def official_web_lookup(query: str, topic: str) -> dict[str, Any]:
    """Search LHDN official pages via Tavily for the given topic.

    Args:
        query: Natural-language search query.
        topic: One of DTA_COUNTRY_LIST | PUBLIC_RULING_UPDATE | FILING_DEADLINE_CHANGE.

    Returns:
        { source: "tavily", topic: str, results: list[dict] }

    Raises:
        ValueError: If topic is not in ALLOWED_TOPICS.
    """
    if topic not in ALLOWED_TOPICS:
        raise ValueError(f"Invalid topic '{topic}'. Must be one of {sorted(ALLOWED_TOPICS)}")

    client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))

    raw = client.search(
        query=query,
        include_domains=[ALLOWED_DOMAIN],
        max_results=MAX_RESULTS * 2,  # fetch more; we'll filter + cap
    )

    raw_results: list[dict] = raw.get("results") or []

    # Enforce URL allowlist: only hasil.gov.my
    filtered = [r for r in raw_results if ALLOWED_DOMAIN in r.get("url", "")]

    # Cap at MAX_RESULTS
    filtered = filtered[:MAX_RESULTS]

    results = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
            **({"publishedDate": r["published_date"]} if r.get("published_date") else {}),
        }
        for r in filtered
    ]

    return {
        "source": "tavily",
        "topic": topic,
        "results": results,
    }
