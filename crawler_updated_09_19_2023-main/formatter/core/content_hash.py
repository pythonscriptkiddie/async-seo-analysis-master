import hashlib

def create_content_hash(raw_html: str):
    '''Takes a string of text and returns the content hash using hashlib.'''
    return hashlib.sha1(raw_html.encode('utf-8')).hexdigest()