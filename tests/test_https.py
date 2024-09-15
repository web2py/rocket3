import requests
import threading
import unittest
import os
import ssl

import rocket3


def demo_app(environ, start_response):
    start_response(200, "Hello World")


class SimpleSSLTest(unittest.TestCase):
    def start_server(self):
        dir = os.path.dirname(__file__)
        interfaces = [
            ("localhost", 8007),
            (
                "localhost",
                8008,
                f"{dir}/data/localhost.key",
                f"{dir}/data/localhost.crt",
            ),
        ]
        rocket = rocket3.Rocket3(interfaces, "wsgi", {"wsgi_app": demo_app})
        rocket.start()

    def start_client(self):
        # HTTP ok
        res = requests.get("http://localhost:8007")
        self.assertTrue(res.content, "Hello World")

        # HTTPS ok
        res = requests.get("https://localhost:8008", verify=False)
        self.assertTrue(res.content, "Hello World")

        # HTTP wrong port
        try:
            res = requests.get("http://localhost:8008", timeout=1)
            raise RuntimeError("Expected no response/timeout")
        except requests.exceptions.ReadTimeout:
            ...

        # HTTPS wrong port
        try:
            res = requests.get("https://localhost:8007", verify=False)
            raise RuntimeError("should not get here")
        except Exception:
            ...

    def test_server(self):
        server = threading.Thread(target=self.start_server)
        server.daemon = True
        server.start()
        self.start_client()
