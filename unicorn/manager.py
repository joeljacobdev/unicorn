import logging
import multiprocessing
import os
import threading
from typing import List

from unicorn.server import Server

multiprocessing.allow_connection_pickling()
spawn: multiprocessing.context.SpawnContext = multiprocessing.get_context("spawn")

logger = logging.getLogger('unicorn')


class Manager:
    def __init__(self, app, workers=1, host='0.0.0.0', port=8000, backlog=100):
        self.app = app
        self.host = host
        self.port = port
        self.workers = workers
        self.should_wait = multiprocessing.Event()
        self.processes: List[spawn.Process] = []
        self.pid = os.getpid()
        # self.socket = None
        self.backlog = backlog

    def run_worker(self):
        logger.info(f'Initializing worker process [{os.getpid()}]')
        Server(app=self.app, host=self.host, port=self.port).run()

    def run(self):
        # self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        # self.socket.bind((self.host, self.port))
        # self.socket.listen(self.backlog)

        for idx in range(self.workers):
            process = spawn.Process(target=self.run_worker)
            process.start()
            self.processes.append(process)

        self.should_wait.wait()

        for process in self.processes:
            process.terminate()
            process.join()
