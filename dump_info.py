#!/usr/bin/env python

__doc__ = "simple tool to dump the information from articles"
__author__ = "Ruggero Turra"
__email__ = "ruggero.turra@mi.infn.it"

import logging

from common import get_html, arxiv_number_from_inspire
import dump_milano_authors
import dump_abstract
import dump_keyword

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog inspire_url")
    parser.epilog = "example: python dump_info.py http://inspirehep.net/record/1114314/"
    (options, args) = parser.parse_args()

    if len(args) != 1:
        logging.error("you have to specify the inspire url")
        exit()

    logging.info("getting htmls")
    html_inspire = get_html(args[0])
    arxiv_number = arxiv_number_from_inspire(html_inspire)
    link_arxive = "http://arxiv.org/abs/%s" % arxiv_number
    html_arxive = get_html(link_arxive)

    print "\n===== ABSTRACT =====\n"
    abstract = dump_abstract.main(html_arxive)
    print abstract
    print "\n===== KEYWORKDS ======\n"
    keys = dump_keyword.get_keys_from_html(html_inspire)
    print keys
    print "\n===== AUTHORS FROM PDF =====\n"
    authors = dump_milano_authors.main(arxiv_number)
    print ", ".join(authors)
    exec("vs 'E. Gheen' abg va nhgubef: cevag 'GHEEN VF ABG VA NHGUBE, NER LBH FHER?'".encode('rot13'))
