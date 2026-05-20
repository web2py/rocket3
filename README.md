# Rocket3

Rocket3 is the multi-threaded WSGI web server used by web2py and py4web, stripped of all the Python 2 logic and dependencies. It supports Python 3.9+ and can be used without web2py or py4web.

Rocket was originally developed by Massimo Di Pierro, then rewritten much better by Timothy Farrell, and then has had refactorings made by Massimo and other web2py contributors.

## Installation

```
pip install rocket3
```

## Example

```python
from rocket3 import Rocket3 as Rocket

def demo_app(environ, start_response):
    """simple example WSGI app"""
    start_response("200 OK", [("Content-Type", "text/html")])
    return [b"<html><body><h1>Hello from Rocket Web Server</h1></body></html>"]


server = Rocket(("0.0.0.0", 8080), "wsgi", {"wsgi_app": demo_app})
server.start()
```

## HTTPS

Pass a 4-tuple `(host, port, key_file, cert_file)` to serve over TLS, or a 5-tuple `(host, port, key_file, cert_file, ca_cert_file)` to also request a client certificate:

```python
server = Rocket(
    ("0.0.0.0", 8443, "key.pem", "cert.pem"),
    "wsgi",
    {"wsgi_app": demo_app},
)
server.start()
```

## Built-in demo

A trivial server that serves static files (or a hello page if no static folder is given) is bundled as `rocket3.demo`:

```
python -c "from rocket3 import demo; demo()" -i 127.0.0.1 -p 8000 -s ./static
```

## Development

The project uses [uv](https://docs.astral.sh/uv/) and [ruff](https://docs.astral.sh/ruff/). Common targets:

```
make check     # ruff check
make format    # ruff format
make test      # run the test suite
make build     # build sdist + wheel
make publish   # upload to PyPI
```

## License

BSDv3
