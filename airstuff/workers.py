import threading
import logging
import colorlog
logger = colorlog.getLogger('airstuff.driverair')


class OffsetsProducer(threading.Thread):
    def __init__(self, input_queue, step, stop_event=None):
        super(OffsetsProducer, self).__init__()
        self.step = step
        self.input_queue = input_queue
        self.stop_event = stop_event

    def run(self):
        i = 0
        while self.stop_event is None or not self.stop_event.is_set():
            if not self.input_queue.full():
                logging.debug("adding %d", i)
                self.input_queue.put(i)
                logging.debug('added %d', i)
                i += self.step
        logging.debug('producer end')
        return


class DuplicateFilter(threading.Thread):
    added = []
    lock_duplicated = threading.Lock()

    def __init__(self, input_queue, output_queue, stop_event=None):
        super(DuplicateFilter, self).__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.stop_event = stop_event

    def run(self):
        while self.stop_event is None or not self.stop_event.is_set():
            if not self.input_queue.empty():
                item = self.input_queue.get()
                if item in self.added:
                    logging.warning('duplicate: %s', item)
                    self.input_queue.task_done()
                    continue
                with self.lock_duplicated:
                    self.added.append(item)
                self.input_queue.task_done()
                self.output_queue.put(item)


class CallBackConsumer(threading.Thread):
    def __init__(self, input_queue, callback, stop_event=None):
        super(CallBackConsumer, self).__init__()
        self.callback = callback
        self.input_queue = input_queue
        self.stop_event = stop_event

    def run(self):
        while True:
            if not self.input_queue.empty():
                item = self.input_queue.get()
                self.callback(item)
                self.input_queue.task_done()
            if self.stop_event is not None and self.stop_event.is_set() and self.input_queue.empty():
                logging.debug('breaking main loop in callback worker')
                break

        logging.debug("callback worker end")
