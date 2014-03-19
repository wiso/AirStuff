from common import get_html
import logging
logging.basicConfig(level=logging.INFO)

try:
    import xmltodict
except ImportError:
    print """
you have to install xmltodict:

su
pip install xmltodict
"""


def main(inspire_number):
    url = "http://inspirehep.net/record/{0}/export/xn".format(inspire_number)
    xml = get_html(url)
    doc = xmltodict.parse(xml)

    authors = get_authors(doc)
    print "found %d authors" % len(authors)
    milan_authors = [author for author in authors if ("Milan U" in " ".join(author[2]))]

    print "=" * 10  + " MILANO AUTHORS " + "=" * 10
    for ma in milan_authors:
        print "%s %s" % (ma[0], ma[1])


def get_authors(xml_dict):
    authors = []

    meta = xml_dict['articles']['article']['front']['article-meta']
    title = meta['title-group']['article-title']
    contrib = meta['contrib-group']['contrib']
    for c in contrib[10:]:
        author_institutions = []
        aff = c["aff"]
        if len(aff) == 1:
            author_institutions.append(aff["institution"])
        else:
            for a in aff:
                author_institutions.append(a["institution"])

        authors.append((c["name"]["surname"],
                        c["name"]["given-names"],
                        author_institutions))
    return authors


if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog inspire_number")
    parser.epilog = "example: python dump_milano_authors.py 1240088"
    (options, args) = parser.parse_args()

    if len(args) != 1:
        logging.error("you have to specify the inspire url")
        exit()

    main(args[0])
