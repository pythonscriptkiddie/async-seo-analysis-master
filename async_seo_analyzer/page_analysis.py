import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from string import punctuation
from typing import Dict, List, Tuple

import lxml.html as lh
from bs4 import BeautifulSoup
from urllib.parse import urlsplit
import trafilatura
import numpy as np
from .stopwords import ENGLISH_STOP_WORDS
from .utils import rel_to_abs_url

TOKEN_REGEX = re.compile(r"(?u)\b\w\w+\b")

HEADING_TAGS_XPATHS = {
    "h1": "//h1",
    "h2": "//h2",
    "h3": "//h3",
    "h4": "//h4",
    "h5": "//h5",
    "h6": "//h6",
}

ADDITIONAL_TAGS_XPATHS = {
    "title": "//title/text()",
    "meta_desc": "//meta[@name='description']/@content",
    "viewport": "//meta[@name='viewport']/@content",
    "charset": "//meta[@charset]/@charset",
    "canonical": "//link[@rel='canonical']/@href",
    "alt_href": "//link[@rel='alternate']/@href",
    "alt_hreflang": "//link[@rel='alternate']/@hreflang",
    "og_title": "//meta[@property='og:title']/@content",
    "og_desc": "//meta[@property='og:description']/@content",
    "og_url": "//meta[@property='og:url']/@content",
    "og_image": "//meta[@property='og:image']/@content",
}

IMAGE_EXTENSIONS = {".img", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp", ".avif"}


@dataclass
class PageResult:
    url: str
    title: str = ""
    description: str = ""
    author: str = ""
    hostname: str = ""
    sitename: str = ""
    date: str = ""
    total_word_count: int = 0
    wordcount: Counter = field(default_factory=Counter)
    bigrams: Counter = field(default_factory=Counter)
    trigrams: Counter = field(default_factory=Counter)
    keywords: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    content_hash: str = ""
    links: List[str] = field(default_factory=list)
    headings: Dict[str, List[str]] = field(default_factory=dict)
    additional_info: Dict[str, List[str]] = field(default_factory=dict)

    def as_dict(self) -> Dict:
        result = {
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "author": self.author,
            "hostname": self.hostname,
            "sitename": self.sitename,
            "date": self.date,
            "word_count": self.total_word_count,
            "keywords": sorted(
                [(self.keywords[k], k) for k in self.keywords if self.keywords[k] > 0],
                reverse=True,
            )[:5],
            "bigrams": dict(self.bigrams),
            "trigrams": dict(self.trigrams),
            "warnings": self.warnings,
            "content_hash": self.content_hash,
            "links": self.links,
            "wordcount": dict(self.wordcount),
        }
        if self.headings:
            result["headings"] = self.headings
        if self.additional_info:
            result["additional_info"] = self.additional_info
        return result


def tokenize(rawtext: str) -> List[str]:
    return [word for word in TOKEN_REGEX.findall(rawtext.lower()) if word not in ENGLISH_STOP_WORDS]


def raw_tokenize(rawtext: str) -> List[str]:
    return TOKEN_REGEX.findall(rawtext.lower())


def get_ngrams(tokens: List[str], n: int) -> List[Tuple[str, ...]]:
    if len(tokens) < n:
        return []
    arr = np.array(tokens, dtype=object)
    windows = np.lib.stride_tricks.sliding_window_view(arr, window_shape=n)
    return [tuple(row.tolist()) for row in windows]


def analyze_html(url: str, raw_html: str, analyze_headings: bool, analyze_extra_tags: bool) -> PageResult:
    content_hash = hashlib.sha1(raw_html.encode("utf-8")).hexdigest()

    html_without_comments = re.sub(r"<!--.*?-->", r"", raw_html, flags=re.DOTALL)
    soup = BeautifulSoup(html_without_comments, "html.parser")

    metadata = trafilatura.extract_metadata(filecontent=raw_html, default_url=url, extensive=True)
    md = metadata.as_dict() if metadata else {}

    def mget(key: str) -> str:
        v = md.get(key)
        return "" if (v is None or v == "None") else v

    title = (soup.title.string or "").strip() if soup.title else mget("title")
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = (
        (description_tag["content"].strip() if description_tag and description_tag.has_attr("content") else "")
        or mget("description")
    )

    author = mget("author")
    hostname = mget("hostname")
    sitename = mget("sitename")
    date = mget("date")

    if analyze_headings or analyze_extra_tags:
        try:
            dom = lh.fromstring(html_without_comments)
        except ValueError:
            dom = lh.fromstring(html_without_comments.encode("utf-8"))

    headings: Dict[str, List[str]] = {}
    additional: Dict[str, List[str]] = {}

    if analyze_headings:
        for tag, xpath in HEADING_TAGS_XPATHS.items():
            values = [h.text_content() for h in dom.xpath(xpath)]
            if values:
                headings[tag] = values

    if analyze_extra_tags:
        for tag, xpath in ADDITIONAL_TAGS_XPATHS.items():
            values = dom.xpath(xpath)
            if values:
                additional[tag] = values

    links_set = set()
    base = urlsplit(url)

    def is_internal(abs_url: str) -> bool:
        return urlsplit(abs_url).netloc == base.netloc

    for a in soup.find_all("a", href=True):
        abs_link = rel_to_abs_url(a["href"], base_domain=url, url=url)
        if not is_internal(abs_link):
            continue
        if "#" in abs_link:
            abs_link = abs_link[: abs_link.rindex("#")]
        links_set.add(abs_link)

    image_warnings: List[str] = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if len(img.get("alt", "")) == 0:
            image_warnings.append(f"Image missing alt tag: {src}")

    links = sorted(list(links_set))

    text_content = soup.get_text(" ")
    tokens = tokenize(text_content)
    raw_tokens = raw_tokenize(text_content)

    total_word_count = len(raw_tokens)
    wordcount = Counter(tokens)

    bigrams_counter = Counter(" ".join(t) for t in get_ngrams(raw_tokens, 2))
    trigrams_counter = Counter(" ".join(t) for t in get_ngrams(raw_tokens, 3))

    keywords: Dict[str, int] = {w: c for w, c in wordcount.items() if c > 4}

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

    og_title = soup.find_all("meta", attrs={"property": "og:title"})
    og_description = soup.find_all("meta", attrs={"property": "og:description"})
    og_image = soup.find_all("meta", attrs={"property": "og:image"})
    if len(og_title) == 0:
        warnings.append("Missing og:title")
    if len(og_description) == 0:
        warnings.append("Missing og:description")
    if len(og_image) == 0:
        warnings.append("Missing og:image")

    meta_keywords = soup.find("meta", attrs={"name": "keywords"})
    if meta_keywords and meta_keywords.get("content", "").strip():
        warnings.append(
            "Keywords should be avoided as they are a spam indicator and no longer used by Search Engines"
        )

    # Anchor warnings (title/generic text)
    for a in soup.find_all("a", href=True):
        abs_link = rel_to_abs_url(a["href"], base_domain=url, url=url)
        if not is_internal(abs_link):
            continue
        if "#" in abs_link:
            abs_link = abs_link[: abs_link.rindex("#")]
        if len(a.get("title", "")) == 0:
            warnings.append(f"Anchor missing title tag: {abs_link}")
        text = a.text.lower().strip()
        if text in ["click here", "page", "article"]:
            warnings.append(f"Anchor text contains generic text: {text}")

    warnings.extend(image_warnings)

    # H1 presence warning (parity)
    if soup.find_all("h1") == []:
        warnings.append("Each page should have at least one h1 tag")

    page = PageResult(
        url=url,
        title=title,
        description=description,
        author=author,
        hostname=hostname,
        sitename=sitename,
        date=date,
        total_word_count=total_word_count,
        wordcount=wordcount,
        bigrams=bigrams_counter,
        trigrams=trigrams_counter,
        keywords=keywords,
        content_hash=content_hash,
        links=links,
        headings=headings if analyze_headings else {},
        additional_info=additional if analyze_extra_tags else {},
        warnings=warnings,
    )

    return page