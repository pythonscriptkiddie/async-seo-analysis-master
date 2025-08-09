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


async def _analyze_crawled_pages(crawled: List[Dict], analyze_headings: bool, analyze_extra_tags: bool) -> List[Dict]:
    tasks = [
        asyncio.to_thread(
            analyze_html, p["url"], p.get("text", ""), analyze_headings, analyze_extra_tags
        )
        for p in crawled
    ]
    results = await asyncio.gather(*tasks)
    return [r.as_dict() for r in results]


def analyze(
    url: str,
    sitemap_url: str | None = None,
    analyze_headings: bool = False,
    analyze_extra_tags: bool = False,
    follow_links: bool = False,
    max_depth: int = 3,
    concurrency: int = 20,
) -> Dict:
    start = time.time()

    pages: List[Dict]
    if follow_links or sitemap_url:
        crawler = AsyncCrawler(homepage=url, max_depth=max_depth, max_concurrency=concurrency)
        crawled = asyncio.run(crawler.crawl(sitemap_url=sitemap_url))
        pages = asyncio.run(_analyze_crawled_pages(crawled, analyze_headings, analyze_extra_tags))
    else:
        pages = [asyncio.run(_analyze_single_page(url, analyze_headings, analyze_extra_tags))]

    # Aggregate like pyseoanalyzer
    content_hashes = defaultdict(set)
    unigram_counts = Counter()
    bigram_counts = Counter()
    trigram_counts = Counter()

    for p in pages:
        content_hash = p.get("content_hash")
        if content_hash:
            content_hashes[content_hash].add(p.get("url", ""))
        # per-page wordcount/bigrams/trigrams
        unigram_counts.update(p.get("wordcount", {}))
        bigram_counts.update(p.get("bigrams", {}))
        trigram_counts.update(p.get("trigrams", {}))

    duplicate_pages = [list(v) for v in content_hashes.values() if len(v) > 1]

    # Build site-level keywords list: words and n-grams with count > 4
    keywords: List[Dict] = []
    for w, c in unigram_counts.items():
        if c > 4:
            keywords.append({"word": w, "count": c})
    for w, c in bigram_counts.items():
        if c > 4:
            keywords.append({"word": tuple(w.split(" ")), "count": c})
    for w, c in trigram_counts.items():
        if c > 4:
            keywords.append({"word": tuple(w.split(" ")), "count": c})
    keywords.sort(key=lambda x: x["count"], reverse=True)

    result: Dict = {
        "pages": pages,
        "duplicate_pages": duplicate_pages,
        "keywords": keywords,
        "errors": [],
        "total_time": _calc_total_time(start),
    }
    return result