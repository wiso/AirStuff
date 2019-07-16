import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, GLib
from threading import Lock
import datetime
import inspire
from air import AirQuery

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

    def __init__(self):
        Gtk.Window.__init__(self, title="Air Stuff")

        self.set_default_size(1000, 350)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)

        # inspire
        box_inspire = Gtk.Box()
        main_box.add(box_inspire)

        # buttons inpire
        self.button_start = Gtk.Button(label="start")
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
        sw.set_size_request(1000, 200)
        box_table.pack_start(sw, True, True, 0)

        self.table_store = Gtk.ListStore(str, str, str)
        self.table_view = Gtk.TreeView(model=self.table_store)
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

        self.button_start_air = Gtk.Button(label="start")
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
        sw.set_size_request(1000, 200)
        box_table_air.pack_start(sw, True, True, 0)

        self.table_air_store = Gtk.ListStore(str, str, str)
        self.table_air_view = Gtk.TreeView(model=self.table_air_store)
        sw.add(self.table_air_view)
        self.table_view.set_search_column(1)

        headers = 'doi', 'title', 'year'
        for i in range(3):
            column = Gtk.TreeViewColumn(headers[i], Gtk.CellRendererText(), text=i)
            self.table_air_view.append_column(column)

        self.stat_box_air = StatBox()
        main_box.add(self.stat_box_air)

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

        self.inspire_query = inspire.InspireQuery(query="collaboration:'ATLAS' AND collection:published", callback=f)
        self.inspire_query.run()

    def stop_inspire(self):
        self.inspire_query.stop()
        self.inspire_query = None

    def add_inspire(self, item):
        item = inspire.fix_info(item)
        self.table_store.append([item['doi'], str(item['title']), str(item['creation_date'])])
        self.stat_box_inspire.fill(item['creation_date'].year)

    def upload_inspire(self, item):
        dlg = Gtk.FileChooserDialog(title="Please choose a file",
                                    parent=self,
                                    action=Gtk.FileChooserAction.OPEN)
        dlg.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dlg.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        answer = dlg.run()
        try:
            if answer == Gtk.ResponseType.OK:
                print(dlg.get_filename())
        finally:
            dlg.destroy() 

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
        try:
            if answer == Gtk.ResponseType.OK:
                print(dlg.get_filename())
        finally:
            dlg.destroy() 


def app_main():
    win = MyWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()


if __name__ == '__main__':
    import threading
    threading.Thread(target=lambda: None).start()
    GObject.threads_init()

    app_main()
    Gtk.main()