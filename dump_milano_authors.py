#!/usr/bin/env python

#mac cmd = 'echo %s | tr -d "\n" | pbcopy' % str
# os.system(cmd)
#linux 

__doc__ = "simple tool to dump the Milano author list"
__author__ = "Ruggero Turra"
__email__ = "ruggero.turra@mi.infn.it"

import logging
import StringIO
import urllib2
import os.path
import re
import sys

logging.basicConfig(level=logging.DEBUG)

try:
    from pdfminer.converter import TextConverter
    from pdfminer.layout import LAParams
    from pdfminer.pdfinterp import PDFResourceManager, process_pdf
except ImportError:
    logging.error("""You have to install pdfminer from http://www.unixuser.org/~euske/python/pdfminer/index.html.
wget http://pypi.python.org/packages/source/p/pdfminer/pdfminer-20110515.tar.gz#md5=f3905f801ed469900d9e5af959c7631a
tar xvzf pdfminer-20110515.tar.gz
cd pdfminer-20110515/
su
python setup.py install
""")


def get_text(pdf_filename):
    outfp = StringIO.StringIO()
    rsrcmgr = PDFResourceManager(caching=True)
    device = TextConverter(rsrcmgr, outfp, codec='utf-8', laparams=LAParams())
    pagenos = set()
    fp = open(pdf_filename, 'r')
    process_pdf(rsrcmgr, device, fp, pagenos, check_extractable=True)
    text = outfp.getvalue()
    return text


def get_pdf_url(html, url):
    logging.debug("searching pdf link")
    start = html.find("PDF</a>")
    m = re.search(' \| .*?href="(.+?)">PDF</a>', html[start-500:start+100])
    if m is None:
        logging.error("cannot find link into html")
        exit()
    logging.debug("pdf link found: %s", m.group(1))
    from urlparse import urljoin
    return urljoin(url, m.group(1))


def download_file(url, filename):
    f = open(filename, 'wb')
    u = urllib2.urlopen(url)
    logging.debug("downloading %s", url)
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8) * (len(status) + 1)
        print >> sys.stderr, status,
    f.close()
    sys.stdout.flush()


def main(arxiv_number):
    url_pdf = "http://arxiv.org/pdf/%s.pdf" % arxiv_number

    import tempfile
    pdf_filename = os.path.join(tempfile.gettempdir(), url_pdf.split('/')[-1])
    logging.info("dowloading pdf from %s to %s", url_pdf, pdf_filename)
    download_file(url_pdf, pdf_filename)
    logging.info("converting pdf to txt, patience")
    text = get_text(pdf_filename)

    ftext = open("text", "w")
    ftext.write(text)
    logging.info("parsing txt")
#    print text
    m = re.search("([0-9]+).*?\(([ab])\) ?Dipartimento\sdi\sFisica,\sUniversit ?`a\sdi\sMilano,\sMilano", text)

    if m is None:
        logging.error("Cannot find Milano in this paper")
        exit()
    milano_tag = m.group(1) + m.group(2)
    logging.info("found milano tag: %s", milano_tag)
    authors = re.findall("([A-Za-z\. ]+)[0-9ab,]*?" + milano_tag, text)
#    all_authors = re.findall("((?:[A-Z]\.)+ [A-Z][\w ]+)[0-9]+[abcdef]* [\.,]", text, re.UNICODE)
#    all_authors = re.findall("((?:[A-Z]\.)+ [^0-9]+?)[0-9]+[abcdef]*(?: ,| \.)", text, re.UNICODE)


#    print ", ".join([author.strip() for author in all_authors])
#    print len(all_authors)
 #   logging.info("found %d authors", len(authors))
    return [author.strip() for author in authors]


if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog arxiv_number")
    parser.epilog = "example: python dump_milano_authors.py 1208.0572"
    (options, args) = parser.parse_args()

    if len(args) != 1:
        logging.error("you have to specify the arxiv url")
        exit()

    print "\n".join(main(args[0]))

"""
(2005), [arXiv:hep-ph/0508020].

The ATLAS Collaboration

G. Aad48 , T. Aba jyan21 , A.B. Pippo32 , B. Abbott112 , J. Abdallah12 , S. Abdel Khalek116 , O. Abdinov11 , R. Aben106 , B. Abi113 ,
"""
