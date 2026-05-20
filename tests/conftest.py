import socket
import threading
import time

import pytest

import rocket3


def _free_port():
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def _wait_listening(host, port, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return True
        except OSError:
            time.sleep(0.02)
    raise RuntimeError("server on %s:%i never came up" % (host, port))


class ServerHandle:
    def __init__(self, server, thread, port):
        self.server = server
        self.thread = thread
        self.port = port

    def stop(self):
        self.server.stop()
        self.thread.join(timeout=5)


@pytest.fixture
def make_server():
    """Factory that spins up a Rocket3 in a background thread and tears it
    down at end of test.  Returns ServerHandle objects."""
    handles = []

    def _factory(app, *, interfaces=None, **kwargs):
        if interfaces is None:
            port = _free_port()
            interfaces = ("127.0.0.1", port)
        else:
            port = interfaces[1] if not isinstance(interfaces, list) else interfaces[0][1]

        kwargs.setdefault("handle_signals", False)
        server = rocket3.Rocket3(interfaces, "wsgi", {"wsgi_app": app}, **kwargs)
        thread = threading.Thread(target=server.start, daemon=True)
        thread.start()
        _wait_listening("127.0.0.1", port)
        handle = ServerHandle(server, thread, port)
        handles.append(handle)
        return handle

    yield _factory

    for h in handles:
        try:
            h.stop()
        except Exception:
            pass
