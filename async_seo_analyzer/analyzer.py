import asyncio
import time
import hashlib
from collections import Counter, defaultdict
from typing import Dict, List
from urllib.parse import urlsplit

import aiohttp
from bs4 import BeautifulSoup
import trafilatura

from .crawler import AsyncCrawler
from .utils import rel_to_abs_url

TOKEN_REGEX = r"(?u)\b\w\w+\b"


def _calc_total_time(start_time: float) -> float:
    return time.time() - start_time


async def _fetch_text(session: aiohttp.ClientSession, url: str, timeout: float = 10.0) -> tuple[str, dict[str, str]]:
    async with session.get(url, timeout=timeout) as resp:
        text = await resp.text()
        return text, {k.lower(): v for k, v in resp.headers.items()}


def _tokenize(text: str) -> List[str]:
    import re

    return [w for w in re.findall(TOKEN_REGEX, text.lower())]


def _basic_keywords(tokens: List[str]) -> List[Dict]:
    counts = Counter(tokens)
    result: List[Dict] = []
    for word, cnt in counts.items():
        if cnt > 4:
            result.append({"word": word, "count": cnt})
    result.sort(key=lambda x: x["count"], reverse=True)
    return result


async def _analyze_single_page(url: str, analyze_headings: bool, analyze_extra_tags: bool) -> Dict:
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        raw_html, headers = await _fetch_text(session, url)

    content_hash = hashlib.sha1(raw_html.encode("utf-8")).hexdigest()

    metadata = trafilatura.extract_metadata(filecontent=raw_html, default_url=url, extensive=True)
    metadata_dict = metadata.as_dict() if metadata else {}

    def mget(key: str) -> str:
        val = metadata_dict.get(key)
        return "" if val is None or val == "None" else val

    title = mget("title")
    description = mget("description")
    sitename = mget("sitename")
    hostname = mget("hostname")
    date = mget("date")

    extracted = trafilatura.extract(
        raw_html,
        include_links=True,
        include_formatting=False,
        include_tables=True,
        include_images=True,
        output_format="json",
    )
    text_content = ""
    if extracted:
        import json

        try:
            text_content = json.loads(extracted).get("text", "")
        except Exception:
            text_content = ""

    soup = BeautifulSoup(raw_html, "html.parser")

    links: List[str] = []
    for a in soup.find_all("a", href=True):
        abs_link = rel_to_abs_url(a["href"], base_domain=url, url=url)
        if abs_link not in links:
            links.append(abs_link)

    warnings: List[str] = []
    if len(title) == 0:
        warnings.append("Missing title tag")
    elif len(title) < 10:
        warnings.append(f"Title tag is too short (less than 10 characters): {title}")
    elif len(title) > 70:
        warnings.append(f"Title tag is too long (more than 70 characters): {title}")

    if len(description) == 0:
        warnings.append("Missing description")
    elif len(description) < 140:
        warnings.append(f"Description is too short (less than 140 characters): {description}")
    elif len(description) > 255:
        warnings.append(f"Description is too long (more than 255 characters): {description}")

    tokens = _tokenize(text_content)
    total_word_count = len(tokens)

    page_dict: Dict = {
        "url": url,
        "title": title,
        "description": description,
        "author": "",
        "hostname": hostname,
        "sitename": sitename,
        "date": date,
        "word_count": total_word_count,
        "keywords": [],
        "bigrams": {},
        "trigrams": {},
        "warnings": warnings,
        "content_hash": content_hash,
        "links": links,
    }

    if analyze_headings:
        headings: Dict[str, List[str]] = {}
        for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            values = [h.get_text(strip=True) for h in soup.find_all(tag)]
            if values:
                headings[tag] = values
        page_dict["headings"] = headings

    if analyze_extra_tags:
        addl = {
            "title": [title] if title else [],
            "meta_desc": [description] if description else [],
        }
        page_dict["additional_info"] = addl

    return page_dict


def analyze(
    url: str,
    sitemap_url: str | None = None,
    analyze_headings: bool = False,
    analyze_extra_tags: bool = False,
    follow_links: bool = False,
) -> Dict:
    start = time.time()

    pages: List[Dict]
    if follow_links or sitemap_url:
        crawler = AsyncCrawler(homepage=url, max_depth=3, max_concurrency=20)
        pages = asyncio.run(crawler.crawl(sitemap_url=sitemap_url))
    else:
        pages = [asyncio.run(_analyze_single_page(url, analyze_headings, analyze_extra_tags))]

    # Aggregate like pyseoanalyzer
    wordcount = Counter()
    bigrams = Counter()
    trigrams = Counter()
    content_hashes = defaultdict(set)

    for p in pages:
        # simple tokenization from page text fallback
        tokens = _tokenize(((p.get("title") or "") + " " + (p.get("description") or "")))
        wordcount.update(tokens)
        content_hash = p.get("content_hash")
        if content_hash:
            content_hashes[content_hash].add(p.get("url", ""))

    duplicate_pages = [list(v) for v in content_hashes.values() if len(v) > 1]

    keywords = _basic_keywords(list(wordcount.elements()))

    result: Dict = {
        "pages": pages,
        "duplicate_pages": duplicate_pages,
        "keywords": keywords,
        "errors": [],
        "total_time": _calc_total_time(start),
    }
    return result