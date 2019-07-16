import logging
logging.basicConfig(level=logging.INFO)
import re
import xmltodict

from common import get_html
import dump_keyword

from tkinter import *


def format_name(author):
    name = author[1]
    surname = author[0]
    names = name.split()
    initials = "".join(["%s." % n[0] for n in names])
    return "%s %s" % (initials, surname)


def format_name_italian(author):
    name = author[1]
    surname = author[0]
    return "%s, %s" % (surname, name)


def parse(html_inspire, default_institution):
    m = re.search(r"/([0-9]+)", html_inspire)
    if m is None:
        raise ValueError("not valid html")
    inspire_number = m.group(1)
    url = "http://inspirehep.net/record/{0}/export/xn".format(inspire_number)
    xml = get_html(url)
    doc = xmltodict.parse(xml)

    authors = get_authors(doc)

    print("\n" + "=" * 10 + " ALL AUTHORS " + "=" * 10)
    authors_list = ", ".join(map(format_name, authors))
    print(authors_list)

    print("\n found %d authors" % len(authors))
    milan_authors = [author for author in authors if (default_institution in " ".join(author[2]))]

    print("\n" + "=" * 10 + (" %s AUTHORS " % default_institution) + "=" * 10)
    milan_list = "\n".join(map(format_name_italian, milan_authors))
    print(milan_list)

    print("\n" + "=" * 10 + " TITLE " + "=" * 10)
    title = get_title(doc)
    print(title)

    print("\n" + "=" * 10 + " ABSTRACT " + "=" * 10)
    abstract = get_abstract(doc)
    print(abstract)

    print("\n===== KEYWORKDS ======\n")
    keys = dump_keyword.get_keys_from_html(get_html(html_inspire))
    print(keys)

    return authors_list, milan_list, title, abstract, keys


def get_abstract(xml_dict):
    return xml_dict['articles']['article']['front']['abstract']


def get_title(xml_dict):
    meta = xml_dict['articles']['article']['front']['article-meta']
    title = meta['title-group']['article-title']
    return title


def get_authors(xml_dict):
    authors = []

    meta = xml_dict['articles']['article']['front']['article-meta']
    contrib = meta['contrib-group']['contrib']
    for c in contrib:
        author_institutions = []
        try:
            aff = c["aff"]
            if len(aff) == 1:
                author_institutions.append(aff["institution"])
            else:
                for a in aff:
                    author_institutions.append(a["institution"])

        except KeyError:
            logging.warning("author %s %s has no institution, check manually" % (c["name"]["surname"], c["name"]["given-names"]))
            author_intitutions = ["unknown"]
                        

        authors.append((c["name"]["surname"],
                        c["name"]["given-names"],
                        author_institutions))
    return authors


class Application(Frame):
    def run(self):
        url = self.input_inspirehep.get()

        self.text_titles.delete("1.0", END)
        self.text_all_authors.delete("1.0", END)
        self.text_milan_authors.delete("1.0", END)
        self.text_abstract.delete("1.0", END)
        self.text_keywords.delete("1.0", END)

        authors_list, milan_list, title, abstract, keys = parse(url,
                                                               self.institution)
        
        self.text_titles.insert(INSERT, title)
        self.text_all_authors.insert(INSERT, authors_list)
        self.text_milan_authors.insert(INSERT, milan_list)
        self.text_abstract.insert(INSERT, abstract)
        self.text_keywords.insert(INSERT, keys)

    def say_hi(self):
        print("hi there, everyone!")

    def copy(self, widget):
        text = widget.get("1.0", END)
        self.clipboard_clear()
        self.clipboard_append(text)

    def createWidgets(self, url):
        self.label_input = Label(self, text="inspirehep url:")
        self.label_input.grid(row=0, sticky=W)
        self.input_inspirehep = Entry(self)
        self.input_inspirehep.configure(width=50)
        self.input_inspirehep.grid(row=0, column=1)
        self.input_inspirehep.insert(INSERT, url)
        self.button_run = Button(self, text="run", command=self.run)
        self.button_run.grid(row=0, column=2)

        self.text_titles = Text(self)
        self.text_titles.config(height=2)
        self.text_titles.grid(row=1, sticky=N, columnspan=2)
        self.copy_button_titles = Button(self, text="copy",
                                         command=lambda: self.copy(self.text_titles))
        self.copy_button_titles.grid(row=1, column=2)

        self.text_all_authors = Text(self)
        self.text_all_authors.config(height=10)
        self.text_all_authors.grid(row=2, sticky=N, columnspan=2)
        self.copy_button_all_authors = Button(self, text="copy",
                                              command=lambda: self.copy(self.text_all_authors))
        self.copy_button_all_authors.grid(row=2, column=2)

        self.text_milan_authors = Text(self)
        self.text_milan_authors.config(height=10)
        self.text_milan_authors.grid(row=3, sticky=N, columnspan=2)
        self.copy_button_milan_authors = Button(self, text="copy",
                                                command=lambda: self.copy(self.text_milan_authors))
        self.copy_button_milan_authors.grid(row=3, column=2)

        self.text_abstract = Text(self)
        self.text_abstract.config(height=10)
        self.text_abstract.grid(row=4, sticky=N, columnspan=2)
        self.copy_button_milan_authors = Button(self, text="copy",
                                                command=lambda: self.copy(self.text_abstract))
        self.copy_button_milan_authors.grid(row=4, column=2)

        self.text_keywords = Text(self)
        self.text_keywords.config(height=10)
        self.text_keywords.grid(row=4, sticky=N, columnspan=2)
        self.copy_button_milan_authors = Button(self, text="copy",
                                                command=lambda: self.copy(self.text_keywords))
        self.copy_button_milan_authors.grid(row=4, column=2)

    def __init__(self, url, institution, master=None):
        Frame.__init__(self, master)
        self.institution = institution
        self.pack()
        self.createWidgets(url)


def main():
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog inspire_url")
    parser.epilog = "example: parse_inspire.py http://inspirehep.net/record/1240088"
    parser.add_option("--institution", type=str, default="Milan U", help="which institution you want to find. Default = 'Milan U'")
    parser.add_option("--no-gui", action="store_true", default=False, help="do no show GUI")
    (options, args) = parser.parse_args()

    if options.no_gui:
        parse(args[0], options.institution)
        exit()

    root = Tk()
    app = Application(args[0] if len(args) else "",
                      institution=options.institution, master=root)
    app.mainloop()
    root.destroy()


if __name__ == '__main__':
    main()