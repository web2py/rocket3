import requests


def hello_app(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"Hello World"]


def test_basic_get(make_server):
    h = make_server(hello_app)
    res = requests.get("http://127.0.0.1:%i/" % h.port)
    assert res.status_code == 200
    assert res.content == b"Hello World"
    assert res.headers["Content-Type"] == "text/plain"
    assert res.headers["Content-Length"] == "11"


def test_echo_method_and_path(make_server):
    def app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [
            ("%s %s" % (environ["REQUEST_METHOD"], environ["PATH_INFO"])).encode()
        ]

    h = make_server(app)
    res = requests.get("http://127.0.0.1:%i/some/path" % h.port)
    assert res.status_code == 200
    assert res.content == b"GET /some/path"


def test_post_round_trip(make_server):
    def echo(environ, start_response):
        length = int(environ.get("CONTENT_LENGTH", "0") or 0)
        body = environ["wsgi.input"].read(length) if length else b""
        start_response("200 OK", [("Content-Type", "application/octet-stream")])
        return [body]

    h = make_server(echo)
    payload = b"hello bytes" * 32
    res = requests.post("http://127.0.0.1:%i/" % h.port, data=payload)
    assert res.status_code == 200
    assert res.content == payload


def test_400_on_garbage_request_line(make_server):
    import socket

    h = make_server(hello_app)
    with socket.create_connection(("127.0.0.1", h.port), timeout=2) as s:
        s.sendall(b"NOT A VALID REQUEST LINE\r\n\r\n")
        data = b""
        s.settimeout(2)
        while True:
            try:
                chunk = s.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk
    assert data.startswith(b"HTTP/1.1 400")


def test_response_uses_crlf_line_endings(make_server):
    """The error RESPONSE template used to use bare LF. Confirm CRLF."""
    import socket

    h = make_server(hello_app)
    with socket.create_connection(("127.0.0.1", h.port), timeout=2) as s:
        s.sendall(b"BOGUS / HTTP/1.1\r\nHost: x\r\n\r\n")
        s.settimeout(2)
        buf = b""
        while b"\r\n\r\n" not in buf and len(buf) < 4096:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
    # Headers separated by CRLF and terminated by a blank CRLF line.
    head, _, _ = buf.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    assert lines[0].startswith(b"HTTP/1.1 400"), buf
    # No bare LF inside the header block.
    for line in lines:
        assert b"\n" not in line, "bare LF in header line: %r" % line


def test_keepalive_two_requests(make_server):
    import socket

    h = make_server(hello_app)
    with socket.create_connection(("127.0.0.1", h.port), timeout=5) as s:
        for _ in range(2):
            s.sendall(
                b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: keep-alive\r\n\r\n"
            )
            s.settimeout(5)
            buf = b""
            while b"Hello World" not in buf:
                chunk = s.recv(4096)
                if not chunk:
                    raise AssertionError("connection closed early; got %r" % buf)
                buf += chunk
            assert b"HTTP/1.1 200" in buf


def test_head_request_has_no_body(make_server):
    import socket

    def app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"BODY"]

    h = make_server(app)
    with socket.create_connection(("127.0.0.1", h.port), timeout=2) as s:
        s.sendall(b"HEAD / HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
        s.settimeout(2)
        buf = b""
        while True:
            try:
                chunk = s.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
    head, _, body = buf.partition(b"\r\n\r\n")
    assert head.startswith(b"HTTP/1.1 200"), buf
    assert body == b"", "HEAD response must not include a body, got %r" % body
