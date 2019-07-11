import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import threading
import queue
import time
from threading import Lock

import inspire


class MyWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="Hello World")

        self.set_default_size(1000, 350)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)

        box_inspire = Gtk.Box()
        main_box.add(box_inspire)

        self.button_start = Gtk.Button(label="start")
        self.button_start.connect("clicked", self.run_stop_inspire)
        self.inspire_running = False
        box_inspire.pack_start(self.button_start, True, True, 0)


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
            self.table_view.append_column(column)

        self.indico_query = None

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

    def run_inspire(self):
        lock = Lock()

        def f(item):
            with lock:
                self.debug(item)

        self.indico_query = inspire.IndicoQuery(callback=f)
        self.indico_query.run()

    def stop_inspire(self):
        self.indico_query.stop()
        self.indico_query = None

    def debug(self, item):
        msg = "%s\n" % item
        item = inspire.fix_info(item)
        self.table_store.append([item['doi'], str(item['title']), str(item['creation_date'])])

win = MyWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()