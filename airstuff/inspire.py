# https://labs.inspirehep.net/api/literature?sort=mostrecent&size=25&q=&collaboration=ATLAS
# https://labs.inspirehep.net/api/literature?sort=mostrecent&size=25&q=&collaboration=ATLAS&doc_type=peer%20reviewed
# https://labs.inspirehep.net/api/literature?sort=mostrecent&size=25&q=&collaboration=ATLAS&doc_type=peer%20reviewed&page=2

import requests
import json
from multiprocessing.pool import ThreadPool
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("bibtexparser").setLevel(logging.WARNING)

URL_SEARCH = "http://inspirehep.net/search"


def query_inspire(search, rg, sc, ot=None):
    ot = ot or ['recid', 'creation_date', 'number_of_authors', 'system_control_number', 'doi', 'title']
    r = requests.get(URL_SEARCH,
                     params=dict(
                         of='recjson',             # json format
                         rg=rg,                    # range
                         action_search="Search",
                         sc=sc,                    # offset
                         do='d',
                         ot=ot,                    # ouput tags
                         sf='earliestdate',        # sorting
                         so='d',                   # descending
                         p=search))
    logging.debug('querying %s' % r.url)
    try:
        j = json.loads(r.text)
    except json.decoder.JSONDecodeError:
        logging.error("problem decoding", r.text)
        return None
    return j


def fix_info(info):
    if 'doi' in info:
        if type(info['doi']) is list:
            if len(set(info['doi'])) == 1:
                info['doi'] = info['doi'][0]
    if 'title' in info:
        if type(info['title']) is dict:
            info['title'] = info['title']['title']
    return info


def get_all_collaboration(collaboration, infos=None):
    infos = infos or ['recid', 'creation_date', 'number_of_authors', 'system_control_number', 'doi', 'title']
    nthread = 10
    shift = 20
    offset = 0

    def get(offset):
        search = "collaboration:'%s' AND collection:published" % collaboration
        return query_inspire(search, shift, offset, infos)

    while True:
        offset_bunch = []
        for b in range(nthread):
            offset_bunch.append(offset)
            offset += shift
        with ThreadPool(nthread) as pool:
            r = pool.map(get, offset_bunch)
            for rr in r:
                dobreak = False
                for rrr in rr:
                    yield fix_info(rrr)
                if not rr:
                    dobreak = True
            if dobreak:
                break


for x in get_all_collaboration('ATLAS'):
    print(x['creation_date'], x['doi'], x['title'])