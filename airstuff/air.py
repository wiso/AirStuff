import requests
import bibtexparser
from lxml import etree
from multiprocessing.pool import ThreadPool
from airstuff.workers import OffsetsProducer, CallBackConsumer
#logging.getLogger("requests").setLevel(logging.WARNING)
#logging.getLogger("urllib3").setLevel(logging.WARNING)
#logging.getLogger("bibtexparser").setLevel(logging.WARNING)
import colorlog
logger = colorlog.getLogger('airstuff.air')


def get_document_metadata(document_id):
    BASEURL = "https://air.unimi.it/references"
    r = requests.get(BASEURL, params={'format': 'bibtex', 'item_id': str(document_id)})
    try:
        return bibtexparser.loads(r.text).entries[0]
    except:
        logger.error("problem parsing %s", r.text)
        return None


def get_document_ids_from_author(author_id):
    offset = 0
    BUNCH = 10

    # get = partial(get_document_ids_from_author_offset, author_id=author_id)

    def get(offset):
        return get_document_ids_from_author_offset(author_id, BUNCH, offset)

    while True:
        with ThreadPool(BUNCH) as pool:
            offset_bunch = []
            for b in range(BUNCH):
                offset_bunch.append(offset)
                offset += 20

            r = pool.map(get, offset_bunch)
            for rr in r:
                dobreak = False
                for rrr in rr:
                    yield rrr
                if not rr:
                    dobreak = True
            if dobreak:
                break


def get_document_ids_from_author_offset(author_id, rg, offset):
    BASEURL = "https://air.unimi.it/browse?type=author&order=DESC&rpp=%s&authority=%s&offset=%d"

    url = BASEURL % (rg, author_id, offset)
    logger.debug("getting %s", url)
    r = requests.get(url)
    html = r.text

    root = etree.HTML(html)
    result = root.xpath('//form[@class="form-inline"]/*[@name="item_id"]')
    result = [r.attrib['value'] for r in result]

    logger.debug('results %s', result)
    return result


import threading
import queue


class AirConsumer(threading.Thread):
    def __init__(self, input_queue, output_queue, author_id, step, infos=None, stop_event=None):
        super(AirConsumer, self).__init__()
        self.author_id = author_id
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.step = step
        self.stop_event = stop_event

    def run(self):
        while self.stop_event is None or not self.stop_event.is_set():
            if not self.input_queue.empty():
                offset = self.input_queue.get()
                r = get_document_ids_from_author_offset(self.author_id, self.step, offset)
                for rr in r:
                    info = get_document_metadata(rr)
                    if not info:
                        logging.error('no info in offset %s, step %s', offset, self.step)
                        continue
                    if 'doi' not in info:
                        logger.warning('no doi for %s', info['title'])
                        info['doi'] = None
                    else:
                        info['doi'] = info['doi'].upper()
                    logger.debug('putting info for %s into queue', info['doi'])
                    info['title'] = info['title'].replace('\n', ' ').replace('\t', ' ')
                    info = {k: info[k] for k in ('doi', 'title', 'year')}
                    self.output_queue.put(info)

                self.input_queue.task_done()


class AirQuery():
    def __init__(self, author_id, workers=5, callback=None, buf_size=10):
        self.input_queue = queue.Queue(buf_size)
        self.output_queue = queue.Queue()
        self.author_id = author_id
        self.buf_size = buf_size
        self.all_producers = []
        self.all_workers = []
        self.callback = callback
        self.callback_worker = None
        self.status = 'stopped'
        self.stop_event = threading.Event()
        self.stop_event_callback = threading.Event()
        self.nworkers = workers

    def run(self):
        self.status = 'starting'
        p = OffsetsProducer(self.input_queue, self.buf_size, stop_event=self.stop_event)
        p.setDaemon(True)
        self.all_producers.append(p)

        for w in range(self.nworkers):
            worker = AirConsumer(self.input_queue, self.output_queue, self.author_id, self.buf_size, stop_event=self.stop_event)
            worker.setDaemon(True)
            self.all_workers.append(worker)
            worker.start()

        if self.callback is not None:
            logger.debug('creating callback consumer')
            self.callback_worker = CallBackConsumer(self.output_queue, self.callback, stop_event=self.stop_event_callback)
            self.callback_worker.setDaemon(True)
            self.callback_worker.start()

        p.start()
        self.status = 'running'

    def stop(self):
        self.status = 'stopping'
        self.stop_event.set()

        logger.debug('stopping producer')
        for worker in self.all_producers:
            worker.join()

        logger.debug('stopping consumer')
        for worker in self.all_workers:
            worker.join()

        if self.callback_worker is not None:
            self.stop_event_callback.set()
            logger.debug('stopping callback')
            logger.debug('waiting callback worker to join')
            self.callback_worker.join()

        self.status = 'stopped'
        logger.debug('all stopped')

        self.stop_event.clear()


if __name__ == '__main__':
    import time
    import argparse

    parser = argparse.ArgumentParser(description='Query AIR')
    parser.add_argument('--max-results', type=int, help='stop the query after number of results')
    parser.add_argument('--max-seconds', type=int, help='max number of second for the query')
    parser.add_argument('--out', help='output filename')
    parser.add_argument('--workers', type=int, default=5)
    args = parser.parse_args()

    all_publications = []
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
            print("%4d %40s %30s %s" % (ifound, item['doi'], str(item['title'][:30]), item['year']))
            if fout is not None:
                fout.write("%s\t%s\t%s\n" % (item['doi'], item['title'], item['year']))
            ifound += 1
    all_publications = []

    lock = threading.Lock()
    ifound = 0

    start_time = time.time()
    q = AirQuery('rp09852', callback=callback, workers=args.workers)
    q.run()
    logger.info("running")
    while True:
        if (args.max_results is not None and ifound >= args.max_results) or \
           (args.max_seconds is not None and (time.time() - start_time) > args.max_seconds):
            logger.info("stopping")
            q.stop()
            logger.info("stopped")
            logger.info("found %d publications" % len(all_publications))
            break

    print("found %d publications" % len(all_publications))

    """
    g = get_document_ids_from_author('rp09852')
    for gg in g:
        info = get_document_metadata(gg)
        if 'doi' not in info:
            logger.info("skipping %s", info)
            continue
        if gg:
            print(info['doi'])
    """