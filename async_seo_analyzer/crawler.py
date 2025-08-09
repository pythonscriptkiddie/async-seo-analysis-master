import asyncio
import hashlib
import ssl
import certifi
from asyncio import Queue
from dataclasses import dataclass
from typing import Dict, List, Set
from urllib.parse import urlsplit
from xml.dom import minidom
import urllib.robotparser as robotparser

import aiohttp
from aiohttp import TCPConnector
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
        self.user_agent = user_agent
        self.headers = {"User-Agent": user_agent}

        self.crawled_urls: Set[str] = set()
        self.pages: List[Dict] = []

        self._robots: robotparser.RobotFileParser | None = None
        self._crawl_delay: float = 0.0

    @property
    def base_netloc(self) -> str:
        return urlsplit(self.homepage).netloc

    @property
    def base_scheme(self) -> str:
        return urlsplit(self.homepage).scheme or "https"

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

        result["content_hash"] = hashlib.sha1(html.encode("utf-8")).hexdigest() if html else ""
        return result

    async def _load_robots(self, session: aiohttp.ClientSession) -> None:
        robots_url = f"{self.base_scheme}://{self.base_netloc}/robots.txt"
        try:
            resp = await session.get(robots_url)
            if resp.status >= 400:
                self._robots = None
                self._crawl_delay = 0.0
                return
            body = await resp.text()
            rp = robotparser.RobotFileParser()
            rp.parse(body.splitlines())
            self._robots = rp
            delay = rp.crawl_delay(self.user_agent)
            if delay is None:
                delay = rp.crawl_delay("*")
            self._crawl_delay = float(delay) if delay else 0.0
        except Exception:
            self._robots = None
            self._crawl_delay = 0.0

    def _allowed_by_robots(self, url: str) -> bool:
        if not self._robots:
            return True
        try:
            allowed = self._robots.can_fetch(self.user_agent, url)
            if allowed is None:
                return True
            return bool(allowed)
        except Exception:
            return True

    async def crawl(self, sitemap_url: str | None = None) -> List[Dict]:
        queue: Queue[WorkItem] = Queue()
        await queue.put(WorkItem(depth=0, url=self.homepage))

        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        connector = TCPConnector(ssl=ssl_ctx)
        async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
            await self._load_robots(session)

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

                    if not self._allowed_by_robots(item.url):
                        queue.task_done()
                        continue

                    self.crawled_urls.add(item.url)
                    async with sem:
                        if self._crawl_delay:
                            await asyncio.sleep(self._crawl_delay)
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
                                if self._allowed_by_robots(href):
                                    await queue.put(WorkItem(depth=item.depth + 1, url=href))

                    queue.task_done()

            workers = [asyncio.create_task(worker()) for _ in range(self.max_concurrency)]
            await queue.join()
            for w in workers:
                w.cancel()

        return self.pages