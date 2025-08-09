import time
import asyncio
import aiohttp
import logging
from functools import partial
from asyncio import Queue
from contextvars import ContextVar
from urllib.parse import urlsplit
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from .rel_to_abs_url.rel_to_abs_url import rel_to_abs_url
from .retry.retry import retry


class WorkItem:
    def __init__(self, item_depth: int, url: str):
        self.item_depth = item_depth
        self.url = url


async def worker(worker_id: int, queue: Queue, session: ClientSession, max_depth: int,
    start_url: ContextVar, base_netloc: ContextVar, pages: ContextVar, crawled_pages: ContextVar):
    '''Workers get new items as they are added to the queue, and then schedule them for processing.'''
    print(f'Worker {worker_id}')
    while True: #A
        work_item: WorkItem = await queue.get()
        print(f'Worker {worker_id}: Processing {work_item.url}')
        await process_page(work_item, queue, session, max_depth, start_url, base_netloc, pages, crawled_pages)
        print(f'Worker {worker_id}: Finished {work_item.url}')
        queue.task_done()


async def process_page(work_item: WorkItem, queue: Queue, session: ClientSession, max_depth: int,
    start_url: ContextVar, base_netloc: ContextVar, pages: ContextVar, crawled_pages: ContextVar): #B
    '''Processes each page as it is put through the queue.'''
    def remove_symbols(url: str):
        '''Convenience function to remove symbols from a url. If there is a question mark or
        an asterisk we will remove it'''
        new_url = url
        if '?' in new_url:
            new_url = new_url[:new_url.index('?')]
        elif '#' in new_url:
            new_url = new_url[:new_url.index('#')]
        return new_url

    base_url = start_url.get()
    default_netloc = base_netloc.get()
    pages_crawled = crawled_pages.get()
    page_results = pages.get()
    try:
        get_url = partial(session.get, url=work_item.url)
        #response = await asyncio.wait_for(session.get(work_item.url), timeout=3)
        response = await retry(get_url, timeout=10, retry_interval=1, max_retries=3)
        if work_item.item_depth == max_depth:
            print(f'Max depth reached, '
                  f'not processing more for {work_item.url}')
        else:
            url = str(response.url)
            body = await response.text()
            page_results.append({'url': url, 'text': body})
            soup = BeautifulSoup(body, 'html.parser')
            links = soup.find_all('a', href=True)
            relative_urls = (link['href'] for link in links)
            absolute_urls = (rel_to_abs_url(link=relative_url, base_domain=base_url,
                url=base_url) for relative_url in relative_urls)
            internal_links = (link for link in absolute_urls if urlsplit(link).netloc == default_netloc)
            links_symbols_removed = (remove_symbols(link) for link in internal_links)
            for link in links_symbols_removed:
                #print(start_url.get())
                if link not in pages_crawled:
                    #print(link not in pages_crawled)
                    pages_crawled.append(link)
                    queue.put_nowait(WorkItem(work_item.item_depth + 1,
                                          link))
    except Exception as e:
        logging.exception(f'Error processing url {work_item.url}')


async def crawl_site(homepage: str,
    max_depth: int = 3, num_workers: int=25): #C
    start = time.time()
    start_url = ContextVar('start url',
        default=homepage)
    base_netloc = ContextVar('base netloc',
        default=urlsplit(homepage).netloc)
    crawled_pages = ContextVar('crawled pages', default=[])
    pages = ContextVar('pages', default=[])
    url_queue = Queue()
    url_queue.put_nowait(WorkItem(0, start_url.get()))
    async with aiohttp.ClientSession() as session:
        workers = [asyncio.create_task(worker(i, url_queue, session, max_depth, start_url, base_netloc,
            pages, crawled_pages))
                   for i in range(num_workers)]
        await url_queue.join()
        [w.cancel() for w in workers]
    end = time.time()
    print(f'Total time was: {end-start}')
    return pages.get()

if __name__ == '__main__':
    crawled_pages = asyncio.run(crawl_site(homepage='http://kevinmartinlaw.com'))
    #print(crawled_pages)
    print(len(crawled_pages))
    print([item.get('url') for item in crawled_pages])