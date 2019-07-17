import requests
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


API_KEY = 'a929befb1fbb5c7e1c5cc994b6188472'


def get_eid_from_doi(doi):
    r = requests.get('https://api.elsevier.com/content/search/scopus',
                     params={'query': 'doi(%s)' % doi,
                             'apiKey': API_KEY})
    json = r.json()
    entries = json['search-results']['entry']
    
    if len(entries) == 0:
        logging.warning("no results from doi %s", doi)
        return None
    if len(entries) == 1 and 'error' in entries[0]:
        logging.warning("no results from doi %s", doi)
        return None
    if len(entries) != 1:
        logging.warning('multiple results from doi %s', doi)
        return None
    return entries[0]['eid']


if __name__ == '__main__':
    print(get_eid_from_doi('10.1088/1748-0221/14/06/P06012'))
    print(get_eid_from_doi('10.1016/j.physletb.2011.11.010'))