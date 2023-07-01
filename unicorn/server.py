import asyncio
import importlib
import logging
from typing import Any

logging.basicConfig(level=logging.DEBUG)


def import_from_string(import_str: Any) -> Any:
    if not isinstance(import_str, str):
        return import_str

    module_str, _, attrs_str = import_str.partition(":")
    if not module_str or not attrs_str:
        message = (
            'Import string "{import_str}" must be in format "<module>:<attribute>".'
        )
        raise Exception(message.format(import_str=import_str))

    try:
        module = importlib.import_module(module_str)
    except ImportError as exc:
        if exc.name != module_str:
            raise exc from None
        message = 'Could not import module "{module_str}".'
        raise Exception(message.format(module_str=module_str))

    instance = module
    try:
        for attr_str in attrs_str.split("."):
            instance = getattr(instance, attr_str)
    except AttributeError:
        message = 'Attribute "{attrs_str}" not found in module "{module_str}".'
        raise Exception(
            message.format(attrs_str=attrs_str, module_str=module_str)
        )

    return instance


class Server:
    def __init__(self, app, host='0.0.0.0', port=8000):
        self.app = app
        self.writer = None
        self.body = None
        self.host = host
        self.port = port

    def run(self):
        asyncio.run(self.serve())

    async def send(self, message):
        message_type = message['type']
        if message_type == 'http.response.start':
            status_code = message['status']
            headers = ''.join(f'{k.decode()}: {v.decode()}\r\n' for k, v in message['headers'])
            initial_response_part = f'HTTP/1.1 {status_code} OK\r\n{headers}\r\n'
            self.writer.write(initial_response_part.encode('utf-8'))
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

    async def handle_request(self, reader, writer):
        data = await reader.read(10000)
        method, path, query_string, headers, body = self._parse_request(data)
        self.body = body
        scope = {
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
        self.writer = writer
        await self.app(scope, self.receive, self.send)
        self.body = b''

    async def serve(self):
        server = await asyncio.start_server(
            self.handle_request,
            host=self.host,
            port=self.port
        )
        async with server:
            await server.serve_forever()
