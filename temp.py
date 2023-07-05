import asyncio
from asyncio import StreamReaderProtocol, StreamReader, Server
import socket

host = '0.0.0.0'
port = 9500
backlog = 10


async def client_is_connected_callback(reader, writer):
    print(f'client is connected callback reader={reader}, writer={writer}\n--------')
    data = await reader.readuntil(b'\r\n\r\n')
    print(data)


async def main():
    loop = asyncio.get_running_loop()

    def factory():
        reader = StreamReader(limit=100, loop=loop)
        protocol = StreamReaderProtocol(reader, client_is_connected_callback,
                                        loop=loop)
        return protocol

    # What is proto?
    # what is meant by family and type of socket?
    proto = 6  # ??
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, proto)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.setblocking(False)
    sock.bind((host, port))

    ssl = None
    ssl_handshake_timeout = None
    ssl_shutdown_timeout = None
    server = Server(loop, [sock], factory,
                    ssl, backlog, ssl_handshake_timeout,
                    ssl_shutdown_timeout)
    await server.serve_forever()
    # sock.listen(1)
    # server = await loop.create_server(factory, host, port)
    # await server.serve_forever()


asyncio.run(main())
# asyncio.selector_events.BaseSelectorEventLoop._accept_connection