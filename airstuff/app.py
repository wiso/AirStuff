import tkinter as tk
from tkinter import ttk
import logging
logging.basicConfig(level=logging.DEBUG)

import inspire
from threading import Lock


class Application(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.pack()
        self.create_widgets()

        self.indico_query = None

    def create_widgets(self):
        self.label_input = tk.Label(self, text="inspirehep query:")
        self.label_input.grid(row=0, sticky=tk.W)
        self.input_inspirehep = tk.Entry(self)
        self.input_inspirehep.configure(width=50)
        self.input_inspirehep.grid(row=0, column=1)
        self.input_inspirehep.insert(tk.INSERT, "collaboration:'ATLAS' AND collection:published")
        self.button_run = tk.Button(self, text="run", command=self.run_search_inspire)
        self.button_run.grid(row=0, column=2)
        self.button_stop = tk.Button(self, text="stop", command=self.stop_search_inspire)
        self.button_stop.grid(row=0, column=3)

        cols = 'Date', 'Title', 'doi'
        self.table = ttk.Treeview(self, columns=cols, show='headings')
        # set column headings
        for col in cols:
            self.table.heading(col, text=col)    
        self.table.grid(row=1, column=0, columnspan=3)

        self.table_index = 1

        self.button_login = tk.Button(self, text="login", command=self.air_login)
        self.button_login.grid(row=2, column=0)

        self.button_values = tk.Button(self, text="get values", command=self.air_login)
        self.button_values.grid(row=2, column=1)

        self.button_upload = tk.Button(self, text="upload", command=self.air_login)
        self.button_upload.grid(row=2, column=2)

        self.log = tk.Text(self)
        self.log.grid(row=3, column=0, columnspan=3)

    def run_search_inspire(self):
        self.button_run.config(state="disabled")
        self.master.update()

        lock = Lock()

        def f(item):
            with lock:
                self.update_table(item)
                self.button_stop.update_idletasks()
                self.button_run.update_idletasks()

        #self.indico_query = inspire.IndicoQuery(callback=f)
        #self.indico_query.run()

        self.indico_query = inspire.IndicoQuery()
        self.indico_query.run()

        while self.indico_query.status != 'stopped':
            if not self.indico_query.output_queue.empty():
                item = self.indico_query.output_queue.get()
                self.update_table(item)
                self.button_stop.update_idletasks()
                self.button_run.update_idletasks()

    def update_table(self, item):
        logging.debug('adding to table %s' % item)
        self.table.insert("", self.table_index, self.table_index,
                          values=(item['doi'], item['title']))
        self.table_index += 1

    def stop_search_inspire(self):
        self.indico_query.stop()
        self.indico_query = None
        self.button_run.config(state="enabled")
        self.log.insert(tk.INSERT, "Found %d entries from inspirehep\n" % self.table_index)

    def air_login(self):
        pass


def main():
    root = tk.Tk()
    app = Application(master=root)
    app.master.title("Automate AIR")
    app.master.maxsize(1000, 400)

    app.mainloop()

if __name__ == "__main__":
    main()