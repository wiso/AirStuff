from bs4 import BeautifulSoup
import re
import itertools
import xml.etree.ElementTree as ET
from lxml import etree
import lxml.html


def soup(html):
    print('creating soup')
    soup = BeautifulSoup(html, 'lxml')
    print('searching form')
    form = soup.find("form", {'id': 'exportform'})
    if not form:
        return []
    print('searching entries')
    entries = form.find_all("input", {'name': 'item_id'})
    result = [entry['value'] for entry in entries]
    return result


def regex(html):
    r = re.compile(r'<input type="hidden" name="item_id" value="([0-9]+)">')

    s = r.finditer(html)
    result = []
    for ss in itertools.islice(s, 10):
        result.append(ss.group(1))
    return result


def xpath(html):
    root = lxml.html.fromstring(html)
    result = root.xpath('(//div[@class="panel panel-primary"]/div[@class="panel-heading"]/form[@class="form-inline"]/*[@name="item_id"])[position() <= 10]')
    return [r.attrib['value'] for r in result]


def xpath2(html):
    root = etree.HTML(html)
    result = root.xpath('//form[@class="form-inline"]/*[@name="item_id"]')
    return [r.attrib['value'] for r in result]


html = open('/home/turra/example.html').read()

print(xpath(html))

print(xpath2(html))
print(soup(html))
print(regex(html))

import timeit
print(timeit.timeit('soup(html)', setup="from __main__ import soup, html", number=4))
print(timeit.timeit('regex(html)', setup="from __main__ import regex, html", number=4))
print(timeit.timeit('xpath(html)', setup="from __main__ import xpath, html", number=4))
print(timeit.timeit('xpath2(html)', setup="from __main__ import xpath2, html", number=4))
