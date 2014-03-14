import urllib2
import re

r = re.compile("arXiv:([0-9\.]+)")


def get_html(url):
    return urllib2.urlopen(url).read()


def arxiv_number_from_inspire(html_inspire):
    m = r.search(html_inspire)
    if not m:
        raise ValueError("cannot find arxiv from inspire")
    return m.group(1)
