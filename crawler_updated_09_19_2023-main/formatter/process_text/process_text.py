import re
from typing import List, Dict, Tuple
from collections import Counter
from bs4 import BeautifulSoup
from .stemmer import stem

TOKEN_REGEX = re.compile(r'(?u)\b\w\w+\b')

# This list of English stop words is taken from the "Glasgow Information
# Retrieval Group". The original list can be found at
# http://ir.dcs.gla.ac.uk/resources/linguistic_utils/stop_words
ENGLISH_STOP_WORDS = frozenset([
    "a", "about", "above", "across", "after", "afterwards", "again", "against",
    "all", "almost", "alone", "along", "already", "also", "although", "always",
    "am", "among", "amongst", "amoungst", "amount", "an", "and", "another",
    "any", "anyhow", "anyone", "anything", "anyway", "anywhere", "are",
    "around", "as", "at", "back", "be", "became", "because", "become",
    "becomes", "becoming", "been", "before", "beforehand", "behind", "being",
    "below", "beside", "besides", "between", "beyond", "bill", "both",
    "bottom", "but", "by", "call", "can", "cannot", "cant", "co", "con",
    "could", "couldnt", "cry", "de", "describe", "detail", "do", "done",
    "down", "due", "during", "each", "eg", "eight", "either", "eleven", "else",
    "elsewhere", "empty", "enough", "etc", "even", "ever", "every", "everyone",
    "everything", "everywhere", "except", "few", "fifteen", "fify", "fill",
    "find", "fire", "first", "five", "for", "former", "formerly", "forty",
    "found", "four", "from", "front", "full", "further", "get", "give", "go",
    "had", "has", "hasnt", "have", "he", "hence", "her", "here", "hereafter",
    "hereby", "herein", "hereupon", "hers", "herself", "him", "himself", "his",
    "how", "however", "hundred", "i", "ie", "if", "in", "inc", "indeed",
    "interest", "into", "is", "it", "its", "itself", "keep", "last", "latter",
    "latterly", "least", "less", "ltd", "made", "many", "may", "me",
    "meanwhile", "might", "mill", "mine", "more", "moreover", "most", "mostly",
    "move", "much", "must", "my", "myself", "name", "namely", "neither",
    "never", "nevertheless", "next", "nine", "no", "nobody", "none", "noone",
    "nor", "not", "nothing", "now", "nowhere", "of", "off", "often", "on",
    "once", "one", "only", "onto", "or", "other", "others", "otherwise", "our",
    "ours", "ourselves", "out", "over", "own", "part", "per", "perhaps",
    "please", "put", "rather", "re", "same", "see", "seem", "seemed",
    "seeming", "seems", "serious", "several", "she", "should", "show", "side",
    "since", "sincere", "six", "sixty", "so", "some", "somehow", "someone",
    "something", "sometime", "sometimes", "somewhere", "still", "such",
    "system", "take", "ten", "than", "that", "the", "their", "them",
    "themselves", "then", "thence", "there", "thereafter", "thereby",
    "therefore", "therein", "thereupon", "these", "they",
    "third", "this", "those", "though", "three", "through", "throughout",
    "thru", "thus", "to", "together", "too", "top", "toward", "towards",
    "twelve", "twenty", "two", "un", "under", "until", "up", "upon", "us",
    "very", "via", "was", "we", "well", "were", "what", "whatever", "when",
    "whence", "whenever", "where", "whereafter", "whereas", "whereby",
    "wherein", "whereupon", "wherever", "whether", "which", "while", "whither",
    "who", "whoever", "whole", "whom", "whose", "why", "will", "with",
    "within", "without", "would", "yet", "you", "your", "yours", "yourself",
    "yourselves"])

def word_list_freq_dist(wordlist: List) -> Dict:
    '''Takes a list of words and returns a dictionary that has the count of each word'''
    freq = [wordlist.count(w) for w in wordlist]
    return dict(zip(wordlist, freq))

def sort_freq_dist(freqdist, limit=1, stem_to_word: Dict={}):
    aux = [(freqdist[key], stem_to_word[key]) for key in freqdist if freqdist[key] >= limit]
    aux.sort()
    aux.reverse()
    return aux

def raw_tokenize(rawtext):
    return TOKEN_REGEX.findall(rawtext.lower())

def tokenize(rawtext):
    return [word for word in TOKEN_REGEX.findall(rawtext.lower()) if word not in ENGLISH_STOP_WORDS]

def getngrams(D, n=2):
    return zip(*[D[i:] for i in range(n)])

def process_text(vt, stem_to_word: Dict={}, wordcount=Counter(), bigrams=Counter(),
                 trigrams=Counter(),
                keywords: Dict={}):
    '''Processes text and returns two counters, bigrams and trigrams.'''
    
    page_text = ''

    for element in vt:
        if element.strip():
            page_text += element.strip().lower() + u' '

    tokens = tokenize(page_text)
    raw_tokens = raw_tokenize(page_text)
    #total_word_count = len(raw_tokens)

    new_bigrams = getngrams(raw_tokens, 2)
    #return bigrams

    for ng in new_bigrams:
        vt = ' '.join(ng)
        #try:
        bigrams[vt] += 1
       # except KeyError:
            #bigrams[''.join(vt)] += 1
    #return {'bigrams': bigrams}

    new_trigrams = getngrams(raw_tokens, 3)

    for ng in new_trigrams:
        vt = ' '.join(ng)
        trigrams[vt] += 1

    freq_dist = word_list_freq_dist(tokens)

    for word in freq_dist:
        root = stem(word)
        cnt = freq_dist[word]

        if root not in stem_to_word:
            stem_to_word[root] = word

        if root in wordcount:
            wordcount[root] += cnt
        else:
            wordcount[root] = cnt

        if root in keywords:
            keywords[root] += cnt
        else:
            keywords[root] = cnt
    keywords2: List[Tuple] = sorted(list(keywords.items()), key=lambda x: x[1])
    keywords3: List[Tuple] = list(filter(lambda x: x[1] >= 5, keywords2))

    return {'bigrams': bigrams,
            'trigrams': trigrams,
            'wordcount': sum(wordcount.values()),
            'keywords': keywords3}

def create_title(soup):
    '''Takes a BeautifulSoup object and returns its title.'''
    try:
        title = soup.title.text
    except AttributeError:
        title = ''
    finally:
        return title

def create_description(soup):
    '''Takes a BeautifulSoup object and returns its description.'''
    raise NotImplementedError

def create_bigrams_trigrams(text): #2-4
    '''Takes the existing item and adds a visible text list to it, helping us
    to create bigrams and trigrams.'''
    
    def __visible_tags(element) -> bool: #4 #do not call by itself
        '''Returns False if a tag is not visible, else True'''
        if element.parent.name in ['style', 'script', '[document]']:
            return False
        return True

    soup_lower = BeautifulSoup(text.lower(), 'lxml')
    soup_regular = BeautifulSoup(text, 'lxml')
    page_title = create_title(soup_regular)
    
    #put analyze images here - uses soup_lower
    #put analyze h1 tags here - uses soup_lower
    texts = soup_lower.findAll(text=True)
    text = [str(w) for w in filter(__visible_tags, texts)]
    result_items = process_text(text)
    result_items['title'] = page_title
    return result_items