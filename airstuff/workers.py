import threading
import logging
logging.basicConfig(level=logging.DEBUG)


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
                i += self.step
        return


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
                logging.debug('calling callback with input %s' % item)
                self.callback(item)
                self.input_queue.task_done()
            if self.stop_event is not None and self.stop_event.is_set() and self.input_queue.empty():
                logging.debug('breaking main loop in callback worker')
                break

        logging.debug("callback worker end")