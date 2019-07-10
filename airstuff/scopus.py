import requests

API_KEY = 'a929befb1fbb5c7e1c5cc994b6188472'


def get_eid_from_doi(doi):
    r = requests.get('https://api.elsevier.com/content/search/scopus',
                     params={'query': 'doi(%s)' % doi,
                             'apiKey': API_KEY})
    json = r.json()
    entries = json['search-results']['entry']
    if len(entries) == 0:
        raise ValueError("no results from doi %s" % doi)
    if len(entries) != 1:
        raise ValueError('multiple results from doi %s' % doi)
    return entries[0]['eid']


if __name__ == '__main__':
    print(get_eid_from_doi('10.1016/j.physletb.2011.11.010'))