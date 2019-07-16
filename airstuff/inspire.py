# https://labs.inspirehep.net/api/literature?sort=mostrecent&size=25&q=&collaboration=ATLAS
# https://labs.inspirehep.net/api/literature?sort=mostrecent&size=25&q=&collaboration=ATLAS&doc_type=peer%20reviewed
# https://labs.inspirehep.net/api/literature?sort=mostrecent&size=25&q=&collaboration=ATLAS&doc_type=peer%20reviewed&page=2

import requests
import json
from multiprocessing.pool import ThreadPool
import logging
from datetime import datetime
from workers import OffsetsProducer, CallBackConsumer
logging.basicConfig(level=logging.INFO)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("bibtexparser").setLevel(logging.WARNING)

URL_SEARCH = "http://inspirehep.net/search"


def query_inspire(query, rg=100, jrec=1, ot=None):
    # see http://inspirehep.net/help/hacking/search-engine-api
    r = requests.get(URL_SEARCH,
                     params=dict(
                         of='recjson',             # json format
                         rg=rg,                    # range
                         action_search="Search",
                         jrec=jrec,                # offset
                         do='d',
                         ot=ot,                    # ouput tags
                         sf='earliestdate',        # sorting
                         so='d',                   # descending
                         p=query))
    logging.debug('querying %s' % r.url)
    try:
        j = json.loads(r.text)
    except json.decoder.JSONDecodeError:
        logging.error("problem decoding", r.text)
        return None
    return j


def fix_title(title):
    if type(title) is str and title:
        return title
    elif type(title) is str and len(title) == 0:
        return 'NO TITLE'
    elif title is None:
        return 'NO TITLE'
    elif type(title) is dict:
        return title['title']
    elif type(title) is list:
        s = set(t['title'].replace('$', '') for t in title)
        if len(s) == 1:
            title = title[0]['title']
            return title
        else:
            return title[0]['title']  # too complicated (difference is in latex style)
    else:
        logging.warning('cannot parse this title:%s', title)
        return title


def fix_info(info):
    if 'doi' in info:
        if type(info['doi']) is list:
            if len(set(info['doi'])) == 1:
                info['doi'] = info['doi'][0]
            else:
                logging.warning('multiple doi: %s', info['doi'][0])
                info['doi'] = info['doi'][0]
    if 'title' in info:
        info['title'] = fix_title(info['title'])
    if 'creation_date' in info:
        if type(info['creation_date']) is str:
            info['creation_date'] = datetime.fromisoformat(info['creation_date'])
    return info


def get_all_collaboration(collaboration, infos=None):
    infos = infos or ['recid', 'creation_date', 'number_of_authors', 'system_control_number', 'doi', 'title']
    nthread = 10
    shift = 20
    offset = 1

    def get(offset):
        query = "collaboration:'%s' AND collection:published" % collaboration
        return query_inspire(query, shift, offset, infos)

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

ndone = 0
lock_ndone = threading.Lock()


class InspireConsumer(threading.Thread):
    def __init__(self, input_queue, output_queue, query, step, infos=None, stop_event=None):
        super(InspireConsumer, self).__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.query = query
        self.step = step
        self.stop_event = stop_event
        self.infos = infos or ['recid', 'creation_date', 'number_of_authors', 'system_control_number', 'doi', 'title']

    def run(self):
        while self.stop_event is None or not self.stop_event.is_set():
            if not self.input_queue.empty():
                offset = self.input_queue.get()
                r = query_inspire(self.query, self.step, offset, self.infos)

                for rr in r:
                    self.output_queue.put(fix_info(rr))
                    with lock_ndone:
                        global ndone
                        ndone += 1

                self.input_queue.task_done()


class InspireQuery():
    def __init__(self, query, workers=5, callback=None, buf_size=10):
        self.input_queue = queue.Queue(buf_size)
        self.output_queue = queue.Queue()
        self.query = query
        self.buf_size = buf_size
        self.all_producers = []
        self.all_workers = []
        self.callback = callback
        self.callback_worker = None
        self.status = 'stopped'
        self.stop_event = threading.Event()
        self.nworkers = workers

    def run(self):
        self.status = 'starting'
        p = OffsetsProducer(self.input_queue, self.buf_size, stop_event=self.stop_event)
        p.setDaemon(True)
        self.all_producers.append(p)

        for w in range(self.nworkers):
            worker = InspireConsumer(self.input_queue, self.output_queue, self.query, self.buf_size, stop_event=self.stop_event)
            worker.setDaemon(True)
            self.all_workers.append(worker)
            worker.start()

        if self.callback is not None:
            self.callback_worker = CallBackConsumer(self.output_queue, self.callback, stop_event=self.stop_event)
            self.callback_worker.setDaemon(True)
            self.callback_worker.start()

        p.start()
        self.status = 'running'

    def stop(self):
        self.status = 'stopping'
        self.stop_event.set()

        logging.info('stopping producer')
        for worker in self.all_producers:
            worker.join()

        logging.info('stopping consumer')
        for worker in self.all_workers:
            worker.join()

        if self.callback_worker is not None:
            logging.info('stopping callback')
            self.callback_worker.join()

        self.status = 'stopped'
        logging.info('all stopped')
        logging.info("Number of inspire entried found: %d" % ndone)

        self.stop_event.clear()


if __name__ == '__main__':

    import time
    import argparse

    parser = argparse.ArgumentParser(description='Query inspire')
    parser.add_argument('--max-results', type=int, help='stop the query after number of results')
    parser.add_argument('--max-seconds', type=int, help='max number of second for the query')
    parser.add_argument('--out', help='output filename')
    parser.add_argument('--workers', type=int, default=5)
    args = parser.parse_args()

    all_publications = []
    doi_set = set()
    lock = threading.Lock()
    ifound = 0

    fout = None
    if args.out:
        fout = open(args.out, 'w')

    def callback(item):
        global ifound
        global fout
        with lock:
            all_publications.append(item)
            if item['doi'] in doi_set:
                logging.warning('duplicate: %s' % item['doi'])
            doi_set.add(item['doi'])
            print("%4d %40s %30s %s" % (ifound, item['doi'], str(item['title'][:30]), item['creation_date']))
            if fout is not None:
                fout.write("%s %s %s\n" % (item['doi'], item['title'], item['creation_date']))
            ifound += 1

    start_time = time.time()
    q = InspireQuery("collaboration:'ATLAS' AND collection:published", callback=callback, workers=args.workers)
    q.run()
    logging.info("running")
    while True:
        if (args.max_results is not None and ifound >= args.max_results) or \
           (args.max_seconds is not None and (time.time() - start_time) > args.max_seconds):
            logging.info("stopping")
            q.stop()
            logging.info("stopped")
            logging.info("found %d publications" % len(all_publications))
            break
    #for x in get_all_collaboration('ATLAS'):
    #    print(x['creation_date'], x['doi'], x['title'])