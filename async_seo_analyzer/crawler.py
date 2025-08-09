import asyncio
import hashlib
from asyncio import Queue
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Set
from urllib.parse import urlsplit
from xml.dom import minidom

import aiohttp
from bs4 import BeautifulSoup

from .utils import rel_to_abs_url, retry


@dataclass
class WorkItem:
    depth: int
    url: str


class AsyncCrawler:
    def __init__(
        self,
        homepage: str,
        max_depth: int = 3,
        max_concurrency: int = 20,
        include_text: bool = True,
        include_links: bool = True,
        include_images: bool = True,
        user_agent: str = "Mozilla/5.0",
    ) -> None:
        self.homepage = homepage
        self.max_depth = max_depth
        self.max_concurrency = max_concurrency
        self.include_text = include_text
        self.include_links = include_links
        self.include_images = include_images
        self.headers = {"User-Agent": user_agent}

        self.crawled_urls: Set[str] = set()
        self.pages: List[Dict] = []

    @property
    def base_netloc(self) -> str:
        return urlsplit(self.homepage).netloc

    async def _fetch(self, session: aiohttp.ClientSession, url: str) -> tuple[str, str]:
        async def do_get():
            return await session.get(url)

        try:
            response = await retry(lambda: do_get(), max_retries=3, timeout=10.0, retry_interval=1.5)
            text = await response.text()
            return str(response.url), text
        except Exception:
            return url, ""

    def _parse(self, url: str, html: str) -> Dict:
        soup = BeautifulSoup(html, "lxml")
        result: Dict = {"url": url}

        if self.include_text:
            result["text"] = html

        if self.include_images:
            images = [
                {
                    "src": (img.get("src") or "") + (img.get("data-src") or ""),
                    "class": img.get("class", ""),
                    "alt": img.get("alt", ""),
                }
                for img in soup.find_all("img")
            ]
            result["images"] = images

        if self.include_links:
            raw_links = soup.find_all("a", href=True)
            links = [
                {
                    "href": rel_to_abs_url(link=a["href"], base_domain=self.homepage, url=url),
                    "text": a.text.lower().strip(),
                    "title": a.get("title", ""),
                }
                for a in raw_links
            ]
            result["links"] = links

        # content hash of raw HTML for deduping
        result["content_hash"] = hashlib.sha1(html.encode("utf-8")).hexdigest() if html else ""
        return result

    async def crawl(self, sitemap_url: str | None = None) -> List[Dict]:
        queue: Queue[WorkItem] = Queue()
        await queue.put(WorkItem(depth=0, url=self.homepage))

        # seed sitemap
        async with aiohttp.ClientSession(headers=self.headers) as session:
            if sitemap_url:
                try:
                    resp = await session.get(sitemap_url)
                    body = await resp.text()
                    if sitemap_url.endswith("xml"):
                        xmldoc = minidom.parseString(body.encode("utf-8"))
                        for node in xmldoc.getElementsByTagName("loc"):
                            text = "".join(n.data for n in node.childNodes if n.nodeType == n.TEXT_NODE)
                            await queue.put(WorkItem(depth=0, url=text))
                    elif sitemap_url.endswith("txt"):
                        for line in body.splitlines():
                            if line.strip():
                                await queue.put(WorkItem(depth=0, url=line.strip()))
                except Exception:
                    pass

            sem = asyncio.Semaphore(self.max_concurrency)

            async def worker() -> None:
                while True:
                    item = await queue.get()
                    if item.url in self.crawled_urls:
                        queue.task_done()
                        continue

                    self.crawled_urls.add(item.url)
                    async with sem:
                        url, html = await self._fetch(session, item.url)

                    if not html:
                        queue.task_done()
                        continue

                    page_result = self._parse(url, html)
                    self.pages.append(page_result)

                    if item.depth < self.max_depth and self.include_links:
                        for link in page_result.get("links", []):
                            href = link.get("href", "")
                            if href and urlsplit(href).netloc == self.base_netloc and href not in self.crawled_urls:
                                await queue.put(WorkItem(depth=item.depth + 1, url=href))

                    queue.task_done()

            workers = [asyncio.create_task(worker()) for _ in range(self.max_concurrency)]
            await queue.join()
            for w in workers:
                w.cancel()

        return self.pages