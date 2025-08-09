import asyncio
import time
import hashlib
from collections import Counter, defaultdict
from typing import Dict, List

import ssl
import certifi
import aiohttp
from aiohttp import TCPConnector

from .crawler import AsyncCrawler
from .page_analysis import analyze_html


def _calc_total_time(start_time: float) -> float:
    return time.time() - start_time


async def _fetch_text(session: aiohttp.ClientSession, url: str, timeout: float = 10.0) -> tuple[str, dict[str, str]]:
    async with session.get(url, timeout=timeout) as resp:
        text = await resp.text()
        return text, {k.lower(): v for k, v in resp.headers.items()}


async def _analyze_single_page(url: str, analyze_headings: bool, analyze_extra_tags: bool) -> Dict:
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    connector = TCPConnector(ssl=ssl_ctx)
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}, connector=connector) as session:
        raw_html, _ = await _fetch_text(session, url)

    page = analyze_html(url, raw_html, analyze_headings, analyze_extra_tags)
    return page.as_dict()


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
        crawled = asyncio.run(crawler.crawl(sitemap_url=sitemap_url))
        # crawled pages have raw HTML and links; re-analyze for parity
        pages = [
            analyze_html(p["url"], p.get("text", ""), analyze_headings, analyze_extra_tags).as_dict()
            for p in crawled
        ]
    else:
        pages = [asyncio.run(_analyze_single_page(url, analyze_headings, analyze_extra_tags))]

    # Aggregate like pyseoanalyzer
    wordcount = Counter()
    content_hashes = defaultdict(set)

    for p in pages:
        # Keywords are embedded per page; global keywords from totals if needed
        for w, c in p.get("keywords", []):
            if isinstance(w, tuple):
                continue
        content_hash = p.get("content_hash")
        if content_hash:
            content_hashes[content_hash].add(p.get("url", ""))

    duplicate_pages = [list(v) for v in content_hashes.values() if len(v) > 1]

    result: Dict = {
        "pages": pages,
        "duplicate_pages": duplicate_pages,
        "keywords": [],
        "errors": [],
        "total_time": _calc_total_time(start),
    }
    return result