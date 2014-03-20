import logging
logging.basicConfig(level=logging.INFO)
import re

try:
    import xmltodict
except ImportError:
    print """
you have to install xmltodict:

su
pip install xmltodict
"""

from common import get_html
import dump_keyword


def format_name(author):
    name = author[1]
    surname = author[0]
    names = name.split()
    initials = "".join(["%s." % n[0] for n in names])
    return "%s %s" % (initials, surname)


def format_name_italian(author):
    name = author[1]
    surname = author[0]
    names = name.split()
    initials = "".join(["%s." % n[0] for n in names])
    return "%s, %s" % (surname, name)


def main(html_inspire, default_institution):
    m = re.search(r"/([0-9]+)", html_inspire)
    if m is None:
        raise ValueError("not valid html")
    inspire_number = m.group(1)
    url = "http://inspirehep.net/record/{0}/export/xn".format(inspire_number)
    xml = get_html(url)
    doc = xmltodict.parse(xml)

    authors = get_authors(doc)

    print "\n" + "=" * 10 + " ALL AUTHORS " + "=" * 10
    print ", ".join(map(format_name, authors))

    print "\n found %d authors" % len(authors)
    milan_authors = [author for author in authors if (default_institution in " ".join(author[2]))]

    print "\n" + "=" * 10 + (" %s AUTHORS " % default_institution) + "=" * 10
    print "\n".join(map(format_name_italian, milan_authors))

    print "\n" + "=" * 10 + " TITLE " + "=" * 10
    print get_title(doc)

    print "\n" + "=" * 10 + " ABSTRACT " + "=" * 10
    print get_abstract(doc)

    print "\n===== KEYWORKDS ======\n"
    keys = dump_keyword.get_keys_from_html(get_html(html_inspire))
    print keys


def get_abstract(xml_dict):
    return xml_dict['articles']['article']['front']['abstract']


def get_title(xml_dict):
    meta = xml_dict['articles']['article']['front']['article-meta']
    title = meta['title-group']['article-title']
    return title


def get_authors(xml_dict):
    authors = []

    meta = xml_dict['articles']['article']['front']['article-meta']
    title = meta['title-group']['article-title']
    contrib = meta['contrib-group']['contrib']
    for c in contrib:
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
    parser = OptionParser(usage="usage: %prog inspire_url")
    parser.epilog = "example: python dump_milano_authors.py http://inspirehep.net/record/1240088"
    parser.add_option("--institution", type=str, default="Milan U", help="which institution you want to find. Default = 'Milan U'")
    (options, args) = parser.parse_args()

    if len(args) != 1:
        logging.error("you have to specify the inspire url")
        exit()

    main(args[0], options.institution)
