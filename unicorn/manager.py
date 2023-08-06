import logging
import multiprocessing
import os
import signal
import threading
from typing import List

from unicorn.server import Server

spawn: multiprocessing.context.SpawnContext = multiprocessing.get_context("spawn")

logger = logging.getLogger('unicorn')


def run_worker(app: str, host: str, port: int):
    """ Initializes and runs a worker process with the given application server details.
    :param app: ASGI callable for the application.
    :param host: IP address on which the application server will run.
    :param port: Port on which the application server will listen for requests.
      """
    logger.info(f'Initializing worker process [{os.getpid()}]')
    Server(app=app, host=host, port=port).run()


class Manager:
    """
    This manager class is responsible for spawning worker process to handle requests of the application server.
    All the worker process can handle requests received at the defined host and port.
    Load balancing across different worker process is done by the TCP kernel.
    Request will be picked by each worker, on accept() system call, which returns a file descriptor of the connection.
    Data is only read on the  recv() system call on the connection
    """

    def __init__(self, app: str, workers: int = 1, host: str = '0.0.0.0', port: int = 8000):
        """
        Initializes the Manager class
        :param app: ASGI callable
        :param workers: Number of workers to spawn which will handle the request to application server.
        :param host: IP address on where the application server will be run
        :param port: Port on which application server will listen for request. Default to 8000.
        """
        self.app = app
        self.host = host
        self.port = port
        self.workers = workers
        self.should_wait: threading.Event = threading.Event()
        self.processes: List[spawn.Process] = []
        self.pid = os.getpid()

    def on_interrupt(self, sig, _):
        logger.info(f'Received interrupt={sig} on manager.')
        self.should_wait.set()

    def run(self):
        """Starts the Manager and spawns the required number of worker processes.

        Sets up signal listeners for interruption. After spawning the worker processes,
        it blocks the main process until an interrupt is received. Upon interruption,
        it terminates all the worker processes.
        """
        logger.info(f'Starting manager process [{os.getpid()}]')
        # Setup listeners for signal
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self.on_interrupt)

        # Spawns the required number of worker processes
        for idx in range(self.workers):
            process = spawn.Process(target=run_worker, kwargs={
                'app': self.app,
                'host': self.host,
                'port': self.port
            })
            process.start()
            self.processes.append(process)

        # Block the execution on this process till an interrupt is received
        self.should_wait.wait()

        # Terminate all the worker processes, when an interrupt is received
        for process in self.processes:
            process.terminate()
            process.join()
        logger.info(f'Closing manager process [{os.getpid()}]')
