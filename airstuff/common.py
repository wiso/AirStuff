import urllib.request, urllib.error, urllib.parse
import re

r = re.compile("arXiv:([0-9\.]+)")


def get_html(url):
    return urllib.request.urlopen(url).read().decode('utf-8')


def arxiv_number_from_inspire(html_inspire):
    m = r.search(html_inspire)
    if not m:
        raise ValueError("cannot find arxiv from inspire")
    return m.group(1)
