#!/usr/bin/env python

__doc__ = "simple tool to dump the information from articles"
__author__ = "Ruggero Turra"
__email__ = "ruggero.turra@mi.infn.it"

import logging
import StringIO
import urllib2
import os.path
import re
import sys

from common import get_html
import dump_milano_authors
import dump_abstract
import dump_keyword

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog arxiv_url inspire_url")
    parser.epilog = "example: python dump_info.py http://arxiv.org/abs/1208.0572 http://inspirehep.net/record/1114314/"
    (options, args) = parser.parse_args()

    if len(args) != 2:
        logging.error("you have to specify the arxiv and inspire urls")
        exit()

    logging.info("getting htmls")
    html_arxive = get_html(args[0])
    html_inspire = get_html(args[1])
    
    
    print "\n===== ABSTRACT =====\n"
    abstract = dump_abstract.main(html_arxive)
    print abstract
    print "\n===== KEYWORKDS ======\n"
    keys = dump_keyword.get_keys_from_html(html_inspire)
    print keys
    print "\n===== AUTHORS =====\n"
    authors = dump_milano_authors.main(html_arxive, args[0])
    print ", ".join(authors)

    
