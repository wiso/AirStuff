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

def query_inspire(search, rg, sc, infos=None):
    logging.debug('go')
    r = requests.get('http://inspirehep.net/search',
                    params=dict(of='recjson', rg=rg, action_search="Search", sc=sc, do='d',
                                p=search))
    logging.debug('querying %s' % r.url)
    j = json.loads(r.text)
    if infos is not None:
        return {key: j[key] for key in infos}
    else:
        return j


def get_all_collaboration(collaboration, infos=None):
    infos = infos or ['creation_date', 'title', 'doi']
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
                        yield rrr
                    if not rr:
                        dobreak = True
            if dobreak:
                break


for x in get_all_collaboration('ATLAS'):
    print(x)