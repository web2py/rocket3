# Rocket3

Rocket3 is the multi-threaded web server used by web2py stripped of all the Python2 logic and dependencies. It now only supports Python3 and can be used without web2py.

Rocket was originally developed by Massimo Di Pierro, then rewritten much better by Timoty Ferrell, and then has minor refactorings made by Massimo and other web2py contributors.

## Example

```
from rocket3 import Rocket

def demo_app(environ, start_response):
    """simple exmaple WSGI app"""
    start_response("200 OK", [("Content-Type", "text/html")])
    data = "<html><body><h1>Hello from Rocket Web Server</h1></body></html>"
    return [data]


server = Rocket(('0.0.0.0', 8080), "wsgi", {"wsgi_app": demo_app})
server.start()
```

## License

BSDv3