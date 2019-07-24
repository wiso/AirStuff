import requests
import urllib
import logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s %(levelname)s %(threadName)s %(message)s')


def get_wos_from_doi(doi):
    r = requests.get('http://ws.isiknowledge.com/cps/openurl/service',
                     params={'url_ver': r'Z39.88-2004', 'rft_id': r'info:doi/%s' % doi},
                     allow_redirects=False)
    logging.debug('querying %s', r.url)
    location_redirect = r.headers['Location']
    logging.debug('redirect to %s', location_redirect)
    url_parsed = urllib.parse.urlparse(location_redirect)
    return urllib.parse.parse_qs(url_parsed.query)['KeyUT'][0]


if __name__ == '__main__':
    print(get_wos_from_doi('10.1016/j.physletb.2011.11.010'))
