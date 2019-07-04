# https://labs.inspirehep.net/api/literature?sort=mostrecent&size=25&q=&collaboration=ATLAS
# https://labs.inspirehep.net/api/literature?sort=mostrecent&size=25&q=&collaboration=ATLAS&doc_type=peer%20reviewed
# https://labs.inspirehep.net/api/literature?sort=mostrecent&size=25&q=&collaboration=ATLAS&doc_type=peer%20reviewed&page=2

import requests
import json
from multiprocessing.pool import ThreadPool
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("bibtexparser").setLevel(logging.WARNING)

URL_SEARCH = "http://inspirehep.net/search"


def query_inspire(search, rg, sc, ot=None):
    ot = ot or ['recid', 'creation_date', 'number_of_authors', 'system_control_number', 'doi', 'title']
    r = requests.get(URL_SEARCH,
                     params=dict(
                         of='recjson',             # json format
                         rg=rg,                    # range
                         action_search="Search",
                         sc=sc,                    # offset
                         do='d',
                         ot=ot,                    # ouput tags
                         sf='earliestdate',        # sorting
                         so='d',                   # descending
                         p=search))
    logging.debug('querying %s' % r.url)
    try:
        j = json.loads(r.text)
    except json.decoder.JSONDecodeError:
        logging.error("problem decoding", r.text)
        return None
    return j


def fix_info(info):
    if 'doi' in info:
        if type(info['doi']) is list:
            if len(set(info['doi'])) == 1:
                info['doi'] = info['doi'][0]
    if 'title' in info:
        if type(info['title']) is dict:
            info['title'] = info['title']['title']
    return info


def get_all_collaboration(collaboration, infos=None):
    infos = infos or ['recid', 'creation_date', 'number_of_authors', 'system_control_number', 'doi', 'title']
    nthread = 10
    shift = 20
    offset = 0

    def get(offset):
        search = "collaboration:'%s' AND collection:published" % collaboration
        return query_inspire(search, shift, offset, infos)

    while True:
        offset_bunch = []
        for b in range(nthread):
            offset_bunch.append(offset)
            offset += shift
        with ThreadPool(nthread) as pool:
            r = pool.map(get, offset_bunch)
            for rr in r:
                dobreak = False
                for rrr in rr:
                    yield fix_info(rrr)
                if not rr:
                    dobreak = True
            if dobreak:
                break


import threading
import queue


class OffsetProducer(threading.Thread):
    def __init__(self, input_queue, step):
        super(OffsetProducer, self).__init__()
        self.step = step
        self.input_queue = input_queue
        self.running = True

    def run(self):
        i = 0
        while self.running:
            if not self.input_queue.full():
                logging.debug("adding %d, running=%s" % (i, self.running))
                self.input_queue.put(i)
                i += self.step
        return


class InspireConsumer(threading.Thread):
    def __init__(self, input_queue, output_queue, search, step, infos=None):
        super(InspireConsumer, self).__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.search = search
        self.step = step
        self.running = True
        self.infos = infos or ['recid', 'creation_date', 'number_of_authors', 'system_control_number', 'doi', 'title']

    def run(self):
        while self.running:
            if not self.input_queue.empty():
                offset = self.input_queue.get()
                r = query_inspire(self.search, self.step, offset, self.infos)

                for rr in r:
                    self.output_queue.put(fix_info(rr))

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
                logging.debug('calling callback with input %s' % item)
                self.callback(item)
                self.input_queue.task_done()
            if not self.running and self.input_queue.empty():
                break

        logging.debug("callback worker end")


class IndicoQuery():
    def __init__(self, search="collaboration:'ATLAS' AND collection:published", callback=None, buf_size=10):
        self.input_queue = queue.Queue(buf_size)
        self.output_queue = queue.Queue()
        self.search = search
        self.buf_size = buf_size
        self.all_producers = []
        self.all_workers = []
        self.callback = callback
        self.callback_worker = None
        self.status = 'stopped'

    def run(self):
        self.status = 'starting'
        p = OffsetProducer(self.input_queue, self.buf_size)
        p.setDaemon(True)
        self.all_producers.append(p)

        for w in range(5):
            worker = InspireConsumer(self.input_queue, self.output_queue, self.search, self.buf_size)
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
        logging.debug('stopping producer')
        for i in range(len(self.all_producers)):
            self.all_producers[i].running = False
            self.all_producers[i].join()

        logging.debug('stopping consumer')
        for i in range(len(self.all_workers)):
            self.all_workers[i].running = False
            self.all_workers[i].join()

        if self.callback_worker is not None:
            logging.debug('stopping callback')
            self.callback_worker.running = False
            logging.debug('waiting callback worker to join')
            self.callback_worker.join()

        self.status = 'stopped'
        logging.debug('all stopped')



if __name__ == '__main__':

    def callback(item):
        print(item)

    q = IndicoQuery(callback=callback)
    q.run()
    print("running")
    print("sleeping")
    import time
    time.sleep(3)
    print("stopping")
    q.stop()
    print("stopped")
    #for x in get_all_collaboration('ATLAS'):
    #    print(x['creation_date'], x['doi'], x['title'])