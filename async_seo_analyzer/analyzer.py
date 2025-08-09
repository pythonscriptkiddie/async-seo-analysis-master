"""Public analyzer API bridging the async crawler and page analysis.

Exports the synchronous `analyze` function which orchestrates crawling (optional)
and per-page analysis, aggregating site-level metrics similar to pyseoanalyzer.
"""

import asyncio
import time
from collections import Counter, defaultdict
from typing import Dict, List

import ssl
import certifi
import aiohttp
from aiohttp import TCPConnector
from concurrent.futures import ThreadPoolExecutor
import os

from .crawler import AsyncCrawler
from .page_analysis import analyze_html


def _calc_total_time(start_time: float) -> float:
    """Compute elapsed time in seconds given a start timestamp."""
    return time.time() - start_time


async def _fetch_text(session: aiohttp.ClientSession, url: str, timeout: float = 10.0) -> tuple[str, dict[str, str]]:
    """Fetch URL text via aiohttp with a timeout; return (text, headers)."""
    async with session.get(url, timeout=timeout) as resp:
        text = await resp.text()
        return text, {k.lower(): v for k, v in resp.headers.items()}


async def _analyze_single_page(url: str, analyze_headings: bool, analyze_extra_tags: bool, pool: ThreadPoolExecutor) -> Dict:
    """Asynchronously download and analyze a single page using a thread pool."""
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    connector = TCPConnector(ssl=ssl_ctx)
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}, connector=connector) as session:
        raw_html, _ = await _fetch_text(session, url)

    loop = asyncio.get_running_loop()
    page = await loop.run_in_executor(
        pool, analyze_html, url, raw_html, analyze_headings, analyze_extra_tags
    )
    return page.as_dict()


async def _analyze_crawled_pages(crawled: List[Dict], analyze_headings: bool, analyze_extra_tags: bool, pool: ThreadPoolExecutor) -> List[Dict]:
    """Analyze a batch of crawled pages concurrently in a shared thread pool."""
    loop = asyncio.get_running_loop()
    tasks = [
        loop.run_in_executor(
            pool, analyze_html, p["url"], p.get("text", ""), analyze_headings, analyze_extra_tags
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
    workers: int = 0,
) -> Dict:
    """Analyze a site or a single page and return a result dictionary.

    Parameters
    - url: The start URL to analyze.
    - sitemap_url: Optional sitemap URL to seed the crawl.
    - analyze_headings: If True, include h1-h6 extraction.
    - analyze_extra_tags: If True, include additional meta and OG tags.
    - follow_links: If True, crawl internal links up to max_depth.
    - max_depth: Maximum depth for crawling.
    - concurrency: Max number of concurrent fetches.
    - workers: Thread pool size for CPU-bound tasks (0 = auto cpu_count).

    Returns
    - A dictionary with pages, duplicate_pages, keywords, errors, total_time,
      and optionally crawl_metrics when crawling.
    """
    start = time.time()

    max_workers = workers if workers and workers > 0 else (os.cpu_count() or 4)
    crawl_metrics = None
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        if follow_links or sitemap_url:
            crawler = AsyncCrawler(
                homepage=url,
                max_depth=max_depth,
                max_concurrency=concurrency,
                cpu_workers=max_workers,
            )
            crawled = asyncio.run(crawler.crawl(sitemap_url=sitemap_url))
            crawl_metrics = crawler.metrics
            pages = asyncio.run(_analyze_crawled_pages(crawled, analyze_headings, analyze_extra_tags, pool))
        else:
            pages = [asyncio.run(_analyze_single_page(url, analyze_headings, analyze_extra_tags, pool))]

        content_hashes = defaultdict(set)
        unigram_counts = Counter()
        bigram_counts = Counter()
        trigram_counts = Counter()

        def accumulate(page: Dict) -> tuple[Counter, Counter, Counter, str, str]:
            return (
                Counter(page.get("wordcount", {})),
                Counter(page.get("bigrams", {})),
                Counter(page.get("trigrams", {})),
                page.get("content_hash", ""),
                page.get("url", ""),
            )

        futures = [pool.submit(accumulate, p) for p in pages]
        for fut in futures:
            u, b, t, ch, uurl = fut.result()
            unigram_counts.update(u)
            bigram_counts.update(b)
            trigram_counts.update(t)
            if ch:
                content_hashes[ch].add(uurl)

        duplicate_pages = [list(v) for v in content_hashes.values() if len(v) > 1]

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
    if crawl_metrics is not None:
        result["crawl_metrics"] = crawl_metrics
    return result