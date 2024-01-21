import asyncio
import logging
import os
import signal

from unicorn import utils

logging.basicConfig(level=logging.DEBUG)


class Server:
    """
    Worker server, which creates async server running on the current thread's event loop.
    We require this async server to reuse port, so that multiple workers can be run and handle request
     from the same port.
    """
    def __init__(self, app: str, host: str = '0.0.0.0', port: int = 8000):
        self.app = utils.import_from_string(app)
        self.host = host
        self.port = port
        self.pid = os.getpid()
        self.should_exit = False
        self.logger = logging.getLogger('unicorn')
        self.access_logger = logging.getLogger('unicorn.access')

    def run(self):
        """
        Start the server in an event loop
        """
        asyncio.run(self.serve())

    def on_interrupt(self, sig, _):
        self.logger.info(f'Received signal={sig} on server.')
        self.should_exit = True

    async def handle_request(self, reader, writer):
        cycle = RequestResponseCycle(
            app=self.app, reader=reader, writer=writer, access_logger=self.access_logger,
        )
        await cycle.complete()

    async def serve(self):
        """
        Create a server which will start serving request after the ASGI lifespan start event is triggered.
        Once an interrupt is received, it will perform the required cleanup using the ASGI lifespan shutdown event.
        Interrupt handling is done on worker so that each worker can perform cleanup of its resources.
        """
        lifecycle = Lifecycle(app=self.app, state={})
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self.on_interrupt)

        server = await asyncio.start_server(
            self.handle_request,
            host=self.host,
            port=self.port,
            reuse_port=True,
            start_serving=False
        )
        await lifecycle.on_startup()
        async with server:
            await server.start_serving()
            # While interrupt is not received, do this infinitely.
            while not self.should_exit:
                await asyncio.sleep(0.1)
        await lifecycle.on_shutdown()


class Lifecycle:
    __slots__ = ('app', 'state', 'startup_event', 'shutdown_event', 'events', 'logger',)

    def __init__(self, app, state):
        """
        :param app: Instance of application server
        :param state: dict containing state of the server. NOT used in current implementation.
        """
        self.app = app
        self.state = state
        self.startup_event = asyncio.Event()
        self.shutdown_event = asyncio.Event()
        self.logger = logging.getLogger('unicorn')
        self.events: asyncio.Queue = asyncio.Queue()

    async def main(self):
        try:
            scope = {
                'type': 'lifespan',
                'asgi': {
                    'spec_version': '2.3',
                    'version': '3.0'
                },
                'state': self.state
            }
            await self.app(scope, self.receive, self.send)
        except Exception as e:
            self.logger.error('Following error occurred during lifespan of the server.', exc_info=e)
        finally:
            self.startup_event.set()
            self.shutdown_event.set()

    async def on_startup(self):
        await self.events.put({'type': 'lifespan.startup'})
        loop = asyncio.get_running_loop()
        main_task = loop.create_task(self.main())  # noqa
        await self.startup_event.wait()

    async def on_shutdown(self):
        await self.events.put({'type': 'lifespan.shutdown'})
        await self.shutdown_event.wait()

    async def receive(self):
        return await self.events.get()

    async def send(self, message):
        if message['type'] == 'lifespan.startup.failed':
            self.logger.info('Application startup has failed')
            self.startup_event.set()
        elif message['type'] == 'lifespan.startup.complete':
            self.logger.info('Application startup has completed successfully')
            self.startup_event.set()
        elif message['type'] == 'lifespan.shutdown.failed':
            self.logger.info('Application shutdown has failed')
            self.shutdown_event.set()
        elif message['type'] == 'lifespan.shutdown.complete':
            self.logger.info('Application shutdown has completed successfully')
            self.shutdown_event.set()


class RequestResponseCycle:
    """
    Request Response cycle level object - which has access to reader and writer to read and write the data
    """
    __slots__ = ('app', 'reader', 'writer', 'scope', 'body', 'access_logger')

    def __init__(self, app, reader, writer, access_logger):
        self.app = app
        self.reader = reader
        self.writer = writer
        self.scope = None
        self.body = b''
        self.access_logger = access_logger

    async def complete(self):
        data = await self.reader.read(10000)
        method, path, query_string, headers, body = self._parse_request(data)
        self.body = body
        self.scope = {
            'type': 'http',
            'http_version': '1.1',
            'asgi': {
                'spec_version': '2.3',
                'version': '3.0'
            },
            'method': method.decode('utf-8'),
            'headers': headers,
            'path': path.decode('utf-8'),
            'query_string': query_string,
            'state': {}
        }
        await self.app(self.scope, self.receive, self.send)

    async def send(self, message):
        message_type = message['type']
        if message_type == 'http.response.start':
            status_code = message['status']
            headers = ''.join(f'{k.decode()}: {v.decode()}\r\n' for k, v in message['headers'])
            initial_response_part = f'HTTP/1.1 {status_code} OK\r\n{headers}\r\n'
            self.writer.write(initial_response_part.encode('utf-8'))
            self.access_logger.info(f"{self.scope['method']} {self.scope['path']} {status_code}")
        elif message_type == 'http.response.body':
            self.writer.write(message.get('body', b''))
            if not message.get('more_body', False):
                # No more body content to be sent, close the connection
                await self.writer.drain()
                self.writer.close()
                await self.writer.wait_closed()
        else:
            logging.warning(f"Unhandled message type: {message_type}")

    async def receive(self):
        return {'type': 'http.request', 'body': self.body}

    @staticmethod
    def _parse_request(request_bytes: bytes) -> tuple[bytes, bytes, bytes, list[tuple[bytes, bytes]], bytes]:
        """
        Parses the request data and return request method, path, query string, headers and body
        :param request_bytes: bytes of request data
        """
        request = request_bytes
        request_lines = request.split(b'\r\n')

        # Extract the request method
        request_line = request_lines[0]

        request_method: bytes = request_line.split(b' ')[0]
        path, _, query_string = request_line.split(b' ')[1].partition(b'?')

        # Extract the headers
        headers = []
        for line in request_lines[1:]:
            if line:
                key, value = line.split(b': ', 1)
                headers.append((key.lower(), value))

        # Extract the body (if present)
        body_index = request.find(b'\r\n\r\n')
        if body_index != -1:
            body = request[body_index + 4:]
        else:
            body = b''

        return request_method, path, query_string, headers, body
