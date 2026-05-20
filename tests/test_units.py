"""Unit tests targeting the specific bugs fixed in this revision.

Where possible these are pure-Python tests that exercise the parsing /
formatting helpers without a real socket.  A handful of small end-to-end
tests at the bottom cover behavior that only shows up in the wire format.
"""

import io
import os
import socket
import threading
import time

import pytest

import rocket3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _ByteReader:
    """Minimal sock_file substitute backed by a bytes buffer."""

    def __init__(self, data):
        self.buf = io.BytesIO(data)

    def readline(self):
        return self.buf.readline()

    def read(self, n=-1):
        return self.buf.read(n)


def _make_worker():
    """Build a Worker with the bare minimum so we can call its parsers."""
    worker = rocket3.Worker.__new__(rocket3.Worker)
    worker.size = 0
    worker.status = "200 OK"
    worker.closeConnection = True
    worker.request_line = ""
    worker.protocol = "HTTP/1.1"
    worker.err_log = rocket3.logging.getLogger("rocket3.test.worker")
    worker.req_log = rocket3.logging.getLogger("rocket3.test.req")
    return worker


# ---------------------------------------------------------------------------
# RESPONSE template (CRLF fix)
# ---------------------------------------------------------------------------


def test_response_template_uses_crlf():
    body = rocket3.RESPONSE % ("HTTP/1.1", "400 Bad Request", 11, "text/plain", "Bad Request")
    # Bare LF only ever follows a CR, never on its own.
    for i, ch in enumerate(body):
        if ch == "\n":
            assert body[i - 1] == "\r", "bare LF at index %d in %r" % (i, body)
    # Header section ends with a CRLF CRLF.
    assert "\r\n\r\n" in body


# ---------------------------------------------------------------------------
# send_headers Content-Length gating (the or/and bug)
# ---------------------------------------------------------------------------


class _FakeConn:
    def __init__(self):
        self.sent = b""

    def sendall(self, data):
        self.sent += data


def _make_wsgi_worker(status):
    """Build a WSGIWorker just barely enough to call send_headers()."""
    from wsgiref.headers import Headers

    worker = rocket3.WSGIWorker.__new__(rocket3.WSGIWorker)
    worker.size = 0
    worker.status = status
    worker.closeConnection = False
    worker.protocol = "HTTP/1.1"
    worker.headers_sent = False
    worker.chunked = False
    worker.header_set = Headers([])
    worker.environ = {
        "SERVER_PROTOCOL": "HTTP/1.1",
        "HTTP_CONNECTION": "",
    }
    worker.err_log = rocket3.logging.getLogger("rocket3.test.wsgi")
    worker.conn = _FakeConn()
    return worker


@pytest.mark.parametrize("status", ["100 Continue", "101 Switching Protocols"])
def test_1xx_status_gets_no_content_length(status):
    """Pre-fix, the `or` logic added Content-Length to 1xx responses."""
    worker = _make_wsgi_worker(status)
    worker.send_headers(b"", sections=1)
    headers = worker.conn.sent.decode("latin-1")
    assert "Content-Length" not in headers, headers


@pytest.mark.parametrize("status", ["204 No Content", "304 Not Modified"])
def test_204_304_get_no_content_length(status):
    worker = _make_wsgi_worker(status)
    worker.send_headers(b"", sections=1)
    headers = worker.conn.sent.decode("latin-1")
    assert "Content-Length" not in headers, headers


def test_200_gets_content_length():
    worker = _make_wsgi_worker("200 OK")
    worker.send_headers(b"hello", sections=1)
    headers = worker.conn.sent.decode("latin-1")
    assert "Content-Length: 5" in headers, headers


# ---------------------------------------------------------------------------
# Request line / header parsing
# ---------------------------------------------------------------------------


def test_read_request_line_parses_get():
    worker = _make_worker()
    req = worker.read_request_line(_ByteReader(b"GET /foo?bar=1 HTTP/1.1\r\n"))
    assert req["method"] == "GET"
    assert req["path"] == "/foo"
    assert req["query_string"] == "bar=1"
    assert req["protocol"] == "HTTP/1.1"


def test_read_request_line_preserves_encoded_slash():
    worker = _make_worker()
    req = worker.read_request_line(
        _ByteReader(b"GET /a%2Fb HTTP/1.1\r\n")
    )
    # %2F in the path must be preserved (not turned into a real "/").
    assert req["path"] == "/a%2Fb"


def test_read_request_line_skips_leading_blank_line():
    worker = _make_worker()
    req = worker.read_request_line(
        _ByteReader(b"\r\nGET / HTTP/1.1\r\n")
    )
    assert req["method"] == "GET"


def test_read_request_line_bad_request_raises():
    worker = _make_worker()
    worker.conn = _FakeConn()
    with pytest.raises(rocket3.BadRequest):
        worker.read_request_line(_ByteReader(b"this is not http\r\n"))
    # send_response should have been called with a 400 over CRLF.
    assert worker.conn.sent.startswith(b"HTTP/1.1 400")
    assert b"\r\n\r\n" in worker.conn.sent


def test_read_headers_basic():
    worker = _make_worker()
    headers = worker.read_headers(
        _ByteReader(b"Host: x.example\r\nContent-Length: 5\r\n\r\n")
    )
    assert headers["HOST"] == "x.example"
    assert headers["CONTENT_LENGTH"] == "5"


def test_read_headers_continuation_line():
    worker = _make_worker()
    headers = worker.read_headers(
        _ByteReader(b"X-Long: part1\r\n part2\r\n\r\n")
    )
    assert headers["X_LONG"] == "part1 part2"


# ---------------------------------------------------------------------------
# demo_app: path-traversal safety
# ---------------------------------------------------------------------------


def test_safe_join_normal_path(tmp_path):
    (tmp_path / "ok.html").write_text("hi")
    result = rocket3._safe_join(str(tmp_path), "/ok.html")
    assert result == os.path.realpath(str(tmp_path / "ok.html"))


def test_safe_join_dot_dot_rejected(tmp_path):
    # /../etc/passwd style escape
    result = rocket3._safe_join(str(tmp_path), "/../etc/passwd")
    assert result is None


def test_safe_join_absolute_path_rejected(tmp_path):
    # Absolute paths inside path_info should still be confined to root
    # because we strip the leading slash before join.
    result = rocket3._safe_join(str(tmp_path), "/etc/passwd")
    # Allowed if 'etc/passwd' resolves under tmp_path (it doesn't exist
    # but is still inside root).  The point is it cannot escape.
    assert result is None or result.startswith(os.path.realpath(str(tmp_path)))


def test_demo_app_blocks_traversal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "static").mkdir()
    (tmp_path / "static" / "index.html").write_text("ok")

    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)

    out = rocket3.demo_app(
        {"PATH_INFO": "/../../../../etc/passwd"}, start_response
    )
    assert captured["status"].startswith(("403", "404")), captured
    # Make sure we did not somehow return the contents of a sensitive file.
    body = b"".join(out)
    assert b"root:" not in body


# ---------------------------------------------------------------------------
# Ctrl+C / clean shutdown
# ---------------------------------------------------------------------------


def _free_port():
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def _wait_listening(port, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.02)
    raise RuntimeError("server on 127.0.0.1:%i never came up" % port)


def test_stop_from_background_thread_terminates_cleanly():
    """server.start() running in a thread must return shortly after stop()."""
    def app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"ok"]

    port = _free_port()
    server = rocket3.Rocket3(
        ("127.0.0.1", port), "wsgi", {"wsgi_app": app}, handle_signals=False
    )
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    _wait_listening(port)
    server.stop()
    thread.join(timeout=10)
    assert not thread.is_alive(), "server thread did not exit within 10s"


def test_double_stop_does_not_deadlock():
    """A second stop() during shutdown must not block forever."""
    def app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"ok"]

    port = _free_port()
    server = rocket3.Rocket3(
        ("127.0.0.1", port), "wsgi", {"wsgi_app": app}, handle_signals=False
    )
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    _wait_listening(port)
    server.stop()
    # Second call should be a no-op rather than hang on the lock.
    second = threading.Thread(target=server.stop, daemon=True)
    second.start()
    second.join(timeout=5)
    assert not second.is_alive(), "second stop() deadlocked"
    thread.join(timeout=10)


def test_sigint_handler_stops_server():
    """The Rocket3._sigint handler must drive the server to shutdown.

    Real signal delivery only works from the main thread, and firing a
    real SIGINT inside pytest would also abort the test run, so we
    invoke the handler directly — that's the codepath SIGINT takes.
    """
    def app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"ok"]

    port = _free_port()
    server = rocket3.Rocket3(
        ("127.0.0.1", port), "wsgi", {"wsgi_app": app}, handle_signals=False
    )
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    _wait_listening(port)
    # Pretend SIGINT just fired.
    server._sigint(2, None)
    thread.join(timeout=10)
    assert not thread.is_alive(), "server thread did not exit after _sigint"


# ---------------------------------------------------------------------------
# log module name is not shadowed
# ---------------------------------------------------------------------------


def test_module_log_is_rocket_logger():
    assert rocket3.log.name == "Rocket"
    assert rocket3.threadpool_log.name == "Rocket.Errors.ThreadPool"
