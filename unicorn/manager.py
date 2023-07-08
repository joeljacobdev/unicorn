import logging
import multiprocessing
import signal

import os
from typing import List

from unicorn.server import Server

multiprocessing.allow_connection_pickling()
spawn: multiprocessing.context.SpawnContext = multiprocessing.get_context("spawn")

logger = logging.getLogger('unicorn')


def run_worker(app, host, port):
    logger.info(f'Initializing worker process [{os.getpid()}]')
    Server(app=app, host=host, port=port).run()


class Manager:
    def __init__(self, app, workers=1, host='0.0.0.0', port=8000, backlog=100):
        self.app = app
        self.host = host
        self.port = port
        self.workers = workers
        self.should_wait: multiprocessing.Event = multiprocessing.Event()
        self.processes: List[spawn.Process] = []
        self.pid = os.getpid()
        self.backlog = backlog

    def on_interrupt(self, sig, _):
        logger.info(f'Received interrupt={sig}.')
        self.should_wait.set()

    def run(self):
        logger.info(f'Starting manager process [{os.getpid()}]')
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self.on_interrupt)

        for idx in range(self.workers):
            process = spawn.Process(target=run_worker, kwargs={
                'app': self.app,
                'host': self.host,
                'port': self.port
            })
            process.start()
            self.processes.append(process)

        self.should_wait.wait()

        for process in self.processes:
            process.terminate()
            process.join()
        logger.info(f'Closing manager process [{os.getpid()}]')
