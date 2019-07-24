from urllib.parse import urlparse, urljoin
import lxml.html
import requests
import colorlog
from functools import wraps
from time import time
logger = colorlog.getLogger('airstuff.journal')
URL_DOI = 'https://doi.org'


def timing_warning(max_time):
    def wrap(f):
        @wraps(f)
        def wrapped_f(*args, **kwargs):
            tstart = time()
            result = f(*args, **kwargs)
            tstop = time()
            if tstop - tstart > max_time:
                logger.warning('function %s with arguments %s %s took much time: %f ms', f.__name__, args, kwargs, (tstop - tstart) * 1000)
            return result
        return wrapped_f
    return wrap


@timing_warning(1)
def check_url_exists(url):
    return requests.head(url).status_code < 400


@timing_warning(3)
def get_redirect(url):
    r = requests.head(url, allow_redirects=True)
    if r.status_code == 404:
        return None
    location_redirect = r.url
    return location_redirect


def get_redirect_doi(doi):
    url_doi = urljoin(URL_DOI, doi)
    redirect = get_redirect(url_doi)
    if not redirect:
        logger.warning('cannot get redirect for doi %s', url_doi)
        return None
    return redirect


def get_pdf_url(doi):
    logger.debug('getting redirect for doi %s', doi)
    url = get_redirect_doi(doi)
    if not url:
        logger.warning('cannot resolve doi %s', doi)

        tentative_url = None
        if 'epjc' in doi.lower():
            tentative_url = 'http://link.springer.com/content/pdf/%s' % doi
        elif 'jhep' in doi.lower():
            tentative_url = 'https://link.springer.com/content/pdf/%s' % doi

        logger.debug('tentative url: %s from doi: %s', tentative_url, doi)

        if tentative_url:
            if check_url_exists(tentative_url):
                return tentative_url
        
        return None

    hostname = urlparse(url).hostname
    logger.debug('redirect from doi %s is %s', doi, url)
    if hostname == 'link.springer.com':
        return get_pdf_url_springler(doi, url)
    elif hostname == 'journals.aps.org':
        return url.replace('abstract', 'pdf')
    elif hostname == 'linkinghub.elsevier.com':
        return get_pdf_url_science_direct(url)
    elif hostname == 'iopscience.iop.org':
        return urljoin(url, '/pdf')
    else:
        logger.error('not able to get pdf for %s from %s', doi, url)
        return None


def get_pdf_url_science_direct(url):
    if 'linkinghub' in url:
        n = url.split('/')[-1]
        url = 'https://www.sciencedirect.com/science/article/pii/%s/pdfft' % n
        return url
    else:
        raise NotImplementedError


def get_pdf_url_springler(doi, url):
    r = get_pdf_url_springler_tight(url)
    if r:
        return r
    logger.warning('problem to find pdf link for %s on springler, try another method', doi)
    r = get_pdf_url_springler_loose(doi)
    return r

@timing_warning(1)
def get_pdf_url_springler_tight(url):   
    r = requests.get(url)
    html = r.text
    root = lxml.html.fromstring(html)         
    els = root.xpath('//div[@class="download-article test-pdf-link"]//a[@title="Download this article in PDF format"]')

    if len(els) != 1:
        logger.error('more than one download link on %s', url)
        return None
    elif not els:
        logger.error('no download link on %s', url)
        return None

    return urljoin(url, els[0].attrib['href'])


def get_pdf_url_springler_loose(doi):
    url = urljoin('https://link.springer.com/content/pdf/', doi)
    if check_url_exists(url):
        return url
    else:
        return None