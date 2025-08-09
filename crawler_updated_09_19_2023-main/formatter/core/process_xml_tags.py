from typing import Dict
import lxml.html as lh

def title_desc_additional_tags(text: str):
    '''Analyze the heading tags and populate the headings'''
    ADDITIONAL_TAGS_XPATHS: Dict = {'title': '//title/text()',
        'meta_desc': '//meta[@name="description"]/@content',
        'keywords_tag': '//meta[@name="keywords"]/@content',
        'viewport': '//meta[@name="viewport"]/@content',
        'charset': '//meta[@charset]/@charset',
        'canonical': '//link[@rel="canonical"]/@href',
        'alt_href': '//link[@rel="alternate"]/@href',
        'alt_hreflang': '//link[@rel="alternate"]/@hreflang'}
    headings: Dict = {}
    try:
        dom = lh.fromstring(text)
    except ValueError as _:
        dom = lh.fromstring(text).encode('utf-8')
    for tag, xpath in ADDITIONAL_TAGS_XPATHS.items():
        value = dom.xpath(xpath)
        if value:
            headings.update({tag: value})
    return headings

def analyze_heading_tags(text: str):
    '''Analyze the heading tags and populate the headings'''
    HEADING_TAGS_XPATHS = {f'h{i}': f'//h{i}' for i in range(1, 7)}
    headings: Dict = {}
    try:
        dom = lh.fromstring(text)
    except ValueError as _:
        dom = lh.fromstring(text).encode('utf-8')
    for tag, xpath in HEADING_TAGS_XPATHS.items():
        value = [heading.text_content() for heading in dom.xpath(xpath)]
        if value:
            headings.update({tag: value})
    return headings

def analyze_og_tags(text):
    '''Analyze the heading tags and populate the headings. Taken from Seth Black,
    https://github.com/sethblack/python-seo-analyzer/blob/master/seoanalyzer/page.py'''
    OG_TAGS_XPATHS: Dict = {'og:title':"//meta[@property='og:title']/@content",
                        'og:description':"//meta[@property='og:description']/@content",
                        'og:type':"//meta[@property='og:type']/@content",
                        'og:image':"//meta[@property='og:image']/@content",
                        'og:url': "//meta[@property='og:url']/@content"}
    og_tags: Dict = {}
    try:
        dom = lh.fromstring(text)
    except ValueError as _:
        dom = lh.fromstring(text.encode('utf-8'))
    for tag, xpath in OG_TAGS_XPATHS.items():
        try:
            value = dom.xpath(xpath)[0]
        except IndexError:
            value = None
        if value:
            og_tags.update({tag: value})
    return og_tags