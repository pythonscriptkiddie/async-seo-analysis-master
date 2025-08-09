import asyncio
from typing import List, Dict

async def title_length(title, min_title_length=10, max_title_length=70):
    '''Takes an element from a dask bag and creates the warnings if it exceeds
    the minimum or maximum title length.'''
    warning_msg = None #create warning message as an empty variable
    if min_title_length >= max_title_length:
        raise Exception('Min title lengths MUST be less than max length.')
    else:
        if (title_length := len(title)) == 0:
            warning_msg = 'Missing title tag'
        elif title_length <= min_title_length:
            warning_msg = f'Title tag is too short (less than {min_title_length} characters): {title}'
        elif title_length >= max_title_length:
            warning_msg = f'Title tag is too long (more than {max_title_length} characters): {title}'
    await asyncio.sleep(0)
    return [warning_msg]

async def description_length(description, min_description_length=120, max_description_length=255):
    '''Takes an element from a dask bag and creates the warnings if it exceeds
    the minimum or maximum title length.'''
    warning_msg = None #create warning message as an empty variable
    if min_description_length >= max_description_length:
        raise Exception('Min description lengths MUST be less than max length.')
    else:
        if (description_length := len(description)) == 0:
            warning_msg = 'Missing description'
        elif description_length <= min_description_length:
            warning_msg = f'Title tag is too short (less than {min_description_length} characters): {description}'
        elif description_length >= max_description_length:
            warning_msg = f'Title tag is too long (more than {min_description_length} characters): {description}'
    await asyncio.sleep(0)
    #return [warning_msg]
    if warning_msg:
        return [warning_msg]
    else:
        return []
    
async def get_og_tag_warnings(tags: Dict) -> List[str]:
    '''Takes a dictionary of og_tags and returns a list of warnings if any are not present.'''
    og_tags: List = ['og:title', 'og:description', 'og:image', 'og:type', 'og:url']
    og_tag_warnings = []
    for item in og_tags:
        if tags.get(item, '') == '':
            og_tag_warnings.append(f'Missing {item}')
    await asyncio.sleep(0)
    return og_tag_warnings

async def keywords_tag_present(tags: Dict) -> bool:
    '''Takes a dictionary of og tags and returns True if the keywords tag is present
    else False.'''
    await asyncio.sleep(0)
    if (keywords_tag := tags.get('keywords_tag', '') == ''):
        return None
    else:
        return f'Keywords should be avoided as they are a spam indicator: {keywords_tag}' 

async def get_h1_warnings(tags):
    '''Takes the heading tags dictionary and returns warnings based on the number of h1 tags.'''
    try:
        match len(tags.get('h1', '')):
            case 0:
                h1_tag_warnings = ['Page must have at least one h1 tag']
            case _:
                h1_tag_warnings = []
    finally:
        await asyncio.sleep(0)
    return h1_tag_warnings


async def make_image_warnings(images: List[Dict]) -> List[str]:
    '''Takes each element and creates warnings for the links as appropriate.'''
    '''Takes each element and creates warnings for the links as appropriate.'''
    await asyncio.sleep(0)
    return [f'Image missing alt tag : {i.get("src")}'
                     for i in images if not i.get('alt')]


async def make_link_warnings(links: List[Dict]) -> List[str]:
    '''Takes each element and creates warnings for the links as appropriate.'''
    '''Takes each element and creates warnings for the links as appropriate.'''
    await asyncio.sleep(0)
    return [f'Anchor missing title tag: {i.get("href")}'
                           for i in links if not i.get('title', '')]