import asyncio
import logging
import os

from unicorn import utils

logging.basicConfig(level=logging.DEBUG)


class Server:
    def __init__(self, app, host='0.0.0.0', port=8000):
        self.app = utils.import_from_string(app)
        self.host = host
        self.port = port
        self.pid = os.getpid()
        self.access_logger = logging.getLogger('unicorn.access')

    def run(self):
        asyncio.run(self.serve())

    async def handle_request(self, reader, writer):
        cycle = RequestResponseCycle(
            app=self.app, reader=reader, writer=writer, access_logger=self.access_logger,
        )
        await cycle.complete()

    async def serve(self):
        server = await asyncio.start_server(
            self.handle_request,
            host=self.host,
            port=self.port,
            reuse_port=True
        )
        async with server:
            await server.serve_forever()


class RequestResponseCycle:
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
            'method': method,
            'headers': headers,
            'path': path,
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
    def _parse_request(request_bytes):
        request = request_bytes.decode('utf-8')
        request_lines = request.split('\r\n')

        # Extract the request method
        request_line = request_lines[0]

        request_method = request_line.split(' ')[0]
        path, _, query_string = request_line.split(' ')[1].partition('?')

        # Extract the headers
        headers = []
        for line in request_lines[1:]:
            if line:
                key, value = line.split(': ', 1)
                headers.append((key.lower().encode('utf-8'), value.encode('utf-8')))

        # Extract the body (if present)
        body_index = request.find('\r\n\r\n')
        if body_index != -1:
            body = request[body_index + 4:].encode('utf-8')
        else:
            body = b''

        return request_method, path, query_string, headers, body
