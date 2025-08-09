import hashlib

def create_content_hash(html: str) -> str:
    '''Takes a string and returns the content hash. We use the same format as in
    pyseoanalyzer.'''
    return hashlib.sha1(html.encode('utf-8')).hexdigest()

