import datetime
import re
from typing import Dict, List, Tuple, Union, Optional, Generator
from collections import Counter
from pydantic import BaseModel, Field, validator, HttpUrl
#from pydantic.dataclasses import dataclass

class PageIterator(BaseModel):
    '''This iterator for the Analysis object only includes the pages'''
    warnings: List
    index: int = Field(gte=0, default=0)
    
    def __iter__(self):
        '''Returns itself as an iterator'''
        return self
    
    def __next__(self):
        '''Returns the next page'''
        if self.index >= len(self.warnings):
            raise StopIteration
        value = self.warnings[self.index]
        self.index += 1
        return value

class Page(BaseModel):
    '''A class that represents each page in the website'''
    url: Union[HttpUrl, str]
    title: str = Field(default='', min_length=0, max_length=500)
    description: str = Field(default='', min_length=0, max_length=1000)
    word_count: int = Field(gte=0, default=0)
    keywords: List[Tuple[str, int]] = Field(default=[])
    bigrams: Union[Counter, Dict] = Field(default=Counter())
    trigrams: Union[Counter, Dict] = Field(default=Counter())
    content_hash: str = Field(default='')
    headings: Dict = Field(default={})
    og_tags: Dict = Field(default={})
    additional_info: Dict = Field(default={})
    links: List[Dict] = Field(default=[])
    images: List[Dict] = Field(default=[])
    warnings: List[str] = Field(default=[])
    
    @property
    def slug(self) -> Union[str, None]:
        '''Takes a url and returns a slug.'''
        try:
            def get_last(item):
                '''Internal function that gets the last item in a sequence, returning
                None if the item is empty'''
                try:
                    return item[-1]
                except IndexError:
                    return None
                #we have to get all the possible slugs
            split_url: List[List[str]] = self.url.split(r'/') #split the url
            if len(split_url) == 0: #if no segments match return none
                return None
            slug_matches: List[List] = [re.search(r"^[A-Za-z0-9_-]*$", item) for item in split_url]
            filtered_slug_matches: List[List] = list(filter(None, slug_matches))
            regex_item_results: List[List[str]] = list(map(lambda x: x.group(), filtered_slug_matches))
            #remove_none_types: List[List[str]] = [list(filter(lambda x: bool(x == ''), item)) for item in regex_item_results]
            new_items = [element for element in regex_item_results if element]
            final_slug_with_nonetypes: Union[str, None] = get_last(new_items)
            return final_slug_with_nonetypes
        except Exception as e:
            return f'Error! {e}'
    
    def __iter__(self):
        return PageIterator(warnings=self.warnings)

    @staticmethod
    def remove_image_warnings(warnings: List[str]) -> List[str]:
        '''Takes a list and removes the image warnings from it.'''
        return list(filter(lambda x: 'Image missing alt tag' not in x, warnings))

    @staticmethod
    def remove_seo_warnings(warnings: List[str]) -> List[str]:
        '''Takes a list and removes the non link or image warnings from it. This method
        helps create the link and image alerts.'''
        seo_warnings_regex = re.compile('(Anchor missing title tag|Image missing alt tag)')
        return list(filter(lambda x: bool(re.search(seo_warnings_regex, x))))

    @staticmethod
    def remove_link_warnings(warnings: List[str]) -> List[str]:
        '''Takes a list and removes the image warnings from it.'''
        return list(filter(lambda x: 'Anchor missing title tag' not in x, warnings))

    
    @validator('warnings', pre=True)
    def validate_warnings(cls, v: List[str]) -> List[str]:
        '''Returns a list of warnings while removing any missing warnings'''
        #remove the image warnings first
        return [item for item in v if item]
        #image_warnings_removed = Page.remove_image_warnings([item for item in v if item])
        #return Page.remove_link_warnings(image_warnings_removed)

    #@validator('link_alerts', pre=True)
    #def validate_link_alerts(cls, v: List[str]) -> List[str]:
    #    '''Returns a list of warnings with only the link warnings present.'''
    #    step1 = Page.remove_seo_warnings(v)
    #    return Page.remove_image_warnings(step1)

    #@validator('image_alerts', pre=True)
    #def validate_image_alerts(cls, v: List[str]) -> List[str]:
    #    '''Returns a list of warnings with only the image warnings present.'''
    #    step1 = Page.remove_seo_warnings(v)
    #    return Page.remove_link_warnings(step1)

    @classmethod
    def factory(cls, v: Dict):
        '''Takes a dictionary and returns a Page object.'''
        new_page = {}
        new_page['url'] = v.get('url', '')
        new_page['title'] = v.get('title', '')
        new_page['description'] = v.get('description', '')
        new_page['word_count'] = v.get('word_count', '')
        new_page['bigrams'] = v.get('bigrams', Counter())
        new_page['trigrams'] = v.get('trigrams', Counter())
        new_page['content_hash'] = v.get('content_hash', '')
        new_page['headings'] = v.get('headings', '')
        new_page['og_tags'] = v.get('og_tags', {})
        new_page['additional_info'] = v.get('additional_info', {})
        new_page['links'] = v.get('links', [])
        new_page['images'] = v.get('images', [])
        new_page['warnings'] = v.get('warnings', [])
        #new_page['link_alerts'] = v.get('warnings', [])
        #new_page['image_alerts'] = v.get('warnings', [])
        return cls(**new_page)
        
        

        
    
    
    
    