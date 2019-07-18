import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, GLib
from threading import Lock
import datetime
import inspire
from air import AirQuery
from air_info import WindowDoi
import logging
logging.basicConfig(level=logging.INFO)

lock = Lock()


class StatBox(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self)
        self.first_year = 2010
        self.years = ['?', '< %s' % self.first_year]
        self.years += [str(year) for year in range(self.first_year, datetime.date.today().year + 1)]
        self.data = {str(year): 0 for year in self.years}
        self.labels = {}
        self.layout_stat_box()

    def fill(self, year):
        if str(year) not in self.years:
            try:
                y = int(year)
                if y < self.first_year:
                    y = self.years[1]
                else:
                    y = '?'
            except ValueError:
                y = '?'
        else:
            y = str(year)

        self.data[y] += 1
        self.update_labels()

    def set_label(self, year, content):
        self.data[str(year)] = content
        self.update_labels()

    def reset(self):
        for year in self.years:
            self.data[str(year)] = 0
        self.update_labels()

    def update_labels(self):
        for year in self.years:
            self.labels[year].set_text("%s" % self.data[year])

    def layout_stat_box(self):
        for year in self.years:
            label_year = Gtk.Label(label="%s: " % year)
            label_number = Gtk.Label(label='0')
            self.labels[year] = label_number
            self.pack_start(label_year, True, True, 0)
            self.pack_start(label_number, True, True, 0)


class MyWindow(Gtk.Window):

    def __init__(self, air_file=None, inspire_file=None):
        Gtk.Window.__init__(self, title="Air Stuff")

        self.set_default_size(800, 350)
        self.create_interface()

        if air_file is not None:
            self.upload_air_from_file(air_file)
        if inspire_file is not None:
            self.upload_inspire_from_file(inspire_file)

    def create_interface(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)

        # inspire
        box_inspire = Gtk.Box()
        main_box.add(box_inspire)

        # buttons inpire
        self.button_start = Gtk.Button(label="search on inspire")
        self.button_start.connect("clicked", self.run_stop_inspire)
        self.inspire_running = False
        box_inspire.pack_start(self.button_start, True, True, 0)

        self.button_upload_inspire = Gtk.Button(label='upload from file')
        self.button_upload_inspire.connect("clicked", self.upload_inspire)
        box_inspire.pack_start(self.button_upload_inspire, True, True, 0)

        # inspire table
        box_table = Gtk.Box()
        main_box.add(box_table)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(
            Gtk.PolicyType.ALWAYS, Gtk.PolicyType.ALWAYS)
        sw.set_size_request(1000, 150)
        box_table.pack_start(sw, True, True, 0)

        self.table_inspire_store = Gtk.ListStore(str, str, str)
        self.table_view = Gtk.TreeView(model=self.table_inspire_store)
        sw.add(self.table_view)
        self.table_view.set_search_column(1)

        headers = 'doi', 'title', 'date'
        for i in range(3):
            column = Gtk.TreeViewColumn(headers[i], Gtk.CellRendererText(), text=i)
            column.set_sort_column_id(i)
            self.table_view.append_column(column)

        self.inspire_query = None

        # stat box inspire
        self.stat_box_inspire = StatBox()
        main_box.add(self.stat_box_inspire)

        # air button
        box_air = Gtk.Box()
        main_box.add(box_air)

        self.button_start_air = Gtk.Button(label="search on AIR")
        self.button_start_air.connect("clicked", self.run_stop_air)
        self.air_running = False
        box_air.pack_start(self.button_start_air, True, True, 0)

        self.button_upload_air = Gtk.Button(label='upload from file')
        self.button_upload_air.connect("clicked", self.upload_air)
        box_air.pack_start(self.button_upload_air, True, True, 0)


        # air table
        box_table_air = Gtk.Box()
        main_box.add(box_table_air)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(
            Gtk.PolicyType.ALWAYS, Gtk.PolicyType.ALWAYS)
        sw.set_size_request(1000, 150)
        box_table_air.pack_start(sw, True, True, 0)

        self.table_air_store = Gtk.ListStore(str, str, str)
        self.table_air_view = Gtk.TreeView(model=self.table_air_store)
        sw.add(self.table_air_view)
        self.table_air_view.set_search_column(1)

        headers = 'doi', 'title', 'year'
        for i in range(3):
            column = Gtk.TreeViewColumn(headers[i], Gtk.CellRendererText(), text=i)
            column.set_sort_column_id(i)
            self.table_air_view.append_column(column)

        self.stat_box_air = StatBox()
        main_box.add(self.stat_box_air)

        # diff buttons
        box_diff = Gtk.Box()
        button_diff = Gtk.Button(label='make diff')
        button_diff.connect('clicked', self.make_diff)
        box_diff.pack_start(button_diff, True, True, 0)
        main_box.add(box_diff)

        # diff table
        box_table_diff = Gtk.Box()
        main_box.add(box_table_diff)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(
            Gtk.PolicyType.ALWAYS, Gtk.PolicyType.ALWAYS)
        sw.set_size_request(1000, 150)
        box_table_diff.pack_start(sw, True, True, 0)

        self.table_diff_store = Gtk.ListStore(str, str, str)
        self.table_diff_view = Gtk.TreeView(model=self.table_diff_store)
        sw.add(self.table_diff_view)
        self.table_diff_view.set_search_column(1)

        headers = 'doi', 'title', 'date'
        for i in range(3):
            column = Gtk.TreeViewColumn(headers[i], Gtk.CellRendererText(), text=i)
            column.set_sort_column_id(i)
            self.table_diff_view.append_column(column)

        self.stat_box_diff = StatBox()
        main_box.add(self.stat_box_diff)

        # footer
        box_action = Gtk.Box()
        main_box.add(box_action)
        button_go = Gtk.Button(label='process selected')
        button_go.connect('clicked', self.go)
        box_action.pack_start(button_go, True, True, 0)

    def run_stop_inspire(self, widget):
        if self.inspire_running:
            self.button_start.get_children()[0].set_label('stopping')
            self.button_start.set_sensitive(False)
            self.stop_inspire()
            self.inspire_running = False
            self.button_start.get_children()[0].set_label('start')
            self.button_start.set_sensitive(True)
        else:
            self.button_start.get_children()[0].set_label('starting')
            self.button_start.set_sensitive(False)
            self.run_inspire()
            self.inspire_running = True
            self.button_start.get_children()[0].set_label('stop')
            self.button_start.set_sensitive(True)

    def run_stop_air(self, widget):
        if self.air_running:
            self.button_start_air.get_children()[0].set_label('stopping')
            self.button_start_air.set_sensitive(False)
            self.stop_air()
            self.air_running = False
            self.button_start_air.get_children()[0].set_label('start')
            self.button_start_air.set_sensitive(True)
        else:
            self.button_start_air.get_children()[0].set_label('starting')
            self.button_start_air.set_sensitive(False)
            self.run_air()
            self.air_running = True
            self.button_start_air.get_children()[0].set_label('stop')
            self.button_start_air.set_sensitive(True)

    def run_inspire(self):

        def f(item):
            with lock:
                GLib.idle_add(self.add_inspire, item)

        self.inspire_query = inspire.InspireQuery(query=inspire.ATLAS_QUERY, callback=f)
        self.inspire_query.run()

    def stop_inspire(self):
        self.inspire_query.stop()
        self.inspire_query = None

    def add_inspire(self, item):
        item = inspire.fix_info(item)
        self.table_inspire_store.append([item['doi'], str(item['title']), str(item['creation_date'])])
        self.stat_box_inspire.fill(item['creation_date'].year)

    def upload_inspire(self, item):
        dlg = Gtk.FileChooserDialog(title="Please choose a file",
                                    parent=self,
                                    action=Gtk.FileChooserAction.OPEN)
        dlg.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dlg.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        answer = dlg.run()
        fn = None
        try:
            if answer == Gtk.ResponseType.OK:
                fn = dlg.get_filename()
        finally:
            dlg.destroy()

        if not fn:
            return
        self.upload_inspire_from_file(fn)

    def upload_inspire_from_file(self, fn):
        with open(fn) as f:
            for line in f:
                row = line.split('\t')
                item = {'doi': row[0].strip(), 'title': row[1].strip(), 'creation_date': datetime.datetime.fromisoformat(row[2].strip())}
                self.add_inspire(item)

    def run_air(self):

        def f(item):
            GLib.idle_add(self.add_air, item)

        self.air_query = AirQuery('rp09852', callback=f, workers=10)
        self.air_query.run()

    def stop_air(self):
        self.air_query.stop()
        self.air_query = None

    def add_air(self, item):
        self.table_air_store.append([item['doi'], str(item['title']), str(item['year'])])
        self.stat_box_air.fill(item['year'])

    def upload_air(self, item):
        dlg = Gtk.FileChooserDialog(title="Please choose a file",
                                    parent=self,
                                    action=Gtk.FileChooserAction.OPEN)
        dlg.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dlg.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        answer = dlg.run()
        fn = None
        try:
            if answer == Gtk.ResponseType.OK:
                fn = dlg.get_filename()
        finally:
            dlg.destroy()

        if not fn:
            return
        self.upload_air_from_file(fn)

    def upload_air_from_file(self, fn):
        with open(fn) as f:
            for iline, line in enumerate(f, 1):
                row = line.split('\t')
                try:
                    item = {'doi': row[0].strip(), 'title': row[1].strip(), 'year': row[2].strip()}
                except IndexError:
                    logging.error('problem parsing %s:%d "%s"', fn, iline, line)
                self.add_air(item)

    def make_diff(self, widget):
        air_values = [list(row) for row in self.table_air_store]
        inspire_values = [list(row) for row in self.table_inspire_store]

        dois_air = set(v[0] for v in air_values)
        dois_inspire = set(v[0] for v in inspire_values)
        dois_diff = dois_inspire - dois_air

        info_diff = []
        for d in inspire_values:
            if d[0] in dois_diff:
                info_diff.append(d)

        for item in info_diff:
            self.table_diff_store.append([item[0], str(item[1]), str(item[2])])
            self.stat_box_diff.fill(datetime.datetime.fromisoformat(item[2]).year)

    def go(self, widget):
        index_selected = self.table_diff_view.get_selection().get_selected_rows()
        if not index_selected[1]:
            return
        doi = self.table_diff_store[index_selected[1][0][0]][0]
        new_window = WindowDoi(doi=doi, institute="Milan U.")
        new_window.show_all()


def app_main(args):
    win = MyWindow(air_file=args.air_file, inspire_file=args.inspire_file)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Air Stuff')
    parser.add_argument('--air-file', help='txt file with air entries')
    parser.add_argument('--inspire-file', help='txt file with inspire entries')
    args = parser.parse_args()

    import threading
    threading.Thread(target=lambda: None).start()
    GObject.threads_init()

    app_main(args)
    Gtk.main()