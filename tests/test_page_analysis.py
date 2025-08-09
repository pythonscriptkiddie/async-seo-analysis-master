import pytest

from async_seo_analyzer.page_analysis import tokenize, get_ngrams, analyze_html


def test_tokenize_basic():
    text = "This is a simple example domain page"
    tokens = tokenize(text)
    assert "example" in tokens
    assert "is" not in tokens  # stopword filtered


def test_get_ngrams():
    tokens = ["a", "b", "c", "d"]
    bigrams = get_ngrams(tokens, 2)
    trigrams = get_ngrams(tokens, 3)
    assert tuple(bigrams[0]) == ("a", "b")
    assert tuple(trigrams[0]) == ("a", "b", "c")


def test_analyze_html_minimal():
    html = """
    <html><head><title>Test Page</title><meta name=\"description\" content=\"Desc\"></head>
    <body>
      <h1>Header</h1>
      <a href=\"/about\" title=\"About\">About</a>
      <img src=\"/x.png\" alt=\"x\" />
      <p>Hello world example domain</p>
    </body></html>
    """
    page = analyze_html("https://example.com/", html, analyze_headings=True, analyze_extra_tags=True)
    d = page.as_dict()
    assert d["title"] == "Test Page"
    assert d["description"] == "Desc"
    assert "h1" in d.get("headings", {})
    assert d["links"][0].startswith("https://example.com")