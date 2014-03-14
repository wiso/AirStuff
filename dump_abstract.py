#!/usr/bin/env python

__doc__ = "simple tool to dump abstract from arxiv website"
__author__ = "Ruggero Turra"
__email__ = "ruggero.turra@mi.infn.it"

import logging
import re

from common import get_html

logging.basicConfig(level=logging.INFO)

re_abstract = re.compile('<blockquote class="abstract.*?">.+?</span>(.+?)</blockquote>',
                         re.DOTALL)

def get_abstract(html):
    m_abstract = re_abstract.search(html)
    if not m_abstract:
        logging.error("cannot find abstract")
        exit()
    result = m_abstract.group(1).strip()
    result = result.replace('\n', ' ').replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    return result

def main(html):
    return get_abstract(html)

if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog arxiv_url")
    parser.epilog = "example: python dump_abstract.py http://arxiv.org/abs/1205.2484"
    (options, args) = parser.parse_args()

    if len(args) != 1:
        logging.error("you have to specify arxiv url")
        exit()

    html = get_html(args[0])
    print main(html)
