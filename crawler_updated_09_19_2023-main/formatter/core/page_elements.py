from typing import Dict
from bs4 import BeautifulSoup

def get_title(soup):
    '''Takes a BeautifulSoup object and returns the title'''
    try:
        title = soup.title.text
    except AttributeError:
        title = ''
    finally:
        return title

def get_description(soup):
    '''Takes a BeautifulSoup object and returns its description'''
    raw_description = soup.findAll('meta', attrs={'name': 'description'})
    if len(raw_description) > 0:
        description = raw_description[0].get('content')
    else:
        description = ''
    return description

def create_title_description(text: str) -> Dict:
    '''Takes the text and creates a BeautifulSoup object,
    returning the title and description'''
    context = {}
    new_soup = BeautifulSoup(text, 'lxml')
    context['title'] = get_title(new_soup)
    context['description'] = get_description(new_soup)
    #context['keywords'] = get_keywords(new_soup)
    return context
    