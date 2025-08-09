import time
import asyncio
import logging
import os
from typing import FrozenSet, List, Union
from urllib.parse import urlsplit
from asyncio import Queue
from functools import partial
import aiohttp
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, validator, HttpUrl
from .retry.retry import retry
from .rel_to_abs_url.rel_to_abs_url import rel_to_abs_url

class WorkItem(BaseModel):
    '''A class consisting of a url and a depth or distance from
    the starting url'''
    item_depth : int
    url : str

class AsyncURLCrawler(BaseModel):
    '''An asynchronous scrape class that collects all the urls
    from the website'''
    homepage: Union[HttpUrl, str]
    crawled_pages : List = []
    pages : List = []
    num_workers : int = Field(default=25, gte=1, lte=101)
    max_depth : int = Field(default=3, gte=1, lte=10)
    #include_title: bool = Field(default=True)
    include_text: bool = Field(default=True)
    include_links: bool = Field(default=True)
    include_images: bool = Field(default=True)
    verbose: bool = Field(default=False)

    @property
    def start_netloc(self):
        '''Takes the starting url and obtains the netloc using urllib.parse.urlsplit.'''
        return urlsplit(self.homepage).netloc

    def get_links(self, raw_links: List):
        '''Takes a list of tag objects and returns a list of links'''
        links = [{'href': AsyncURLCrawler.rel_to_abs_url(link=link['href'],
                    base_domain=self.homepage,
                    url=self.homepage),
                    'text': link.text.lower().strip(),
                    'title': link.get('title', '')} for link in raw_links]
        #await asyncio.sleep(0)
        return links

    def get_images(self, soup):
        '''Takes a BeautifulSoup object and obtains a list of images,
        with a dictionary consisting of the features of each image'''
        images = [image for image in soup.findAll('img')]
        #await asyncio.sleep(0)
        return [{'src':image.get('src', '')+image.get('data-src', ''),
                'class': image.get('class', ''),
                'alt': image.get('alt', '')} for image in images]

    @staticmethod
    def is_image(link: str):
        '''Internal function that returns True if something is an image and false if it
        is not. It is only called during the crawling process.'''
        IMAGE_EXTENSIONS = frozenset(['.img', '.png', '.jpg',
                '.jpeg', '.gif', '.bmp', '.svg'])
        _, url_file_extension = os.path.splitext(link)
        if url_file_extension in IMAGE_EXTENSIONS:
            return True
        return False

    @staticmethod
    def is_file(link: str):
        '''Internal function that returns True if something is an image and false if it
        is not. It is only called during the crawling process.'''
        FILE_EXTENSIONS = frozenset(['.pdf', '.jpeg',])
        _, url_file_extension = os.path.splitext(link)
        if url_file_extension in FILE_EXTENSIONS:
            return True
        return False

    @property
    def __rel_to_abs(self):
        '''Returns a partial function that returns the absolute url given the relative url.'''
        return partial(rel_to_abs_url, base_domain=self.homepage,
            url=self.homepage)

    def internal_link(self, link):
        '''Takes a link and tells whether or not it is internal.'''
        return urlsplit(link).netloc == self.start_netloc

    # @staticmethod
    # def remove_question_mark(url):
    #     '''Takes a url and removes question marks'''
    #     if '?' in url:
    #         return url[:url.index(r'?')]
    #     else:
    #         return url

    # @staticmethod
    # def remove_asterisk(url):
    #     '''Takes a url and removes any asterisks present'''
    #     if '#' in url:
    #         return url[:url.index(r'#')]
    #     else:
    #         return url

    @staticmethod
    def clean_url(url):
        '''Takes a url and returns the characters before an asterisk or question mark.'''
        new_url = url
        if '#' in new_url:
            new_url = new_url[:new_url.index(r'#')]
        if '?' in new_url:
            new_url = new_url[:new_url.index(r'?')]
        return new_url

    async def worker(self, worker_id: int, queue: Queue, session: ClientSession, max_depth: int):
        '''An individual worker that processes a page.'''
        if self.verbose == True:
            print(f'Worker {worker_id}')
        while True: #A
            work_item: WorkItem = await queue.get()
            if self.verbose == True:
                print(f'Worker {worker_id}: Processing {work_item.url}')
            await self.process_page(work_item, queue, session, max_depth)
            if self.verbose == True:
                print(f'Worker {worker_id}: Finished {work_item.url}')
            queue.task_done()

    async def process_page(self, work_item: WorkItem, queue: Queue, session: ClientSession, max_depth: int): #B
       #print(start_netloc)
        async def get_response(response):
            '''Convenience function that takes in a Response object and returns
            the url and body.'''
            url = str(response.url)
            body = await response.text()
            return url, body
        
        try:
            #get the original url netloc
            try:
                response = await asyncio.wait_for(session.get(work_item.url), timeout=10)
            except asyncio.TimeoutError:
                get_url = partial(session.get, url=work_item.url)
                response = await retry(get_url, retry_interval=3, timeout=10, max_retries=3)
            if (work_item.item_depth == max_depth) and (self.verbose == True):
                print(f'Max depth reached, '
                    f'not processing more for {work_item.url}')
            else:
                #url = str(response.url)
                #body = await response.text()
                url, body = await get_response(response)
                soup = BeautifulSoup(body, 'lxml')
                raw_links = soup.find_all('a', href=True)
                print(raw_links)
                #if url not in self.crawled_pages:
                context = {'url': url}
                if self.include_text == True:
                    context['text'] = body
                if self.include_links == True:
                    try:
                        links_from_page = self.get_links(raw_links)
                    except Exception as e:
                        links_from_page = []
                    finally:
                        context['links'] = links_from_page
                if self.include_images == True:
                    try:
                        images_from_page = self.get_images(soup)
                    except Exception as e:
                        images_from_page = []
                    finally:
                        context['images'] = images_from_page
                    
                self.pages.append(context)
                #soup moved upwards
                #raw links moved upward
                relative_urls = (link['href'] for link in raw_links) #get the href for each link
                #print(relative_urls)
                absolute_urls = (self.__rel_to_abs(link=relative_url) for relative_url in relative_urls)
                #absolute_urls = (AsyncURLCrawler.rel_to_abs_url(link=relative_url, base_domain=self.homepage,
                #                url=self.homepage) for relative_url in relative_urls) #make the absolute urls
                #create an internal helper function
                internal_links = (link for link in absolute_urls if self.internal_link(link))
                #we make sure the links are not to a file
                links_without_files = (link for link in internal_links if not AsyncURLCrawler.is_file(link))
                #we make sure the link does not connect to
                links_without_images = (link for link in links_without_files if not AsyncURLCrawler.is_image(link))
                cleaned_links = (AsyncURLCrawler.clean_url(link) for link in links_without_images)
                #links_without_question_marks = (AsyncURLCrawler.remove_question_mark(link) for link in links_without_images)
                #links_without_asterisks = (AsyncURLCrawler.remove_asterisk(link) for link in links_without_question_marks)
                for link in cleaned_links:
                    #print(link)
                    #check to see if the link is a link to an image
                    #if the link is a link to an image then we won't crawl it
                    if link not in self.crawled_pages:
                    #check to see if we have not already crawled the link

                        self.crawled_pages.append(link)
                        queue.put_nowait(WorkItem(item_depth=work_item.item_depth + 1,
                                            url=link))
                    elif link in self.crawled_pages:
                        continue
                    
                
        except Exception as e:
            logging.exception(f'Error processing url {work_item.url}')

    async def get_urls_async(self) -> List[str]: #C
        '''Gets a starting url for a website and returns a list of urls from that website
        using the aihottp library'''
        start_url = self.homepage
        #start_url = 'http://app.mychekker.com'
        #start_netloc = urlsplit(start_url).netloc
        url_queue = Queue()
        url_queue.put_nowait(WorkItem(item_depth=0, url=start_url))
        async with aiohttp.ClientSession() as session:
            workers = [asyncio.create_task(self.worker(i, url_queue, session, self.max_depth))
                    for i in range(self.num_workers)]
            await url_queue.join()
            [w.cancel() for w in workers]
            return self.pages

#perhaps write a crawl coroutine here
async def crawl(homepage: str,
               num_workers: int=25,
               max_depth: int=3,
               include_text: bool=True,
               include_images: bool=True,
               include_links: bool=True,
               verbose: bool=True) -> List:
    '''The API that is exposed for the crawler.'''
    new_scraper = AsyncURLCrawler(homepage=homepage,
                                  num_workers=num_workers,
                                  max_depth=max_depth,
                                  include_text=include_text,
                                  include_links=include_links,
                                 include_images=include_images,
                                 verbose=verbose)
    return await new_scraper.get_urls_async()

if __name__ == '__main__':
    start = time.time()
    #new_crawler = AsyncURLCrawler(homepage='http://app.mychekker.com',
                                 #num_workers=25)
    loop = asyncio.new_event_loop()
    crawl_site = partial(crawl, homepage='http://kevinmartinlaw.com/', num_workers=25,
        include_text=True)
    result: List = loop.run_until_complete(crawl_site())
    print('urls are')
    first_page = result[0]
    print(result[0])
    print(len(result))
    end = time.time()
    print(f'{end-start}')
    import json
    for i in range(0, 2):
        with open(f'kevin_martin_test{i}.json', 'w') as out_file:
            json.dump(result, out_file)