#!/usr/bin/env python

__doc__ = "simple tool to dump keyword and abstract from inspirehep website"
__author__ = "Ruggero Turra"
__email__ = "ruggero.turra@mi.infn.it"

import logging
import re

from common import get_html
logging.basicConfig(level=logging.INFO)

#re_author_keys = re.compile('<meta +name="keywords" +content="(.+?)" ?/>')
re_keys = re.compile('<a href="(?:http://inspirehep.net)?/search\?p=keyword.+?">(.+?)</a>', re.DOTALL)
re_other_keys = re.compile('<meta +content="(.+?)" +name="citation_keywords" ?/>')


def get_keywords(html):
    print(type(html))
    m_iter_keys = re_keys.finditer(html)
    if not m_iter_keys:
        logging.error("cannot find author keys")
        exit()
    keys = [key.group(1).strip() for key in m_iter_keys]

    return keys


def format_keys(keys):
    return " ; ".join(keys)


def get_keys_from_html(html):
    keys = get_keywords(html)
    return format_keys(keys)


def main(url):
    logging.info("getting html from %s", url)
    html = get_html(url)
    logging.info("searching from keys")
    keys = get_keywords(html)
    return format_keys(keys)

if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser()
    parser.epilog = "example: python dump_keyword.py  http://inspirehep.net/record/1114314"
    (options, args) = parser.parse_args()

    if len(args) != 1:
        logging.error("you have to specify the arxiv url")
        exit()

    print(main(args[0]))
