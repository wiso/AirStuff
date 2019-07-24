import requests
import urllib
import colorlog
logger = colorlog.getLogger('airstuff.wos')


def get_wos_from_doi(doi):
    r = requests.get('http://ws.isiknowledge.com/cps/openurl/service',
                     params={'url_ver': r'Z39.88-2004', 'rft_id': r'info:doi/%s' % doi},
                     allow_redirects=False)
    logger.debug('querying %s', r.url)
    location_redirect = r.headers['Location']
    logger.debug('redirect to %s', location_redirect)
    if 'NoRecord' in location_redirect:
        logger.warning('cannot get wos id')
        return None
    url_parsed = urllib.parse.urlparse(location_redirect)
    return urllib.parse.parse_qs(url_parsed.query)['KeyUT'][0]


if __name__ == '__main__':
    print(get_wos_from_doi('10.1016/j.physletb.2011.11.010'))
