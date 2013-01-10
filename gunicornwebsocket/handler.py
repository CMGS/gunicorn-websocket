import base64
import socket
import re
import logging
import errno
import struct
from hashlib import md5, sha1
from socket import error as socket_error
from urllib import quote
from gunicorn.workers.async import ALREADY_HANDLED

from gunicornwebsocket.websocket import WebSocketHybi, WebSocketHixie

logger = logging.getLogger(__name__)

class WebSocketHandler(object):

    GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    SUPPORTED_VERSIONS = ('13', '8', '7')

    def __init__(self, handler):
        self.handler = handler

    def __call__(self, environ, start_response):
        self.pre_start()

        upgrade = environ.get('HTTP_UPGRADE', '').lower()

        if upgrade == 'websocket':
            connection = environ.get('HTTP_CONNECTION', '').lower()
            if 'upgrade' in connection:
                return self._handle_websocket(environ)
        # need to check a few more things here for true compliance
        start_response('400 Bad Request', [('Connection','close')])
        return []

    def pre_start(self):
        pass

    def _handle_websocket(self, environ):
        try:
            if environ.get("HTTP_SEC_WEBSOCKET_VERSION"):
                result = self._handle_hybi(environ)
            elif environ.get("HTTP_ORIGIN"):
                result = self._handle_hixie(environ)

            if not result:
                return

            try:
                self.handler(environ, lambda c, h:None)
            except socket.error, e:
                if e[0] != errno.EPIPE:
                    raise
            # use this undocumented feature of grainbows to ensure that it
            # doesn't barf on the fact that we didn't call start_response
            return [ALREADY_HANDLED]
        finally:
            pass
            #self.log_request()

    def _handle_hybi(self, environ):
        version = environ.get("HTTP_SEC_WEBSOCKET_VERSION")
        socket = environ['gunicorn.socket']
        environ['wsgi.websocket_version'] = 'hybi-%s' % version

        if version not in self.SUPPORTED_VERSIONS:
            logger.error('400: Unsupported Version: %r', version)
            self.respond(socket, \
                '400 Unsupported Version',
                [('Sec-WebSocket-Version', '13, 8, 7')]
            )
            return

        protocol, version = environ.get('SERVER_PROTOCOL').split("/")
        key = environ.get("HTTP_SEC_WEBSOCKET_KEY")

        # check client handshake for validity
        if not environ.get("REQUEST_METHOD") == "GET":
            # 5.2.1 (1)
            self.respond(socket, '400 Bad Request')
            return
        elif not protocol == "HTTP":
            # 5.2.1 (1)
            self.respond(socket, '400 Bad Request')
            return
        elif float(version) < 1.1:
            # 5.2.1 (1)
            self.respond(socket, '400 Bad Request')
            return
        # XXX: nobody seems to set SERVER_NAME correctly. check the spec
        #elif not environ.get("HTTP_HOST") == environ.get("SERVER_NAME"):
            # 5.2.1 (2)
            #logger.error('400 Bad Request')
            #return
        elif not key:
            # 5.2.1 (3)
            logger.error('400: HTTP_SEC_WEBSOCKET_KEY is missing from request')
            self.respond(socket, '400 Bad Request')
            return
        elif len(base64.b64decode(key)) != 16:
            # 5.2.1 (3)
            logger.error('400: Invalid key: %r', key)
            self.respond(socket, '400 Bad Request')
            return

        websocket = WebSocketHybi(socket, environ)
        environ['wsgi.websocket'] = websocket

        headers = [
            ("Upgrade", "websocket"),
            ("Connection", "Upgrade"),
            ("Sec-WebSocket-Accept", base64.b64encode(sha1(key + self.GUID).digest())),
        ]
        self._send_reply(socket, "101 Switching Protocols", headers)
        return True

    def _handle_hixie(self, environ):
        assert "upgrade" in environ.get("HTTP_CONNECTION", "").lower()
        socket = environ['gunicorn.socket']
        body = environ['wsgi.input']

        websocket = WebSocketHixie(socket, environ)
        environ['wsgi.websocket'] = websocket

        key1 = environ.get('HTTP_SEC_WEBSOCKET_KEY1')
        key2 = environ.get('HTTP_SEC_WEBSOCKET_KEY2')

        if key1 is not None:
            environ['wsgi.websocket_version'] = 'hixie-76'
            if not key1:
                logger.error("400: SEC-WEBSOCKET-KEY1 header is empty")
                self.respond(socket, '400 Bad Request')
                return
            if not key2:
                logger.error("400: SEC-WEBSOCKET-KEY2 header is missing or empty")
                self.respond(socket, '400 Bad Request')
                return

            part1 = self._get_key_value(key1)
            part2 = self._get_key_value(key2)
            if part1 is None or part2 is None:
                self.respond(socket, '400 Bad Request')
                return

            headers = [
                ("Upgrade", "WebSocket"),
                ("Connection", "Upgrade"),
                ("Sec-WebSocket-Location", reconstruct_url(environ)),
            ]
            if websocket.protocol is not None:
                headers.append(("Sec-WebSocket-Protocol", websocket.protocol))
            if websocket.origin:
                headers.append(("Sec-WebSocket-Origin", websocket.origin))

            self._send_reply(socket, "101 WebSocket Protocol Handshake", headers)

            # This request should have 8 bytes of data in the body
            key3 = body.read(8)

            challenge = md5(struct.pack("!II", part1, part2) + key3).digest()

            socket.sendall(challenge)
            return True
        else:
            environ['wsgi.websocket_version'] = 'hixie-75'
            headers = [
                ("Upgrade", "WebSocket"),
                ("Connection", "Upgrade"),
                ("WebSocket-Location", reconstruct_url(environ)),
            ]

            if websocket.protocol is not None:
                headers.append(("WebSocket-Protocol", websocket.protocol))
            if websocket.origin:
                headers.append(("WebSocket-Origin", websocket.origin))

            self._send_reply(socket, "101 Web Socket Protocol Handshake", headers)

    def _send_reply(self, socket, status, headers):
        towrite = []
        towrite.append('HTTP/1.1 %s\r\n' % status)

        for header in headers:
            towrite.append("%s: %s\r\n" % header)

        towrite.append("\r\n")
        msg = ''.join(towrite)
        socket.sendall(msg)

    def respond(self, socket, status, headers=[]):
        self._send_reply(socket, status, headers)

        if socket is not None:
            try:
                socket.close()
            except socket_error:
                pass

    def _get_key_value(self, key_value):
        key_number = int(re.sub("\\D", "", key_value))
        spaces = re.subn(" ", "", key_value)[1]

        if key_number % spaces != 0:
            logger.error("key_number %d is not an intergral multiple of spaces %d", key_number, spaces)
        else:
            return key_number / spaces


def reconstruct_url(environ):
    secure = environ['wsgi.url_scheme'] == 'https'
    if secure:
        url = 'wss://'
    else:
        url = 'ws://'

    if environ.get('HTTP_HOST'):
        url += environ['HTTP_HOST']
    else:
        url += environ['SERVER_NAME']

        if secure:
            if environ['SERVER_PORT'] != '443':
                url += ':' + environ['SERVER_PORT']
        else:
            if environ['SERVER_PORT'] != '80':
                url += ':' + environ['SERVER_PORT']

    url += quote(environ.get('SCRIPT_NAME', ''))
    url += quote(environ.get('PATH_INFO', ''))

    if environ.get('QUERY_STRING'):
        url += '?' + environ['QUERY_STRING']

    return url
