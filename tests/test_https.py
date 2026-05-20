import os
import socket
import threading
import time
import urllib3

import pytest
import requests

import rocket3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def hello_app(environ, start_response):
    scheme = environ["wsgi.url_scheme"]
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [("hello %s" % scheme).encode()]


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
                return
        except OSError:
            time.sleep(0.02)
    raise RuntimeError("server on %s:%i never came up" % (host, port))


@pytest.fixture
def dual_server():
    here = os.path.dirname(__file__)
    keyfile = os.path.join(here, "data", "localhost.key")
    crtfile = os.path.join(here, "data", "localhost.crt")
    http_port = _free_port()
    https_port = _free_port()
    interfaces = [
        ("localhost", http_port),
        ("localhost", https_port, keyfile, crtfile),
    ]
    server = rocket3.Rocket3(
        interfaces, "wsgi", {"wsgi_app": hello_app}, handle_signals=False
    )
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    _wait_listening("127.0.0.1", http_port)
    _wait_listening("127.0.0.1", https_port)
    yield http_port, https_port
    server.stop()
    thread.join(timeout=5)


def test_http_works(dual_server):
    http_port, _ = dual_server
    res = requests.get("http://localhost:%i/" % http_port, timeout=5)
    assert res.status_code == 200
    assert res.content == b"hello http"


def test_https_works(dual_server):
    _, https_port = dual_server
    res = requests.get("https://localhost:%i/" % https_port, verify=False, timeout=5)
    assert res.status_code == 200
    assert res.content == b"hello https"


def test_http_to_https_port_times_out(dual_server):
    """Plain HTTP to the HTTPS port: server should not respond."""
    _, https_port = dual_server
    with pytest.raises(requests.exceptions.RequestException):
        requests.get("http://localhost:%i/" % https_port, timeout=1)


def test_https_to_http_port_fails(dual_server):
    """TLS handshake on a plain HTTP port should fail loudly."""
    http_port, _ = dual_server
    with pytest.raises(requests.exceptions.RequestException):
        requests.get(
            "https://localhost:%i/" % http_port, verify=False, timeout=2
        )
