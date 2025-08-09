from bs4 import BeautifulSoup

def make_soup_lower(html: str):
    '''Takes a text object and returns a BeautifulSoup object.'''
    return BeautifulSoup(html.lower(), 'html.parser')

def make_soup_unmodified(html: str):
    '''Takes a text object and returns a BeautifulSoup object. Same
    as make_soup_lower above but with the Beautiful Soup object
    preserving the case.'''
    return BeautifulSoup(html, 'html.parser')