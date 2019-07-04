import tkinter as tk

import threading
import queue
import time
from threading import Lock


class Producer(threading.Thread):
    def __init__(self, queue):
        super(Producer, self).__init__()
        self.running = True
        self.input_queue = queue

    def run(self):
        i = 0
        while self.running:
            if not self.input_queue.full():
                self.input_queue.put(i)
                i += 1
        return


class Consumer(threading.Thread):
    def __init__(self, input_queue, output_queue):
        super(Consumer, self).__init__()
        self.running = True
        self.input_queue = input_queue
        self.output_queue = output_queue

    def run(self):
        while self.running:
            if not self.input_queue.empty():
                item = self.input_queue.get()
                time.sleep(0.1)
                self.output_queue.put(item ** 2)
                self.input_queue.task_done()


class CallBackConsumer(threading.Thread):
    def __init__(self, input_queue, callback):
        super(CallBackConsumer, self).__init__()
        self.callback = callback
        self.input_queue = input_queue
        self.running = True

    def run(self):
        while True:
            if not self.input_queue.empty():
                item = self.input_queue.get()
                self.callback(item)
                self.input_queue.task_done()
            if not self.running and self.input_queue.empty():
                break


class Manager:
    def __init__(self, callback=None, buf_size=10):
        self.input_queue = queue.Queue(buf_size)
        self.output_queue = queue.Queue()
        self.all_producers = []
        self.all_workers = []
        self.callback = callback
        self.callback_worker = None
        self.status = 'stopped'

    def run(self):
        self.status = 'starting'
        p = Producer(self.input_queue)
        p.setDaemon(True)
        self.all_producers.append(p)

        for w in range(5):
            worker = Consumer(self.input_queue, self.output_queue)
            worker.setDaemon(True)
            self.all_workers.append(worker)
            worker.start()

        if self.callback is not None:
            self.callback_worker = CallBackConsumer(self.output_queue, self.callback)
            self.callback_worker.setDaemon(True)
            self.callback_worker.start()

        p.start()
        self.status = 'running'

    def stop(self):
        self.status = 'stopping'
        print('stopping producer')
        for i in range(len(self.all_producers)):
            self.all_producers[i].running = False
            self.all_producers[i].join()

        print('stopping consumer')
        for i in range(len(self.all_workers)):
            self.all_workers[i].running = False
            self.all_workers[i].join()

        if self.callback_worker is not None:
            self.callback_worker.running = False
            print('waiting callback worker to join')
            self.callback_worker.join()

        self.status = 'stopped'
        print('all stopped')


class Application(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.pack()
        self.create_widgets()
        self.task = None

    def create_widgets(self):
        self.button_run = tk.Button(self, text="run", command=self.run).pack()
        self.button_stop = tk.Button(self, text="stop", command=self.stop).pack()
        self.log = tk.Text(self)
        self.log.pack()

    def run(self):
        lock = Lock()

        def f(item):
            with lock:
                self.debug(item)

        self.task = Manager(callback=f)
        self.task.run()

    def stop(self):
        self.task.stop()
        self.task = None

    def debug(self, item):
        msg = "%d\n" % item
        self.log.insert(tk.INSERT, msg)  # commenting this line it works
        print(msg)


root = tk.Tk()
app = Application(master=root)
app.mainloop()