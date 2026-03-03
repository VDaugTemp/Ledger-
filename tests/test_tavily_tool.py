"""Tests for official_web_lookup — Tavily calls are mocked."""
import pytest
from unittest.mock import patch, MagicMock
from lib.tavily_tool import official_web_lookup


def _mock_tavily_response(urls=None):
    """Build a fake Tavily response."""
    urls = urls or [
        "https://www.hasil.gov.my/en/legislation/public-rulings/pr-1",
        "https://www.hasil.gov.my/en/legislation/public-rulings/pr-2",
    ]
    return {
        "results": [
            {
                "title": f"Result {i}",
                "url": url,
                "content": f"Content snippet {i}",
                "published_date": "2025-01-15",
            }
            for i, url in enumerate(urls)
        ]
    }


def test_returns_structured_result():
    with patch("lib.tavily_tool.TavilyClient") as MockClient:
        instance = MockClient.return_value
        instance.search.return_value = _mock_tavily_response()
        result = official_web_lookup(query="latest public ruling", topic="PUBLIC_RULING_UPDATE")
    assert result["source"] == "tavily"
    assert result["topic"] == "PUBLIC_RULING_UPDATE"
    assert isinstance(result["results"], list)
    assert len(result["results"]) <= 5


def test_result_structure():
    with patch("lib.tavily_tool.TavilyClient") as MockClient:
        instance = MockClient.return_value
        instance.search.return_value = _mock_tavily_response()
        result = official_web_lookup(query="public rulings", topic="PUBLIC_RULING_UPDATE")
    r = result["results"][0]
    assert "title" in r
    assert "url" in r
    assert "snippet" in r


def test_caps_at_five_results():
    many_urls = [f"https://www.hasil.gov.my/page{i}" for i in range(10)]
    with patch("lib.tavily_tool.TavilyClient") as MockClient:
        instance = MockClient.return_value
        instance.search.return_value = _mock_tavily_response(many_urls)
        result = official_web_lookup(query="DTA list", topic="DTA_COUNTRY_LIST")
    assert len(result["results"]) <= 5


def test_filters_non_hasil_urls():
    mixed_urls = [
        "https://www.hasil.gov.my/en/international/",
        "https://example.com/bad",
        "https://google.com/also-bad",
    ]
    with patch("lib.tavily_tool.TavilyClient") as MockClient:
        instance = MockClient.return_value
        instance.search.return_value = _mock_tavily_response(mixed_urls)
        result = official_web_lookup(query="DTA", topic="DTA_COUNTRY_LIST")
    for r in result["results"]:
        assert "hasil.gov.my" in r["url"]


def test_empty_results_returns_empty_list():
    with patch("lib.tavily_tool.TavilyClient") as MockClient:
        instance = MockClient.return_value
        instance.search.return_value = {"results": []}
        result = official_web_lookup(query="nothing", topic="PUBLIC_RULING_UPDATE")
    assert result["results"] == []


def test_raises_for_invalid_topic():
    with pytest.raises(ValueError, match="Invalid topic"):
        official_web_lookup(query="test", topic="INVALID_TOPIC")
