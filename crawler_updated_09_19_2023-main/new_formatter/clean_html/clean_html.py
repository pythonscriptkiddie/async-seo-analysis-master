import re

def create_clean_html(raw_html: str) -> str:
    '''Takes an element and replaces the html of the element with
    a version that has comments removed.'''
    #print(type(raw_html))
    return re.sub(r'<!--.*?-->', r'', raw_html, flags=re.DOTALL)