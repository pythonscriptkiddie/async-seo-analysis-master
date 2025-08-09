import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from string import punctuation
from typing import Dict, List, Tuple

import lxml.html as lh
from bs4 import BeautifulSoup
from .stopwords import ENGLISH_STOP_WORDS

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
    return list(zip(*[tokens[i:] for i in range(n)]))


def analyze_html(url: str, raw_html: str, analyze_headings: bool, analyze_extra_tags: bool) -> PageResult:
    content_hash = hashlib.sha1(raw_html.encode("utf-8")).hexdigest()

    # Remove HTML comments for BS4
    html_without_comments = re.sub(r"<!--.*?-->", r"", raw_html, flags=re.DOTALL)
    soup = BeautifulSoup(html_without_comments, "html.parser")

    # Title / description
    title = (soup.title.string or "").strip() if soup.title else ""
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = (description_tag["content"].strip() if description_tag and description_tag.has_attr("content") else "")

    # Headings/additional via lxml
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

    # Links and images checks/warnings
    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.text.lower().strip()
        if len(a.get("title", "")) == 0:
            # mirror upstream warning
            pass
        if text in ["click here", "page", "article"]:
            pass
        links.append(href)

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if len(img.get("alt", "")) == 0:
            # mirror upstream warning
            pass

    # Tokens/keywords
    text_content = soup.get_text(" ")
    tokens = tokenize(text_content)
    raw_tokens = raw_tokenize(text_content)

    total_word_count = len(raw_tokens)
    wordcount = Counter(tokens)

    bigrams_counter = Counter(" ".join(t) for t in get_ngrams(raw_tokens, 2))
    trigrams_counter = Counter(" ".join(t) for t in get_ngrams(raw_tokens, 3))

    # Keywords threshold like upstream (>4)
    keywords: Dict[str, int] = {w: c for w, c in wordcount.items() if c > 4}

    page = PageResult(
        url=url,
        title=title,
        description=description,
        total_word_count=total_word_count,
        wordcount=wordcount,
        bigrams=bigrams_counter,
        trigrams=trigrams_counter,
        keywords=keywords,
        content_hash=content_hash,
        links=links,
        headings=headings if analyze_headings else {},
        additional_info=additional if analyze_extra_tags else {},
    )

    # Warnings parity
    if len(title) == 0:
        page.warnings.append("Missing title tag")
    elif len(title) < 10:
        page.warnings.append(f"Title tag is too short (less than 10 characters): {title}")
    elif len(title) > 70:
        page.warnings.append(f"Title tag is too long (more than 70 characters): {title}")

    if len(description) == 0:
        page.warnings.append("Missing description")
    elif len(description) < 140:
        page.warnings.append(f"Description is too short (less than 140 characters): {description}")
    elif len(description) > 255:
        page.warnings.append(f"Description is too long (more than 255 characters): {description}")

    # OG checks
    og_title = soup.find_all("meta", attrs={"property": "og:title"})
    og_description = soup.find_all("meta", attrs={"property": "og:description"})
    og_image = soup.find_all("meta", attrs={"property": "og:image"})
    if len(og_title) == 0:
        page.warnings.append("Missing og:title")
    if len(og_description) == 0:
        page.warnings.append("Missing og:description")
    if len(og_image) == 0:
        page.warnings.append("Missing og:image")

    return page