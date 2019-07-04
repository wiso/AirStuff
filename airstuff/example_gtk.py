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

        box_inspire = Gtk.Box()
        self.add(box_inspire)

        self.grid = Gtk.Grid()
        self.add(self.grid)

        self.button_start = Gtk.Button(label="start")
        self.button_start.connect("clicked", self.run)
        #self.grid.attach(self.button_start, 0, 1, 1, 1)
        box_inspire.pack_start(self.button_start, True, True, 0)
        self.button_stop = Gtk.Button(label="stop")
        self.button_stop.connect("clicked", self.stop)
        #self.grid.attach(self.button_stop, 1, 1, 1, 1)
        box_inspire.pack_start(self.button_stop, True, True, 0)

        sw = Gtk.ScrolledWindow()
        self.grid.attach(sw, 0, 2, 2, 1)
        self.table_store = Gtk.ListStore(str, str, str)
        self.table_view = Gtk.TreeView(model=self.table_store)
        sw.add(self.table_view)

        headers = 'doi', 'title', 'date'
        for i in range(3):
            column = Gtk.TreeViewColumn(headers[i], Gtk.CellRendererText(), text=i)
            self.table_view.append_column(column)

        self.indico_query = None

        self.frame_air = Gtk.Frame()
        self.grid.attach(self.frame_air, 1, 3, 1, 1)

    def run(self, widget):
        lock = Lock()

        def f(item):
            with lock:
                self.debug(item)

        self.indico_query = inspire.IndicoQuery(callback=f)
        self.indico_query.run()

    def stop(self, widget):
        self.indico_query.stop()
        self.indico_query = None

    def debug(self, item):
        msg = "%s\n" % item
        item = inspire.fix_info(item)
        self.table_store.append([item['doi'], str(item['title']), str(item['creation_date'])])

        print(msg)

win = MyWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()