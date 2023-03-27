""" Usage: 
Scrape : python3 scrape.py
Modify threads : change NUM_WORKERS below
Reset scraping: rm *.html worker*
"""

from threading import Thread
import time, re, requests, os, sys, threading

lock = threading.Lock()
processed = 0
TOTAL = 0

NUM_WORKERS = 10

GLOBAL_START = time.time()

# thread decorator stolen from https://gist.githubusercontent.com/raviolliii/94e9e16ef74f3c4f0886c6eb1fdfa157/raw/b32018243349061aac2776b25c957045ea298d07/thread_decorator.py
def threaded(func):
    """
    Decorator that multithreads the target function
    with the given parameters. Returns the thread
    created for the function
    """
    def wrapper(*args, **kwargs):
        thread = Thread(target=func, args=args)
        thread.start()
        return thread
    return wrapper

def scrape(thread_url):
    next = None
    output_filename = thread_url.replace("https://www.dpreview.com/forums/thread/", "").replace("?page=", "_") + ".html"
    output_filename = os.path.join("./archive/",output_filename)
    if os.path.exists(output_filename):
        # already scraped
        print("%s" % (thread_url), "already scraped")
        return None
    sleepCount=0
    while True:
        sleepCount+=1
        os.system('wget "%s" -q --retry-connrefused --waitretry=1 --read-timeout=2 --timeout=2 -t 1 --content-on-error --user-agent="Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/111.0" --warc-file="%s" -O %s' % (thread_url, output_filename.replace("html", "warc"), output_filename))
        r = open(output_filename).read()
        if not "We can't connect to the server for this app or website at this time. There might be too much traffic or a configuration error." in r and ('title="dpreview.com: Digital Photograhy Review"' in r or "It looks like you're trying to visit a page that doesn't exist" in r):
            break # getting r was a success
        print("FATAL ERROR! BLOCK DETECTED! WAITING TO PROCESS", r)
        print("\tWaiting {} seconds".format(sleepCount*20))
        time.sleep(20*sleepCount)
        sleepCount+=1
        # try again
    if '<link rel="next"' in r:
        sleepCount=0
        next = r.split('<link rel="next" href="')[1].split('"')[0]
        next = next.strip()
    return next


def process(thread_id):
    global processed, TOTAL, lock
    next = "https://www.dpreview.com/forums/thread/" + str(thread_id)
    while next is not None:
        next = scrape(next)
    lock.acquire()
    processed += 1
    lock.release()
#    print(thread_id, "processed", processed, "of", TOTAL, 100 * float(processed) / TOTAL, "% in", time.time() - GLOBAL_START, "seconds", "chunkfile", sys.argv[1])
    print("ThreadId: {} processed {} of {} ({:.02f})% in {:.03f} seconds. Chunkfile: '{}'".format(thread_id,processed,TOTAL,100.0*processed/TOTAL,(time.time()-GLOBAL_START),sys.argv[1]))

def initialize(start):
    curr = start
    interval = int(start / NUM_WORKERS)
    open("workerinterval", "w").write(str(interval))
    for i in range(NUM_WORKERS):
        open("worker%d" % (i), "w").write(str(curr))
        print(i, "starts at", curr)
        curr = curr - interval

@threaded
def work(thread_ids, worker_id):
    for thread in thread_ids:
        starttime = time.time()
        process(int(thread))
        print("worker", worker_id, "scraped thread", thread, "elapsed", time.time() - starttime)



try:
    chunkfile = sys.argv[1]
except:
    print("Usage: python scrape.py [file], file has one thread ID per line to scrape")

if not os.path.exists("./archive"):
    os.mkdirs("./archive")
to_process = open(chunkfile).read().splitlines()
TOTAL = len(to_process)
# assign jobs to threads
chunks = [to_process[x:x+int(len(to_process)/NUM_WORKERS)] for x in range(0, len(to_process), int(len(to_process)/NUM_WORKERS))]

for chunk in range(len(chunks)):
    work(chunks[chunk], chunk)
