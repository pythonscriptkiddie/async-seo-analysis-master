from uuid import UUID, uuid4
import asyncio
import time
import operator
from asyncio import AbstractEventLoop
from typing import List, Dict, Callable, Tuple, Iterable
from functools import partial, reduce
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor
#from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, validator
from .core.content_hash import create_content_hash
from .core.clean_html import create_clean_html
from .core.page_elements import create_title_description
from .core.process_xml_tags import title_desc_additional_tags
from .core.process_xml_tags import analyze_heading_tags
from .core.process_xml_tags import analyze_og_tags
from .core.page_warnings import (make_link_warnings,
           make_image_warnings,
           title_length,
           description_length,
           get_og_tag_warnings,
           keywords_tag_present)
from .core.slug import make_slug
#from formatter.process_text.process_text import create_title
from .process_text.process_text import process_text, create_bigrams_trigrams

class Formatter(BaseModel):
    '''The formatter processes the content after scraping, so that
    any errors can be detected by the analyzer. The processing finds
    and creates the title, description, og_tags and other fields present
    in the text.'''
    unique_id : UUID = Field(default_factory=uuid4)

    async def __process_item(self, items: List[Dict], func: Callable, executor): #async function called every step
        '''A protected method that proceses an item with the designated
        executor.'''
        with executor() as pool:
            loop: AbstractEventLoop = asyncio.get_running_loop()
            calls: List = [partial(func, item) for item in items]
            call_coros = []
            for call in calls:
                call_coros.append(loop.run_in_executor(pool, call))
            return await asyncio.gather(*call_coros)

    async def process_item_threads(self, func, items):
        '''Calls the __process_item method and returns an instance
        of a Formatter with the ThreadPoolExecutor as a executor.'''
        return await self.__process_item(items=items,
                        func=func,
                        executor=ThreadPoolExecutor)
    
    async def process_item_processes(self, func, items):
        '''Calls the __process_item method and returns an instance
        of a Formatter with the ThreadPoolExecutor as a executor.'''
        return await self.__process_item(items=items,
                        func=func,
                        executor=ProcessPoolExecutor)
    
    async def apply_to_iterable(self, items: Iterable, func: Callable):
        '''Applies an asyncronous coroutine to an iterable'''
        funcs: List = [partial(func, item) for item in items]
        tasks: List = [asyncio.create_task(func_with_args()) for func_with_args in funcs]
        return await asyncio.gather(*tasks)

def process_func(element: Dict, new_field: str, existing_field: str,
                func: Callable):
    '''Takes an element of an interable and creates the content hash for it'''
    element[new_field] = func(element[existing_field])
    return element

def process_funcs(element: Dict, new_fields: List[Tuple[str, Callable]], existing_field: str):
    '''Takes an element of an interable and creates the content hash for it'''
    for new_field, func in new_fields:
        element[new_field] = func(element[existing_field])
    return element

#step 1
#step1 partial function
process_content_hash = partial(process_func, new_field='content_hash',
    existing_field='text', func=create_content_hash)

#step 2
process_clean_html = partial(process_func, new_field='text',
    existing_field='text', func=create_clean_html)

process_slug = partial(process_func, new_field='slug',
    existing_field='url', func=make_slug)
#create title description
#process_title_description = partial(process_func, new_field='title_description',
#    existing_field='text', func=create_title_description)

#step 3

#we need to make sure that process_content_hash is called BEFORE process_clean_html
process_bigrams_trigrams_headings = partial(process_funcs,
    new_fields=[('title_description', create_title_description),
                ('soup_bigrams_trigrams', create_bigrams_trigrams),
                ('headings', analyze_heading_tags),
                ('additional_info', title_desc_additional_tags),
                ('og_tags', analyze_og_tags)],
    existing_field='text')

#step4 create bigrams trigrams
#process_bigrams_trigrams = partial(process_func, new_field='soup_bigrams_trigrams',
#    existing_field='text', func=create_bigrams_trigrams)

###---analysis functions start

def get_title(item: Dict):
    '''Takes an item and obtains the title attribute. Only called if the title
    is not present.'''
    try:
        title = item.get('additional_info').get('title')[0]
        #new_item['title'] = (title := item.get('additional_info').get('title')[0])
    except IndexError:
        title = ''
       # new_item['title'] = (title := '')
    finally:
        return title

def get_description(item: Dict):
    '''Takes an item and obtains the description attribute. only called if the
    description is not present'''
    try:
         description = item.get('additional_info').get('meta_desc')[0]
    except IndexError:
        description = ''
    finally:
        return description


async def make_formatted_page(item: Dict) -> Dict:
    '''Takes an unformatted page and creates warning items for that page.'''
    new_item: Dict = {}
    new_item['url'] = item.get('url', '')
    new_item['title'] = (title := item.get('title_description').get('title'))
    new_item['description'] = (description := item.get('title_description').get('description'))
    #new_item['description'] = (description := get_description(item))
    new_item['word_count']: int = item.get('soup_bigrams_trigrams').get('wordcount', 0)
    new_item['slug']: str = item.get('slug', '')
    new_item['keywords'] = item.get('soup_bigrams_trigrams').get('keywords', [])
    new_item['bigrams'] = item.get('soup_bigrams_trigrams').get('bigrams', Counter())
    new_item['trigrams'] = item.get('soup_bigrams_trigrams').get('trigrams', Counter())
    new_item['content_hash'] = item.get('content_hash', '')
    new_item['headings'] = item.get('headings', {})
    new_item['og_tags'] = (og_tags := item.get('og_tags', {}))
    new_item['additional_info'] = item.get('additional_info', {})
    new_item['links'] = (links := item.get('links', []))
    new_item['images'] = (images := item.get('images', []))
    funcs = [make_link_warnings(links),
           make_image_warnings(images),
           title_length(title),
           description_length(description),
           get_og_tag_warnings(og_tags),
           keywords_tag_present(og_tags)]
    #tasks = [asyncio.create_task(func) for func in funcs]
    new_warnings = await asyncio.gather(*funcs)
    new_warnings2 = [i for i in new_warnings if i]
    new_warnings3 = reduce(operator.add, new_warnings2)
    new_item['warnings'] = [warning for warning in new_warnings3 if warning] #remove NoneType objects
    await asyncio.sleep(0)
    return new_item

async def main(pages: List[Dict]):
    '''The main coroutine and entry point to the application. Many
    asyncio-based applications have a main coroutine.'''
    new_formatter = Formatter()
    step1 = await new_formatter.process_item_threads(
        items=pages, func=process_content_hash)
    step2 = await new_formatter.process_item_threads(
        items=step1, func=process_clean_html)
    step3 = await new_formatter.process_item_threads(
        items=step2, func=process_slug)
    step4 = await new_formatter.process_item_processes(
        items=step3, func=process_bigrams_trigrams_headings)
    step5 = await new_formatter.apply_to_iterable(items=step4, func=make_formatted_page)
    return step5

async def format_pages(pages: List[Dict]):
    '''A thin wrapper around the main() function allowing it to be
    called from outside the module.'''
    return await main(pages)

if __name__ == '__main__':
    start = time.time()
    import json
    import random
    with open(f'local_data_final/km_data0.json', 'r') as in_file:
        km_results0 = json.load(in_file)
    #print(len(km_results0))
    loop = asyncio.new_event_loop()
    task0 = loop.run_until_complete(format_pages(pages=km_results0))
    end = time.time()
    
    print(len(task0))
    first_page = task0[random.randrange(1, 50)]
    print(f'url: {first_page.get("url")}')
    print(f'title: {first_page.get("title")}')
    print(f'description: {first_page.get("description")}')
    print(f'headings: {first_page.get("headings")}')
    print(f'additional_info: {first_page.get("additional_info")}')
    print(f'soup: {first_page.get("soup")}')
    print(f'word_count: {first_page.get("word_count")}')
    print(f'content_hash: {first_page.get("content_hash")}')
    print(f'bigrams: {list(first_page.get("bigrams").items())[:20]}')
    print(f'trigrams: {list(first_page.get("trigrams").items())[:20]}')
    print(f'keywords: {first_page.get("keywords")}')
    print(f'og_tags: {first_page.get("og_tags")}')
    print(f'images: {first_page.get("images")}')
    print(f'links: {first_page.get("links")}')
    print(f'warnings: {first_page.get("warnings")}')
    print(f'slug: {first_page.get("slug")}')
    print(f'The operation took {end-start} seconds')
    print(f'{first_page.keys()}')