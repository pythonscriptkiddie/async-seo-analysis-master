import json
import pytest

from async_seo_analyzer import analyze


@pytest.mark.timeout(20)
def test_single_page_example_com():
    result = analyze("https://example.com")
    assert "pages" in result and isinstance(result["pages"], list)
    assert result["pages"][0]["url"].startswith("https://example.com")
    assert result["total_time"] >= 0


@pytest.mark.timeout(30)
def test_follow_links_shallow():
    # Shallow crawl to keep test fast
    result = analyze("https://example.com", follow_links=True, max_depth=1, workers=2)
    assert "pages" in result
    assert len(result["pages"]) >= 1
    assert "crawl_metrics" in result
    assert result["crawl_metrics"]["pages"] >= 1