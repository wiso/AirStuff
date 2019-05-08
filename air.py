import requests
import bibtexparser
from bs4 import BeautifulSoup
from multiprocessing.pool import ThreadPool
from functools import partial
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("bibtexparser").setLevel(logging.WARNING)


def get_document_metadata(document_id):
    BASEURL = "https://air.unimi.it/references"
    r = requests.get(BASEURL, params={'format': 'bibtex', 'item_id': str(document_id)})
    return bibtexparser.loads(r.text).entries[0]


def get_documents_from_author(author_id):
    offset = 0
    BUNCH = 10

    # get = partial(get_documents_from_author_offset, author_id=author_id)

    def get(offset):
        return get_documents_from_author_offset(author_id, offset)

    while True:
        with ThreadPool(BUNCH) as pool:
            offset_bunch = []
            for b in range(BUNCH):
                offset_bunch.append(offset)
                offset += 20

            r = pool.map(get, offset_bunch)
            for rr in r:
                dobreak = False
                for rrr in rr:
                    yield rrr
                if not rr:
                    dobreak = True
            if dobreak:
                break


def get_documents_from_author_offset(author_id, offset):
    BASEURL = "https://air.unimi.it/browse?type=author&order=ASC&rpp=20&authority=%s&offset=%d"
    url = BASEURL % (author_id, offset)
    logging.debug("getting info from %s", url)
    r = requests.get(url)
    html = r.text
    soup = BeautifulSoup(html, 'lxml')

    form = soup.find("form", {'id': 'exportform'})
    if not form:
        return []

    entries = form.find_all("input", {'name': 'item_id'})
    return [entry['value'] for entry in entries]


g = get_documents_from_author('rp09852')
for gg in g:
    info = get_document_metadata(gg)
    if 'doi' not in info:
        logging.info("skipping %s", info)
        continue
    print(info['doi'])