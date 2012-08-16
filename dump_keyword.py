#!/usr/bin/env python

__doc__ = "simple tool to dump keyword and abstract from inspirehep website"
__author__ = "Ruggero Turra"
__email__ = "ruggero.turra@mi.infn.it"

import logging
import re

from common import get_html
logging.basicConfig(level=logging.INFO)

re_author_keys = re.compile('<meta +name="keywords" +content="(.+?)" ?/>')
re_other_keys = re.compile('<meta +content="(.+?)" +name="citation_keywords" ?/>')
def get_keywords(html):
    # author keys
    m_author_keys = re_author_keys.search(html)
    if not m_author_keys:
        logging.error("cannot find author keys")
        exit()
    author_keys_conc = m_author_keys.group(1)
    author_keys = [k.strip() for k in author_keys_conc.split(",")]

    # other keys
    
    m_iter_other_keys = re_other_keys.finditer(html)
    other_keys = []
    if not m_iter_other_keys:
        logging.error("cannot find general keys")
        exit()
    for m_other_key in m_iter_other_keys:
        other_keys.append(m_other_key.group(1).strip())

    keys = other_keys + author_keys
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
    parser.add_option("--url", help="inspirehep url")
    parser.epilog = "example: python dump_milano_authors.py --url http://inspirehep.net/record/1114314"
    (options, args) = parser.parse_args()

    if not options.url:
        logging.error("you have to specify the --url")
        exit()

    print main(options.url)

