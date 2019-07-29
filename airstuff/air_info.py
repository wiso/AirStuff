import gi
gi.require_version('Gtk', '3.0')
import colorlog
from gi.repository import Gtk, Gdk
from airstuff.wos import get_wos_from_doi
from airstuff.inspire import query_inspire, fix_info
from airstuff.scopus import get_eid_from_doi
from airstuff import driver_air
from airstuff import journals

logger = colorlog.getLogger('airstuff.info')


class WindowDoi(Gtk.Window):

    def __init__(self, doi=None, institute=None, additional_authors=None):
        Gtk.Window.__init__(self, title="Air Stuff")

        self.info = None
        self.additional_authors = additional_authors

        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.browser_name = 'chrome'

        self.set_size_request(1000, 500)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)

        doi_box, _, self.entry_doi = self.create_row("DOI")
        find_button = Gtk.Button.new_with_label("Search")
        find_button.connect("clicked", self.search_doi)
        doi_box.pack_start(find_button, True, True, 0)
        main_box.pack_start(doi_box, True, True, 0)

        institute_box, _, self.entry_institute = self.create_row('institute')
        main_box.pack_start(institute_box, True, True, 0)

        title_box, _, self.entry_title = self.create_row("title", copy=True)
        main_box.pack_start(title_box, True, True, 0)

        selected_authors_box = Gtk.Box()
        selected_authors_box.pack_start(Gtk.Label(label='selected authors'), True, True, 0)
        scrolledwindow = Gtk.ScrolledWindow()
        scrolledwindow.set_hexpand(True)
        scrolledwindow.set_vexpand(True)
        self.selected_authors_textview = Gtk.TextView()
        self.selected_authors_textbuffer = self.selected_authors_textview.get_buffer()
        scrolledwindow.add(self.selected_authors_textview)
        selected_authors_box.pack_start(scrolledwindow, True, True, 0)
        main_box.pack_start(selected_authors_box, True, True, 0)
        button_copy = Gtk.Button.new_with_label('copy')
        button_copy.connect("clicked",
                            lambda w: self.clipboard.set_text(
                                self.selected_authors_textbuffer.get_text(
                                    self.selected_authors_textbuffer.get_start_iter(),
                                    self.selected_authors_textbuffer.get_end_iter(),
                                    True
                                ), -1))
        selected_authors_box.pack_start(button_copy, True, True, 0)

        keywords, _, self.entry_keyworkds = self.create_row('keywords', copy=True)
        main_box.pack_start(keywords, True, True, 0)

        scopus, _, self.entry_scopus = self.create_row('scopus', copy=True)
        main_box.pack_start(scopus, True, True, 0)

        wos, _, self.entry_wos = self.create_row('web of knoledge', copy=True)
        main_box.pack_start(wos, True, True, 0)

        pdf_url, _, self.entry_pdf_url = self.create_row('url link', copy=True)
        main_box.pack_start(pdf_url, True, True, 0)

        frame_selenium = Gtk.Frame(label='automatic insertion')
        main_box.pack_start(frame_selenium, True, True, 8)
        box_selenium = Gtk.Box()
        frame_selenium.add(box_selenium)

        button_chrome = Gtk.RadioButton.new_with_label_from_widget(None, "Chrome")
        button_chrome.connect("toggled", self.on_browser_toggled, "chrome")
        box_selenium.pack_start(button_chrome, False, False, 0)
        button_firefox = Gtk.RadioButton.new_with_label_from_widget(button_chrome, "Firefox")
        button_firefox.connect("toggled", self.on_browser_toggled, "firefox")
        box_selenium.pack_start(button_firefox, False, False, 0)

        button_login_selenium = Gtk.Button(label='login to AIR')
        button_login_selenium.connect('clicked', self.login_selenium)
        box_selenium.pack_start(button_login_selenium, True, True, 0)

        button_start_selenium = Gtk.Button(label='insert from doi')
        button_start_selenium.connect('clicked', self.start_selenium)
        box_selenium.pack_start(button_start_selenium, True, True, 0)

        self.button_pause = Gtk.CheckButton()
        self.button_pause.set_label("Wait after each page")
        box_selenium.pack_start(self.button_pause, True, True, 0)
        self.button_pause.set_active(True)

        if institute is not None:
            self.entry_institute.set_text(institute)

        if doi is not None:
            self.entry_doi.set_text(doi)
            self.search_doi(self)

    def create_row(self, label, copy=False):
        box = Gtk.Box()
        label = Gtk.Label(label=label)
        entry = Gtk.Entry()
        box.pack_start(label, True, True, 0)
        box.pack_start(entry, True, True, 0)

        if copy:
            button_copy = Gtk.Button.new_with_label('copy')
            button_copy.connect("clicked", lambda w: self.clipboard.set_text(entry.get_text(), -1))
            box.pack_start(button_copy, True, True, 0)

        return box, label, entry

    def search_doi(self, widget):
        doi = self.entry_doi.get_text()
        info = query_inspire("doi:%s" % doi)
        if not info == 0:
            pass
        if len(info) > 1:
            pass
        info = self.info = fix_info(info[0])

        self.entry_title.set_text(info['title'])

        all_authors = ';'.join([author['full_name'] for author in info['authors']])

        selected_institutes = set([self.entry_institute.get_text()])
        if not selected_institutes:
            logger.warning('no institute specified')

        selected_authors = [author['full_name'] for author in info['authors']
                            if selected_institutes.intersection(set(author.get('affiliation', [])))]
        self.info['local_authors'] = selected_authors
        if self.additional_authors is not None:
            logger.debug('adding additional authors %s', self.additional_authors)
            for aa in self.additional_authors:
                if aa in self.info['local_authors']:
                    logger.warning('additional author %s already present', aa)
                else:
                    self.info['local_authors'].append(aa)
        if not selected_authors:
            logger.warning('no author found for institute %s', selected_institutes)

        self.selected_authors_textbuffer.set_text('\n'.join(selected_authors))

        eid = get_eid_from_doi(doi)
        if eid is not None:
            self.entry_scopus.set_text(eid)
            info['scopus'] = eid

        wos = get_wos_from_doi(doi)
        if wos is not None:
            info['wos'] = wos
            self.entry_wos.set_text(wos)

        if 'thesaurus_terms' in info:
            keywords = [k['term'] for k in info['thesaurus_terms'] if 'term' in k]
            self.entry_keyworkds.set_text(';'.join(keywords))

        logger.info('getting url from journal')
        pdf_url = journals.get_pdf_url(doi)
        if pdf_url:
            info['pdf_url'] = pdf_url
            self.entry_pdf_url.set_text(pdf_url)

    @property
    def driver(self):
        if hasattr(self, '_driver') and self._driver is not None and self._driver.name == self.browser_name:
            return self._driver
        else:
            self._driver = driver_air.get_driver(debug=True, driver=self.browser_name)
            return self._driver

    def login_selenium(self, widget):
        driver_air.login(self.driver)

    def on_browser_toggled(self, button, value):
        self.browser_name = value

    def start_selenium(self, widget):
        r = driver_air.upload_from_doi(self.driver, self.info, pause=self.button_pause.get_active())
        if r == driver_air.ReturnValue.DUPLICATE:
            logger.warning('do not create duplicate')
            doi = self.info['doi']
            if type(doi) == list:
                doi = doi[0]
            self.ignore_in_future(doi)
        d = self.driver
        d.close()
        del d

    def ignore_in_future(self, doi):
        with open('blacklist.txt', 'a') as f:
            f.write('%s\n' % doi)


def app_main(doi=None, institute=None):
    win = WindowDoi(doi, institute)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Insert information on air')
    parser.add_argument("doi", nargs='?', default=None)
    parser.add_argument('--institute')
    args = parser.parse_args()

    app_main(args.doi, args.institute)
    Gtk.main()
