# https://labs.inspirehep.net/api/literature?sort=mostrecent&size=25&q=&collaboration=ATLAS
# https://labs.inspirehep.net/api/literature?sort=mostrecent&size=25&q=&collaboration=ATLAS&doc_type=peer%20reviewed
# https://labs.inspirehep.net/api/literature?sort=mostrecent&size=25&q=&collaboration=ATLAS&doc_type=peer%20reviewed&page=2

import requests
import json
from multiprocessing.pool import ThreadPool
import logging
from datetime import datetime
from airstuff.workers import OffsetsProducer, CallBackConsumer, DuplicateFilter
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("bibtexparser").setLevel(logging.WARNING)
import colorlog
logger = colorlog.getLogger('airstuff.inspire')


URL_SEARCH = "http://inspirehep.net/search"

ATLAS_QUERY = 'collaboration:"ATLAS" AND collection:published and NOT collection:conferencepaper and collection:citeable'

def query_inspire(query, rg=100, jrec=1, ot=None):
    logging.debug('querying %s, offset=%d', query, jrec)
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
    logging.debug('getting %s' % r.url)
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
    if 'doi' in info and info['doi'] is not None:
        if type(info['doi']) is str:
            info['doi'] = [info['doi']]
        
        info['doi'] = [doi.upper() for doi in info['doi']]
        info['doi'] = sorted(list(set(info['doi'])))
    else:
        info['doi'] = []

    if 'date' in info and type(info['date'] is datetime):
        pass
    else:
        date = '?'
        if 'imprint' in info and info['imprint'] is not None and 'date' in info['imprint']:
            date = info['imprint']['date']
        elif 'prepublication' in info and info['prepublication'] is not None and 'date' in info['prepublication']:
            date = info['prepublication']['date']
        info['date'] = date

    if 'title' in info:
        info['title'] = fix_title(info['title'])    

    return info


def get_all_collaboration(collaboration, infos=None):
    infos = infos or ['recid', 'imprint', 'prepublication', 'number_of_authors', 'system_control_number', 'doi', 'title']
    nthread = 10
    shift = 20
    offset = 1

    def get(offset):
        query = ATLAS_QUERY.replace("ATLAS", collaboration)
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
                    if rrr['number_of_authors'] is not None and int(rrr['number_of_authors']) < 30:
                        continue
                    yield fix_info(rrr)
                if not rr:
                    dobreak = True
            if dobreak:
                break


import threading
import queue

ndone = 0
nlow_author = 0
lock_ndone = threading.Lock()


class InspireConsumer(threading.Thread):
    def __init__(self, input_queue, output_queue, query, step, infos=None, stop_event=None):
        super(InspireConsumer, self).__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.query = query
        self.step = step
        self.stop_event = stop_event
        self.infos = infos or ['recid', 'imprint', 'prepublication', 'number_of_authors', 'system_control_number', 'doi', 'title']

    def run(self):
        while self.stop_event is None or not self.stop_event.is_set():
            if not self.input_queue.empty():
                offset = self.input_queue.get()
                r = query_inspire(self.query, self.step, offset, self.infos)

                if len(r) == 0:
                    logging.info("getting empty response")
                    if self.stop_event is not None:
                        self.stop_event.set()
                        logging.debug('stop event set')

                for rr in r:
                    with lock_ndone:
                        global ndone
                        ndone += 1
                    info_fixed = fix_info(rr)
                    if int(info_fixed['number_of_authors']) < 30:  ## TODO: FIXME
                        logging.debug('ignoring %s %s since it has only %d authors',
                                      info_fixed['doi'], info_fixed['title'], info_fixed['number_of_authors'])
                        with lock_ndone:
                            global nlow_author
                            nlow_author += 1
                        continue
                    self.output_queue.put(info_fixed)
                logging.debug('found %d entries from offset %s', len(r), offset)
                self.input_queue.task_done()
        logging.debug('thread at the end')


class ManagerWorker(threading.Thread):
    def __init__(self, stopping_event, stopping_action):
        super(ManagerWorker, self).__init__()
        self.stopping_event = stopping_event
        self.stopping_action = stopping_action

    def run(self):
        self.stopping_event.wait()
        logging.debug('stopping condition met')
        self.stopping_action()
        logging.debug('stopping action done')
        return


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
        p.name = 'producer'
        p.setDaemon(True)
        self.all_producers.append(p)

        self.manager = ManagerWorker(stopping_event=self.stop_event,
                                     stopping_action=self.stop)
        self.manager.name = 'manager'
        self.manager.setDaemon(True)
        self.manager.start()
        logging.debug('manager started')

        queue_duplicates = queue.Queue()

        for w in range(self.nworkers):
            worker = InspireConsumer(self.input_queue, self.output_queue, self.query, self.buf_size, stop_event=self.stop_event)
            worker.name = 'consumer-%d' % w
            worker.setDaemon(True)
            self.all_workers.append(worker)
            worker.start()
        logging.debug('worker started')

        #for w in range(2):
        #    worker = DuplicateFilter(queue_duplicates, self.output_queue, stop_event=self.stop_event)
        #    worker.name = 'duplicate-%d' % w
        #    worker.setDaemon(True)
        #    worker.start()
        #logging.debug('worker duplicates started')

        if self.callback is not None:
            self.callback_worker = CallBackConsumer(self.output_queue, self.callback, stop_event=self.stop_event)
            self.callback_worker.name = 'callback'
            self.callback_worker.setDaemon(True)
            self.callback_worker.start()
        logging.debug('callback started')

        p.start()
        logging.debug('produced started')
        self.status = 'running'

    def stop(self):
        logging.debug('start stopping procedure')
        self.status = 'stopping'
        self.stop_event.set()

        logging.info('wait produer to join')
        for worker in self.all_producers:
            worker.join()

        logging.info('wait consumer to join')
        for worker in self.all_workers:
            #worker.join()
            logging.debug('worker %s joined' % worker.name)

        if self.callback_worker is not None:
            logging.info('wait callback to join')
            self.callback_worker.join()

        if threading.get_ident() != self.manager.ident:
            logging.info('wait manager to join')
            self.manager.join()

        self.status = 'stopped'
        logging.info('all stopped')
        logging.info("Number of inspire entries found: %d" % ndone)
        logging.info("Ignored %d entries since low author" % nlow_author)

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

    f = open(args.out, 'w')
    for x in get_all_collaboration('ATLAS'):
        to_write = '%s\t%s\t%s' % (','.join(x['doi']), x['title'], x['date'])
        print(to_write)
        f.write(to_write + '\n')
    exit()


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
            print("%4d %40s %30s %s" % (ifound, item['doi'], str(item['title'][:30]), item['imprint']['date']))
            if fout is not None:
                fout.write("%s\t%s\t%s\n" % (item['doi'], item['title'], item['imprint']['date']))
            ifound += 1

    start_time = time.time()
    q = InspireQuery(ATLAS_QUERY, callback=callback, workers=args.workers)
    q.run()
    logging.info("running")
    while True:
        if (args.max_results is not None and ifound >= args.max_results) or \
           (args.max_seconds is not None and (time.time() - start_time) > args.max_seconds) or \
           q.status == 'stopped':
            logging.info("stopping")
            q.stop()
            logging.info("stopped")
            logging.info("found %d publications" % len(all_publications))
            break
    
