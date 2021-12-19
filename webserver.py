import socket
from logger import TXTLogger
from datetime import datetime
from pathlib import Path
from threading import Thread
from wsgiref.handlers import format_date_time
from enum import Enum

import settings


class Status(Enum):
    OK = 200
    FORBIDDEN = 403
    NOT_FOUND = 404


class Filetype(Enum):
    HTML = 'html'
    CSS = 'css'
    JS = 'js'
    PNG = 'png'


CODE_MESSAGE = {
    Status.OK: 'OK',
    Status.FORBIDDEN: 'Forbidden',
    Status.NOT_FOUND: 'Not found'
}

CONTENT_TYPE = {
    Filetype.HTML: 'text/html',
    Filetype.CSS: 'text/css',
    Filetype.JS: 'text/javascript',
    Filetype.PNG: 'image/png'
}

BINARY_FILETYPES = [Filetype.PNG]


class WebServer:

    @classmethod
    def get_timestamp(cls):
        return format_date_time(datetime.utcnow().timestamp())

    @classmethod
    def get_resource_path(cls, request):
        print(request)
        resource = request.split('\n')[0].split()[1][1:]
        if not resource:
            resource = 'index.html'
        return Path(settings.ROOT_DIR, resource)

    @classmethod
    def get_response(cls, body, code, filetype):
        return f"""HTTP/1.1 {code.value} {CODE_MESSAGE[code]}
Date: {cls.get_timestamp()}
Server: SelfMadeServer v0.0.1
Content-Type: {CONTENT_TYPE[filetype]}
Content-Length: {len(body)}
Connection: close

""".encode() + body

    @classmethod
    def is_forbidden(cls, resource_path):
        if resource_path.suffix[1:] not in [filetype.value
                                            for filetype in Filetype]:
            return True

    def __init__(self, logger=None):
        self._logger = logger
        self._socket = socket.socket()
        self._socket.bind(('', settings.LISTENING_PORT))
        self._socket.listen()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def accept(self):
        conn, addr = self._socket.accept()
        ip = addr[0]
        Thread(target=self.handle, args=[conn, ip]).start()

    def start(self):
        while True:
            self.accept()

    def handle(self, conn, ip):
        with conn:
            request = conn.recv(settings.REQUEST_SIZE).decode()
            if not request:
                return
            resource_path = self.get_resource_path(request)
            if resource_path.is_file():
                if self.is_forbidden(resource_path):
                    filetype = Filetype.HTML
                    body = ''.encode()
                    status = Status.FORBIDDEN
                else:
                    filetype = Filetype(resource_path.suffix[1:])
                    status = Status.OK
                    if filetype in BINARY_FILETYPES:
                        body = resource_path.read_bytes()
                    else:
                        body = resource_path.read_text().encode()
            else:
                filetype = Filetype.HTML
                body = ''.encode()
                status = Status.NOT_FOUND
            response = self.get_response(body, status, filetype)
            conn.send(response)
            self.log(f'{ip} {resource_path} {status.value}')

    def log(self, message):
        self._logger.log(message)

    def close(self):
        self._socket.close()


with WebServer(logger=TXTLogger('pages/logs.txt')) as server:
    server.start()
