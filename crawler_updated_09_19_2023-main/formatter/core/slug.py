from typing import List, Union
import re
from urllib.parse import urlsplit

def make_slug(url: str) -> str:
    '''Takes a url and returns a slug.'''
    def get_last(item):
        '''Internal function that gets the last item in a sequence, returning
        None if the item is empty'''
        try:
            return item[-1]
        except IndexError:
            return None
        #we have to get all the possible slugs
    split_url: List[List[str]] = url.split(r'/') #split the url
    if len(split_url) == 0: #if no segments match return none
        return None
    slug_matches: List[List] = [re.search(r"^[A-Za-z0-9_-]*$", item) for item in split_url]
    filtered_slug_matches: List[List] = list(filter(None, slug_matches))
    regex_item_results: List[List[str]] = list(map(lambda x: x.group(), filtered_slug_matches))
    #remove_none_types: List[List[str]] = [list(filter(lambda x: bool(x == ''), item)) for item in regex_item_results]
    new_items = [element for element in regex_item_results if element]
    final_slug_with_nonetypes: List[Union[str, None]] = get_last(new_items)
    return final_slug_with_nonetypes

def categories_from_url(url: str) -> Union[List, None]:
    '''Takes a url and obtains the categories, if any. If there are no
    categories it returns None.'''
    slug: str = make_slug(url)
    if url[-1] == r'/': #remove the last character if it ends in a slash
        modified_url: str = url[:-1]
    else:
        modified_url: str = url
    url_path: str = urlsplit(modified_url).path
    #print(type(url_path))
    try:
        url_without_slug: str = re.sub(slug, '', url_path)
    except TypeError:
        return None
    spaces_replace_slashes: str = re.sub(r'/', ' ', url_without_slug)
    categories = spaces_replace_slashes.strip()
    category_list: List = categories.split(' ')
    if not all([i for i in category_list if i == '']): #if there are no items we return None
        return None
    return category_list