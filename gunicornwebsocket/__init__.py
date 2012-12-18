version_info = (0, 0, 1)
__version__ = ".".join(map(str, version_info))

__all__ = ['WebSocketHandler', 'WebSocketError']

from gunicornwebsocket.handler import WebSocketHandler
from gunicornwebsocket.websocket import WebSocketError
