from urllib.parse import urlsplit

def rel_to_abs_url(link, base_domain, url):
    '''Takes in a relative url and returns an absolute url'''
    if ':' in link:
        return link

    relative_path = link
    base_domain = urlsplit(base_domain)
    domain = base_domain.netloc
    #return base_domain

    try:
        if domain[-1] == '/':
            domain = domain[:-1]
    except IndexError:
        domain = domain[:-1]


    if len(relative_path) > 0 and relative_path[0] == '?':
        if '?' in url:
            return f'{url[:url.index("?")]}{relative_path}'

        return f'{url}{relative_path}'

    if len(relative_path) > 0 and relative_path[0] != '/':
        relative_path = f'/{relative_path}'

    return f'{base_domain.scheme}://{domain}{relative_path}'